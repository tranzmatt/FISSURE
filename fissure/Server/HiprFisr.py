from inspect import isfunction
from types import ModuleType
from typing import Dict, List, Union

import asyncio
import fissure.callbacks
import fissure.comms
import fissure.utils
from fissure.utils.plugin_editor import PluginEditor
import logging
import sys
import time
import uuid
import zmq
import subprocess
import os
import atexit
import ssl
from datetime import datetime, timezone, timedelta


HEARTBEAT_LOOP_DELAY = 0.1  # Seconds
EVENT_LOOP_DELAY = 0.1


def run():
    asyncio.run(main())


async def main():
    """
    Server __main__.py does not call this function. Do not edit! Edit __init__() or begin().
    """
    # Initialize HIPFISR
    print("[FISSURE][HiprFisr] start")
    hiprfisr = HiprFisr()

    # Start Event Loop
    await hiprfisr.begin()

    # End and Clean Up
    print("[FISSURE][HiprFisr] end")
    fissure.utils.zmq_cleanup()


class SensorNode:
    listener: fissure.comms.Listener
    connected: bool
    UUID: str
    last_heartbeat: float  # FIX: Use this or self.heartbeats?
    terminated: bool
    plugins: list = []


    def __init__(self, connection_type="IP", serial_port=None, name=None, context=None):
        """
        Initialize Listener
        """
        # self.listener = fissure.comms.Listener(zmq.PAIR, name=f"{fissure.comms.Identifiers.HIPRFISR}::sensor_node")
        self.connected = False
        self.UUID = ""
        self.last_heartbeat = 0
        self.terminated = False
        self.connection_type = connection_type

        if connection_type == "IP":
            self.listener = fissure.comms.Listener(
                zmq.PAIR, name=f"{fissure.comms.Identifiers.HIPRFISR}::sensor_node"
            )
        elif connection_type == "Meshtastic":
            if serial_port is None or context is None:
                raise ValueError("Meshtastic connection requires a serial port and context")

            self.listener = fissure.comms.FissureMeshtasticNode(serial_port, name, context)


    async def close(self):
        """
        Needed to use async close functions.
        """
        if hasattr(self, "listener") and self.listener is not None:
            if self.connection_type == "IP":
                self.listener.shutdown()
            elif self.connection_type == "Meshtastic":
                await self.listener.disconnect()


    def __del__(self):
        """
        Cleanup on GC
        """
        pass
        # if hasattr(self, "listener") and self.listener is not None:
        #     if self.connection_type == "IP":
        #         self.listener.shutdown()
        #     elif self.connection_type == "Meshtastic":
        #         self.listener.disconnect()


class HiprFisr:
    """Fissure HIPRFISR Class"""

    settings: Dict
    identifier: str = fissure.comms.Identifiers.HIPRFISR
    identifierLT: str = fissure.comms.Identifiers.HIPRFISR_LT
    # logger: logging.Logger = fissure.utils.get_logger(fissure.comms.Identifiers.HIPRFISR)
    ip_address: str
    session_active: bool
    dashboard_socket: fissure.comms.Server  # PAIR
    dashboard_connected: bool
    backend_router: fissure.comms.Server  # ROUTER-DEALER
    backend_id: str
    tsi_id: bytes
    tsi_connected: bool
    pd_id: bytes
    pd_connected: bool
    sensor_nodes: List[SensorNode]
    local_plugins: List[str] = []
    heartbeats: Dict[str, Union[float, Dict[int, float]]]  # {name: time, name: time, ... sensor_nodes: {node_id: time}}
    callbacks: Dict = {}
    shutdown: bool
    alert_listeners: Dict = {}


    def __init__(self, address: fissure.comms.Address):
        self.logger = fissure.utils.get_logger(fissure.comms.Identifiers.HIPRFISR)
        self.logger.info("=== INITIALIZING ===")

        # Get IP Address
        self.ip_address = fissure.utils.get_ip_address()

        # Sensor Node GPS Tracker for TAK
        self.sensor_node_tracker = SensorNodeTracker(self.logger)

        # Store Collected Wideband and Narrowband Signals in Lists
        self.wideband_list = []
        self.soi_list = []

        # SOI Blacklist
        self.soi_blacklist = []

        # Don't Process SOIs at Start
        self.process_sois = False

        # Create SOI sorting variables
        # SOI_priority = (0, 1, 2)
        # SOI_filter = ("Highest", "Highest", "Containing")
        self.soi_parameters = (None, None, "FSK")

        # Create the Variable
        self.auto_start_pd = False
        self.soi_manually_triggered = False

        # Initialize Connection/Heartbeat Variables
        self.heartbeats = {
            fissure.comms.Identifiers.HIPRFISR: None,
            fissure.comms.Identifiers.DASHBOARD: None,
            fissure.comms.Identifiers.PD: None,
            fissure.comms.Identifiers.TSI: None,
            fissure.comms.Identifiers.SENSOR_NODE: [None, None, None, None, None],
        }
        self.session_active = False
        self.dashboard_connected = False
        self.pd_id = None
        self.pd_connected = False
        self.tsi_id = None
        self.tsi_connected = False
        self.connect_loop = True

        # Load settings from Fissure Config YAML
        self.settings = fissure.utils.get_fissure_config()

        # Update Logging Levels
        fissure.utils.update_logging_levels(
            self.logger, 
            self.settings["console_logging_level"], 
            self.settings["file_logging_level"]
        )

        # Detect Operating System
        self.os_info = fissure.utils.get_os_info()

        # Start the Database Docker Container (if not running)
        self.start_database_docker_container()
        tak_info = self.settings.get("tak")
        run_tak = tak_info.get("tak_on_startup")
        if run_tak == 'True':
            self.start_tak_docker_container()

        # Create the HIPRFISR ZMQ Nodes
        listen_addr = self.initialize_comms(address)
        self.initialize_sensor_nodes()
        self.message_counter = 0
        self.shutdown = False

        # Register Callbacks
        self.register_callbacks(fissure.callbacks.GenericCallbacks)
        self.register_callbacks(fissure.callbacks.HiprFisrCallbacks)
        self.register_callbacks(fissure.callbacks.HiprFisrCallbacksLT)

        self.logger.info("=== READY ===")
        self.logger.info(f"Server listening @ {listen_addr}")


    def initialize_comms(self, frontend_address: fissure.comms.Address):
        comms_info = self.settings.get("hiprfisr")
        backend_address = fissure.comms.Address(address_config=comms_info.get("backend"))

        # Frontend - Dashboard
        self.dashboard_socket = fissure.comms.Server(
            address=frontend_address, sock_type=zmq.PAIR, name=f"{self.identifier}::frontend"
        )
        self.dashboard_socket.start()

        # Backend - PD, TSI
        self.backend_id = f"{self.identifier}-{uuid.uuid4()}"
        self.backend_router = fissure.comms.Server(
            address=backend_address, sock_type=zmq.ROUTER, name=f"{self.identifier}::backend"
        )
        self.backend_router.start()

        if frontend_address.protocol == "tcp":
            frontend_address.update(address=self.ip_address)
        return frontend_address


    def initialize_sensor_nodes(self):
        """
        Initialize Sensor Node Listeners, Heartbeats, etc
        """
        self.sensor_nodes = []
        for n in range(0,5):
            # self.sensor_nodes.append(SensorNode())
            self.sensor_nodes.append(None)

    
    async def reset_sensor_node_listener(self, sensor_node_index=0, connection_type="IP", **kwargs):
        """
        Resets and initializes a sensor node listener based on the connection type.
        """
        if connection_type == "IP":
            self.sensor_nodes[sensor_node_index] = SensorNode(connection_type="IP")
            atexit.register(self.sensorNodeCleanup, self.sensor_nodes[sensor_node_index])
        elif connection_type == "Meshtastic":
            serial_port = kwargs.get("serial_port")
            context = kwargs.get("context")
            name = kwargs.get("name", "MeshtasticNode")
            if not serial_port or not context:
                raise ValueError("Missing required arguments for Meshtastic connection")

            # Initialize SensorNode with Meshtastic
            self.sensor_nodes[sensor_node_index] = SensorNode(
                connection_type="Meshtastic",
                serial_port=serial_port,
                name=name,
                context=context
            )
            atexit.register(self.sensorNodeCleanup, self.sensor_nodes[sensor_node_index])


    def register_callbacks(self, ctx: ModuleType):
        """
        Register callbacks from the provided context

        :param ctx: context containing callbacks to register
        :type ctx: ModuleType
        """
        callbacks = [(f, getattr(ctx, f)) for f in dir(ctx) if isfunction(getattr(ctx, f))]
        for cb_name, cb_func in callbacks:
            self.callbacks[cb_name] = cb_func
        self.logger.debug(f"registered {len(callbacks)} callbacks from {ctx.__name__}")


    async def shutdown_comms(self):
        shutdown_notice = {
            fissure.comms.MessageFields.IDENTIFIER: self.identifier,
            fissure.comms.MessageFields.MESSAGE_NAME: "Shutting Down",
            fissure.comms.MessageFields.PARAMETERS: "",
        }
        await self.dashboard_socket.send_msg(fissure.comms.MessageTypes.STATUS, shutdown_notice)
        self.dashboard_connected = False
        self.session_active = False
        self.dashboard_socket.shutdown()
        self.backend_router.shutdown()


    async def heartbeat_loop(self):
        """
        Sends and reads heartbeat messages, separate from event loop to prevent freezing on blocking events.
        """
        # Start Heartbeat Loop
        while self.shutdown is False:
            if self.connect_loop is False:
                # Heartbeats
                await self.send_heartbeat()
                await self.recv_heartbeats()
                await self.check_heartbeats()

            await asyncio.sleep(HEARTBEAT_LOOP_DELAY)


    async def begin(self):
        """
        Main Event Loop
        """
        # Begin
        self.logger.info("=== STARTING HIPRFISR ===")

        # Start Heartbeat Loop
        heartbeat_task = asyncio.create_task(self.heartbeat_loop())
        
        # Start Event Loop
        while self.shutdown is False:
            if self.connect_loop is False:
                # Process Incoming Messages
                if self.dashboard_connected:
                    await self.read_dashboard_messages()
                if self.pd_connected or self.tsi_connected:
                    await self.read_backend_messages()

                for sensor_node in self.sensor_nodes:
                    if sensor_node:
                        if sensor_node.connected is True:
                            await self.read_sensor_node_messages()
                            break
                
                await asyncio.sleep(EVENT_LOOP_DELAY)

            else:
                await self.connect_components()
        self.logger.debug("Shutdown reached in HIPRFISR event loop")

        # Ensure the Heartbeat Loop is Stopped
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass  # Heartbeat task was cancelled cleanly

        # Shut Down Comms
        await self.shutdown_comms()
        self.logger.info("=== SHUTDOWN ===")


    async def connect_components(self):
        """
        Wait for all FISSURE Components to connect or `Exit Connect Loop` message from Dashboard
        """
        self.logger.debug("Entering connect loop")
        while self.connect_loop is True:
            # Send and Listen for Heartbeats
            # NOTE: HiprFisr won't send any heartbeats on a socket until it receives one first
            await self.recv_heartbeats()
            await self.send_heartbeat()
            await self.check_heartbeats()

            # Listen for messages
            await self.read_dashboard_messages()
            await self.read_backend_messages()

            # Tell Dashboard everything is connected
            # TODO: Update this message
            if self.dashboard_connected and self.pd_connected and self.tsi_connected:
                msg = {
                    fissure.comms.MessageFields.IDENTIFIER: self.identifier,
                    fissure.comms.MessageFields.MESSAGE_NAME: "Connected",
                    fissure.comms.MessageFields.PARAMETERS: [
                        fissure.comms.Identifiers.PD,
                        fissure.comms.Identifiers.TSI,
                    ],
                }
                await self.dashboard_socket.send_msg(fissure.comms.MessageTypes.STATUS, msg)
                self.connect_loop = False
        self.logger.debug("Exiting connect loop")


    async def read_dashboard_messages(self):
        """
        Receive messages from the Dashboard and carry out commands
        """
        received_message = ""
        while received_message is not None:
            received_message = await self.dashboard_socket.recv_msg()
            if received_message is not None:
                self.dashboard_connected = True
                msg_type = received_message.get(fissure.comms.MessageFields.TYPE)
                if msg_type == fissure.comms.MessageTypes.HEARTBEATS:
                    self.logger.warning("recieved heartbeat on message channel [from Dashboard]")
                elif msg_type == fissure.comms.MessageTypes.COMMANDS:
                    await self.dashboard_socket.run_callback(self, received_message)

                elif msg_type == fissure.comms.MessageTypes.STATUS:
                    msg_name = received_message.get(fissure.comms.MessageFields.MESSAGE_NAME)
                    if msg_name == "Connected":
                        response = {
                            fissure.comms.MessageFields.IDENTIFIER: self.identifier,
                            fissure.comms.MessageFields.MESSAGE_NAME: "OK",
                        }
                        await self.dashboard_socket.send_msg(fissure.comms.MessageTypes.STATUS, response)
                        self.session_active = True
                    elif msg_name == "Exit Connect Loop":
                        self.connect_loop = False
                    else:
                        pass
                else:
                    pass
            if self.dashboard_connected is False:
                received_message = None


    async def read_backend_messages(self):
        """
        Receive messages from the backend components and carry out commands
        """
        received_message = ""
        while received_message is not None:
            received_message = await self.backend_router.recv_msg()
            if received_message is not None:
                sender_id = received_message.get(fissure.comms.MessageFields.SENDER_ID)
                component = received_message.get(fissure.comms.MessageFields.IDENTIFIER)
                msg_type = received_message.get(fissure.comms.MessageFields.TYPE)

                # Set ZMQ Identities of components if we dont already have them
                if component == fissure.comms.Identifiers.PD and self.pd_id is None:
                    self.pd_id = sender_id
                if component == fissure.comms.Identifiers.TSI and self.tsi_id is None:
                    self.tsi_id = sender_id
                if msg_type == fissure.comms.MessageTypes.HEARTBEATS:
                    self.logger.warning(f"recieved heartbeat on message channel [from {component}]")
                elif msg_type == fissure.comms.MessageTypes.COMMANDS:
                    await self.backend_router.run_callback(self, received_message)
                elif msg_type == fissure.comms.MessageTypes.STATUS:
                    msg_name = received_message.get(fissure.comms.MessageFields.MESSAGE_NAME)
                    if msg_name == "Connected":
                        response = {
                            fissure.comms.MessageFields.IDENTIFIER: self.identifier,
                            fissure.comms.MessageFields.MESSAGE_NAME: "OK",
                        }
                        await self.backend_router.send_msg(
                            fissure.comms.MessageTypes.STATUS, response, target_ids=[sender_id]
                        )
                    else:
                        # TODO
                        pass
                else:
                    pass


    async def read_sensor_node_messages(self):
        """
        Receive and parse messages from the Sensor Nodes and carry out commands
        """
        for n, sensor_node in enumerate(self.sensor_nodes):
            if sensor_node:
                if sensor_node.connection_type == "IP":
                    if sensor_node.connected is True:
                        parsed = ""
                        while parsed is not None:
                            parsed = await sensor_node.listener.recv_msg()
                            if parsed is not None:
                                msg_type = parsed.get(fissure.comms.MessageFields.TYPE)
                                # name = parsed.get(fissure.comms.MessageFields.MESSAGE_NAME)
                                # if msg_type == fissure.comms.MessageTypes.HEARTBEATS:  # Handled in recv_heartbeats()
                                #     heartbeat_time = float(parsed.get(fissure.comms.MessageFields.TIME))
                                #     self.heartbeats[fissure.comms.Identifiers.SENSOR_NODE][n] = heartbeat_time
                                if msg_type == fissure.comms.MessageTypes.COMMANDS:
                                    await sensor_node.listener.run_callback(self, parsed)
                                elif msg_type == fissure.comms.MessageTypes.STATUS:
                                    pass
                                else:
                                    pass


    async def send_heartbeat(self):
        """
        Send Hearbeat Message
        NOTE: Can probably just have one log message for heartbeat being sent
        """
        last_heartbeat = self.heartbeats[self.identifier]
        now = time.time()
        if (last_heartbeat is None) or (now - last_heartbeat) >= float(self.settings.get("heartbeat_interval")):
            heartbeat = {
                fissure.comms.MessageFields.IDENTIFIER: self.identifier,
                fissure.comms.MessageFields.MESSAGE_NAME: fissure.comms.MessageFields.HEARTBEAT,
                fissure.comms.MessageFields.TIME: now,
                fissure.comms.MessageFields.PARAMETERS: {
                    fissure.comms.Identifiers.PD: self.heartbeats.get(fissure.comms.Identifiers.PD),
                    fissure.comms.Identifiers.TSI: self.heartbeats.get(fissure.comms.Identifiers.TSI),
                    fissure.comms.Identifiers.SENSOR_NODE: [
                        self.heartbeats.get(f"{fissure.comms.Identifiers.SENSOR_NODE}_{idx}") for idx in range(1, 6)
                    ],
                },
            }
            if self.dashboard_connected:
                await self.dashboard_socket.send_heartbeat(heartbeat)
                self.logger.debug(f"sent heartbeat to dashboard ({fissure.utils.get_timestamp(now)})")
            if self.pd_connected or self.tsi_connected:
                heartbeat.update({fissure.comms.MessageFields.IP: "localhost"})
                await self.backend_router.send_heartbeat(
                    heartbeat,
                    target_ids=[self.pd_id, self.tsi_id],
                )
                self.logger.debug(f"sent heartbeat to backend ({fissure.utils.get_timestamp(now)})")

            for sensor_node in self.sensor_nodes:
                if sensor_node:
                    if sensor_node.connection_type == "IP":
                        if sensor_node.connected:
                            await sensor_node.listener.send_heartbeat(heartbeat)
                            self.logger.debug(f"sent heartbeat to {sensor_node.UUID} ({fissure.utils.get_timestamp(now)})")
            self.heartbeats[self.identifier] = now


    async def recv_heartbeats(self):
        """
        Receive Heartbeat Messages
        """
        # Collect Heartbeats
        dashboard_heartbeat = await self.dashboard_socket.recv_heartbeat()
        backend_heartbeats = await self.backend_router.recv_heartbeats()
        sensor_node_heartbeats = []
        for sensor_node in self.sensor_nodes:
            if sensor_node:
                if sensor_node.connection_type == "IP":
                    sensor_node_heartbeats.append(await sensor_node.listener.recv_heartbeat())            

        # Process Dashboard Heartbeats
        if dashboard_heartbeat is not None:
            heartbeat_time = float(dashboard_heartbeat.get(fissure.comms.MessageFields.TIME))
            self.heartbeats[fissure.comms.Identifiers.DASHBOARD] = heartbeat_time
            self.logger.debug(f"received Dashboard heartbeat ({fissure.utils.get_timestamp(heartbeat_time)})")

        # Process Backend Heartbeats
        if len(backend_heartbeats) > 0:
            for heartbeat in backend_heartbeats:
                sender_id = heartbeat.get(fissure.comms.MessageFields.SENDER_ID)
                component = heartbeat.get(fissure.comms.MessageFields.IDENTIFIER)
                heartbeat_time = float(heartbeat.get(fissure.comms.MessageFields.TIME))
                self.logger.debug(
                    f"received backend heartbeat from {component} ({fissure.utils.get_timestamp(heartbeat_time)})"
                )
                # Set ZMQ Identities of components if we dont already have them
                if component == fissure.comms.Identifiers.PD and self.pd_id is None:
                    self.pd_id = sender_id
                if component == fissure.comms.Identifiers.TSI and self.tsi_id is None:
                    self.tsi_id = sender_id
                try:
                    self.heartbeats[component] = heartbeat_time
                except KeyError:
                    self.logger.warning(f"received unrecogized heartbeat from {component} at {heartbeat_time}")

        # Process Sensor Node Heartbeats
        for heartbeat in sensor_node_heartbeats:
            if heartbeat is not None:
                # Sensor Node UUID and Heartbeat Value
                uuid = heartbeat.get(fissure.comms.MessageFields.IDENTIFIER)
                heartbeat_time = float(heartbeat.get(fissure.comms.MessageFields.TIME))

                # Check if UUID is Saved
                uuid_found = False
                for idx, item in enumerate(self.heartbeats[fissure.comms.Identifiers.SENSOR_NODE]):
                    if item is not None:
                        # Save
                        if next(iter(item)) == uuid:
                            self.heartbeats[fissure.comms.Identifiers.SENSOR_NODE][idx] = {uuid: heartbeat_time}
                            uuid_found = True
                            break
                
                # Save New UUID/Heartbeat to the End of List
                if uuid_found == False:
                     for idx, item in enumerate(self.heartbeats[fissure.comms.Identifiers.SENSOR_NODE]):
                         if item == None:
                             self.heartbeats[fissure.comms.Identifiers.SENSOR_NODE][idx] = {uuid: heartbeat_time}
                             break


    async def check_heartbeats(self):
        """
        Check hearbeats and set connection flags accordingly
        """
        current_time = time.time()
        cutoff_interval = float(self.settings.get("failure_multiple")) * float(self.settings.get("heartbeat_interval"))
        cutoff_time = current_time - cutoff_interval

        # Dashboard Check
        last_dashboard_heartbeat = self.heartbeats.get(fissure.comms.Identifiers.DASHBOARD)
        if last_dashboard_heartbeat is not None:
            # Failed heartbeat check while previously connected
            if self.dashboard_connected and (last_dashboard_heartbeat < cutoff_time):
                # Cannot send notice to Dashboard
                self.dashboard_connected = False
                self.logger.warning("lost dashboard connection")

            # Passed heartbeat check while previously disconnected
            elif (not self.dashboard_connected) and (last_dashboard_heartbeat > cutoff_time):
                msg = {
                    fissure.comms.MessageFields.IDENTIFIER: self.identifier,
                    fissure.comms.MessageFields.MESSAGE_NAME: "componentConnected",
                    fissure.comms.MessageFields.PARAMETERS: fissure.comms.Identifiers.DASHBOARD,
                }
                await self.dashboard_socket.send_msg(fissure.comms.MessageTypes.COMMANDS, msg)
                self.dashboard_connected = True

        # PD Check
        last_pd_heartbeat = self.heartbeats.get(fissure.comms.Identifiers.PD)
        if last_pd_heartbeat is not None:
            # Failed heartbeat check while previously connected
            if self.pd_connected and (last_pd_heartbeat < cutoff_time):
                msg = {
                    fissure.comms.MessageFields.IDENTIFIER: self.identifier,
                    fissure.comms.MessageFields.MESSAGE_NAME: "componentDisconnected",
                    fissure.comms.MessageFields.PARAMETERS: fissure.comms.Identifiers.PD,
                }
                if self.dashboard_connected:
                    await self.dashboard_socket.send_msg(fissure.comms.MessageTypes.COMMANDS, msg)
                self.pd_connected = False
            # Passed heartbeat check while previously disconnected
            elif (not self.pd_connected) and (last_pd_heartbeat > cutoff_time):
                msg = {
                    fissure.comms.MessageFields.IDENTIFIER: self.identifier,
                    fissure.comms.MessageFields.MESSAGE_NAME: "componentConnected",
                    fissure.comms.MessageFields.PARAMETERS: fissure.comms.Identifiers.PD,
                }
                if self.dashboard_connected:
                    await self.dashboard_socket.send_msg(fissure.comms.MessageTypes.COMMANDS, msg)
                self.pd_connected = True

        # TSI Check
        last_tsi_heartbeat = self.heartbeats.get(fissure.comms.Identifiers.TSI)
        if last_tsi_heartbeat is not None:
            # Failed heartbeat check while previously connected
            if self.tsi_connected and (last_tsi_heartbeat < cutoff_time):
                msg = {
                    fissure.comms.MessageFields.IDENTIFIER: self.identifier,
                    fissure.comms.MessageFields.MESSAGE_NAME: "componentDisconnected",
                    fissure.comms.MessageFields.PARAMETERS: fissure.comms.Identifiers.TSI,
                }
                if self.dashboard_connected:
                    await self.dashboard_socket.send_msg(fissure.comms.MessageTypes.COMMANDS, msg)
                self.tsi_connected = False
            # Passed heartbeat check while previously disconnected
            elif (not self.tsi_connected) and (last_tsi_heartbeat > cutoff_time):
                msg = {
                    fissure.comms.MessageFields.IDENTIFIER: self.identifier,
                    fissure.comms.MessageFields.MESSAGE_NAME: "componentConnected",
                    fissure.comms.MessageFields.PARAMETERS: fissure.comms.Identifiers.TSI,
                }
                if self.dashboard_connected:
                    await self.dashboard_socket.send_msg(fissure.comms.MessageTypes.COMMANDS, msg)
                self.tsi_connected = True

        # Sensor Node Check
        for idx, sensor_node in enumerate(self.sensor_nodes):
            if sensor_node:
                # Heartbeat has a Value
                heartbeat_item = self.heartbeats.get(fissure.comms.Identifiers.SENSOR_NODE)[idx]
                if heartbeat_item is not None and isinstance(heartbeat_item, dict):
                    last_sensor_node_heartbeat = next(iter(heartbeat_item.values()))
                    if last_sensor_node_heartbeat is not None:
                        # Failed heartbeat check while previously connected
                        if sensor_node.connected and (last_sensor_node_heartbeat < cutoff_time):
                            msg = {
                                fissure.comms.MessageFields.IDENTIFIER: self.identifier,
                                # fissure.comms.MessageFields.IDENTIFIER: fissure.comms.Identifiers.SENSOR_NODE + f"_{idx}",
                                fissure.comms.MessageFields.MESSAGE_NAME: "componentDisconnected",
                                fissure.comms.MessageFields.PARAMETERS: str(idx),
                            }
                            self.sensor_nodes[idx].connected = False
                            if self.dashboard_connected:
                                await self.dashboard_socket.send_msg(fissure.comms.MessageTypes.COMMANDS, msg)

                        # Passed heartbeat check while previously disconnected
                        elif (
                            (not sensor_node.connected)
                            and (last_sensor_node_heartbeat > cutoff_time)
                            and (not sensor_node.terminated)
                        ):
                            msg = {
                                fissure.comms.MessageFields.IDENTIFIER: self.identifier,
                                # fissure.comms.MessageFields.IDENTIFIER: fissure.comms.Identifiers.SENSOR_NODE + f"_{idx}",
                                fissure.comms.MessageFields.MESSAGE_NAME: "componentConnected",
                                fissure.comms.MessageFields.PARAMETERS: str(idx),  # {"uuid": sensor_node.UUID},
                            }
                            self.sensor_nodes[idx].connected = True
                            if self.dashboard_connected:
                                await self.dashboard_socket.send_msg(fissure.comms.MessageTypes.COMMANDS, msg)


    async def updateLoggingLevels(self, new_console_level="", new_file_level=""):
        """Update the logging levels on the HIPRFISR and forward to all components."""
        # Update New Levels for the HIPRFISR
        fissure.utils.update_logging_levels(self.logger, new_console_level, new_file_level)

        # For Testing
        # self.logger.info("INFO")
        # self.logger.debug("DEBUG")
        # self.logger.warning("WARNING")
        # self.logger.error("ERROR")
        # print(f"Logger level: {self.logger.level}")
        # for handler in self.logger.handlers:
        #     print(f"Handler {type(handler).__name__} level: {handler.level}")

        # Update Other Components
        PARAMETERS = {"new_console_level": new_console_level, "new_file_level": new_file_level}
        msg = {
            fissure.comms.MessageFields.IDENTIFIER: self.identifier,
            fissure.comms.MessageFields.MESSAGE_NAME: "updateLoggingLevels",
            fissure.comms.MessageFields.PARAMETERS: PARAMETERS,
        }
        if (self.pd_connected is True) and (self.tsi_connected is True):
            await self.backend_router.send_msg(
                fissure.comms.MessageTypes.COMMANDS, msg, target_ids=[self.pd_id, self.tsi_id]
            )
        for sensor_node in self.sensor_nodes:
            if sensor_node:
                if sensor_node.connected is True:
                    if sensor_node.connection_type == "IP":
                        await sensor_node.listener.send_msg(fissure.comms.MessageTypes.COMMANDS, msg)
                    elif sensor_node.connection_type == "Meshtastic":
                        pass


    def start_database_docker_container(self):
        """
        Starts the database Docker container if it is not already running.
        """
        def run_docker_command(command, use_sudo=False, cwd=None):
            """ Helper to run Docker commands with optional sudo and working directory. """
            if use_sudo:
                command.insert(0, "sudo")
            return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd)

        try:
            # Define the Docker image to check
            image_name = "postgres:13"

            # Check if the Docker container is running
            result = run_docker_command(['docker', 'ps', '--filter', f'ancestor={image_name}', '--format', '{{.Image}}'])

            # If the command failed due to permissions, retry with sudo
            if result.returncode != 0 and "permission denied" in result.stderr.lower():
                self.logger.info("Docker requires sudo. Retrying with sudo.")
                result = run_docker_command(['docker', 'ps', '--filter', f'ancestor={image_name}', '--format', '{{.Image}}'], use_sudo=True)

            # Check if the container is already running
            if image_name in result.stdout.strip():
                self.logger.info("Database Docker container is already running.")
                return

            # Container not running, start it
            self.logger.info("Database Docker container not found. Starting it...")

            # Define the start command
            start_command = ["docker", "compose", "up", "-d"]
            docker_compose_directory = fissure.utils.FISSURE_ROOT

            # Attempt to start without sudo
            start_result = run_docker_command(start_command, cwd=docker_compose_directory)
            if start_result.returncode != 0 and "permission denied" in start_result.stderr.lower():
                self.logger.info("Starting Docker with sudo.")
                start_result = run_docker_command(start_command, use_sudo=True, cwd=docker_compose_directory)

            if start_result.returncode == 0:
                self.logger.info("Docker container started successfully.")
            else:
                self.logger.error(f"Failed to start Docker container: {start_result.stderr.strip()}")

        except Exception as e:
            self.logger.error(f"Error: {e}")


    def start_tak_docker_container(self):
        """
        Starts the TAK Docker containers (DB and server) if not already running.
        Handles versioned container names dynamically.
        """
        def run_docker_command(command, use_sudo=False, cwd=None):
            """ Helper to run Docker commands with optional sudo and working directory. """
            if use_sudo:
                command.insert(0, "sudo")
            return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd)


        def get_matching_containers(name_prefix):
            """ Returns a list of container names matching a given prefix. """
            cmd = ["docker", "ps", "-a", "--filter", f"name={name_prefix}", "--format", "{{.Names}}"]
            result = run_docker_command(cmd)
            if result.returncode != 0 and "permission denied" in result.stderr.lower():
                result = run_docker_command(cmd, use_sudo=True)
            if result.returncode == 0:
                return result.stdout.strip().splitlines()
            else:
                self.logger.error(f"Failed to list containers with prefix '{name_prefix}': {result.stderr.strip()}")
                return []


        def start_container(name):
            """ Starts a container by name, handling sudo if needed. """
            start_cmd = ["docker", "start", name]
            result = run_docker_command(start_cmd)
            if result.returncode != 0 and "permission denied" in result.stderr.lower():
                result = run_docker_command(start_cmd, use_sudo=True)
            return result

        try:
            db_containers = get_matching_containers("takserver-db-")
            server_containers = get_matching_containers("takserver-")

            # Remove DB containers from the server list (avoid duplication)
            server_containers = [c for c in server_containers if not c.startswith("takserver-db-")]

            if not db_containers and not server_containers:
                self.logger.warning("No TAK Docker containers found.")
                return

            for container in db_containers:
                result = start_container(container)
                if result.returncode == 0:
                    self.logger.info(f"Started TAK DB container: {container}")
                else:
                    self.logger.error(f"Failed to start TAK DB container {container}: {result.stderr.strip()}")

            for container in server_containers:
                result = start_container(container)
                if result.returncode == 0:
                    self.logger.info(f"Started TAK Server container: {container}")
                else:
                    self.logger.error(f"Failed to start TAK Server container {container}: {result.stderr.strip()}")

        except Exception as e:
            self.logger.error(f"Exception while starting TAK containers: {e}")


    def openPluginEditor(self, plugin_name: str):
        self.plugin_editor = PluginEditor(plugin_name)


    # def closePluginEditor(self):
    #     self.plugin_editor = None


    # def pluginEditorGetProtocols(self):
    #     return self.plugin_editor.get_protocols()


    def pluginAddProtocolHiprfisr(self, protocol_name: str):
        # add protocol (or edit if it already exists)
        self.plugin_editor.add_protocol(protocol_name)
        return self.plugin_editor.get_protocol_parameters(protocol_name)
    

    def sensorNodeCleanup(self, sensor: SensorNode):
        """
        Closes SensorNode object on exit.
        """
        asyncio.run(sensor.close())


    async def send_cot(self, uid, lat, lon, alt, time, remarks):
        """
        Sends CoT message to TAK server. Used for alerts but not for the sensor node GPS beacon.
        """

        #print("IN TAK SEND FUNCTION")
        
        # Get TAK server settings
        settings: dict = fissure.utils.get_fissure_config()
        s_addr = settings["tak"]["ip_addr"]
        s_port = settings["tak"]["port"]
        tak_cert = settings["tak"]["cert"]
        tak_key = settings["tak"]["key"]

        cot_msg = f"""<?xml version="1.0" encoding="UTF-8"?>
        <event version="2.0" type="a-f-G-U-H" uid="{uid}" how="m-g" time="{time}" start="{time}" stale="2029-08-09T18:18:06.521956Z">
            <detail>
                <contact callsign="{uid}"/>
                <remarks>"{remarks}"</remarks>
            </detail>
            <point lat="{lat}" lon="{lon}" ce="0" le="0" hae="0"/>
        </event>"""

        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_cert_chain(certfile=tak_cert, keyfile=tak_key)

        # Base directory where TAK server versions are installed
        tak_base_path = os.path.expanduser("~/Installed_by_FISSURE")

        # List directories, ignoring .zip files
        try:
            tak_dirs = [
                d for d in os.listdir(tak_base_path)
                if d.startswith("takserver-docker-") and os.path.isdir(os.path.join(tak_base_path, d))
            ]
            tak_dirs.sort(reverse=True)  # Sort to get the latest version first
            takserver_path = os.path.join(tak_base_path, tak_dirs[0]) if tak_dirs else None
        except FileNotFoundError:
            takserver_path = None  # Handle case where directory does not exist

        # Construct the full path to root-ca.pem
        if takserver_path:
            root_ca_path = os.path.join(takserver_path, "tak/certs/files/root-ca.pem")
        else:
            root_ca_path = None  # No TAK server found

        #print("Using TAK Root CA:", root_ca_path)
        
        context.load_verify_locations(root_ca_path)
        context.check_hostname = False
        
        try:
            reader, writer = await asyncio.open_connection(s_addr, s_port, ssl=context)
            writer.write(cot_msg.encode('utf-8'))
            await writer.drain()
            print("Message sent to TAK server.")
            await asyncio.sleep(1)  # Add a small delay before closing, prevents [SSL: APPLICATION_DATA_AFTER_CLOSE_NOTIFY] error
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            print(f"Error sending to TAK: {e}")


class SensorNodeTracker:
    def __init__(self, logger):
        self.logger = logger
        self.past_positions = {}


    async def send_cot_gps_update(self, uid, lat, lon, alt, time, remarks, max_history=10):
        """
        Sends GPS update CoT messages to TAK server for current position and past positions.
        """
        # Ensure history size limit
        self.past_positions.setdefault(uid, []).append((lat, lon, alt, time))  # Creates dict key and empty list if it does not exist
        if len(self.past_positions[uid]) > max_history:
            self.past_positions[uid].pop(0)

        # Generate stale time (5 minutes ahead)
        time_format = "%Y-%m-%dT%H:%M:%SZ"
        stale_time = (datetime.now(timezone.utc) + timedelta(minutes=60)).strftime(time_format)  # stale_time="2029-08-09T18:18:06.521956Z"

        # Get TAK server settings
        settings: dict = fissure.utils.get_fissure_config()
        s_addr = settings["tak"]["ip_addr"]
        s_port = settings["tak"]["port"]
        tak_cert = settings["tak"]["cert"]
        tak_key = settings["tak"]["key"]

        # # Live Position CoT
        # cot_msg = f"""<?xml version="1.0" encoding="UTF-8"?>
        # <event version="2.0" type="b-m-p-w" uid="{uid}{time}" how="m-g" time="{time}" start="{time}" stale="2029-08-09T18:18:06.521956Z">
        #     <detail>
        #         <contact callsign="{uid}"/>
        #         <remarks>"{remarks}"</remarks>
        #     </detail>
        #     <point lat="{lat}" lon="{lon}" ce="0" le="0" hae="0"/>
        # </event>"""

        # List to hold CoT messages
        cot_messages = []

        # **Loop through past positions and add them to CoT messages**
        for i, past_entry in enumerate(reversed(self.past_positions[uid])):  # Reverse order for logical labeling
            if len(past_entry) == 4:
                p_lat, p_lon, p_alt, p_time = past_entry
            elif len(past_entry) == 3:
                p_lat, p_lon, p_time = past_entry
                p_alt = 0  # Default altitude if missing
            else:
                self.logger.error(f"Skipping malformed entry: {past_entry}")
                continue  # Skip invalid entries

            # First entry gets the base UID, others are numbered
            position_number = "" if i == 0 else f"-{i}"

            past_cot = f"""<?xml version="1.0" encoding="UTF-8"?>
            <event version="2.0" type="b-m-p-w" uid="{uid}{position_number}" how="m-g"
                time="{p_time}" start="{p_time}" stale="{stale_time}">
                <detail>
                    <contact callsign="{uid} {position_number}"/>
                    <remarks>"{remarks}"</remarks>
                </detail>
                <point lat="{p_lat}" lon="{p_lon}" ce="5" le="5" hae="{p_alt}"/>
            </event>"""
            
            cot_messages.append(past_cot)

        # Use Single Persistent Connection
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_cert_chain(certfile=tak_cert, keyfile=tak_key)

        # Base directory where TAK server versions are installed
        tak_base_path = os.path.expanduser("~/Installed_by_FISSURE")

        # List directories, ignoring .zip files
        try:
            tak_dirs = [
                d for d in os.listdir(tak_base_path)
                if d.startswith("takserver-docker-") and os.path.isdir(os.path.join(tak_base_path, d))
            ]
            tak_dirs.sort(reverse=True)  # Sort to get the latest version first
            takserver_path = os.path.join(tak_base_path, tak_dirs[0]) if tak_dirs else None
        except FileNotFoundError:
            takserver_path = None  # Handle case where directory does not exist

        # Construct the full path to root-ca.pem
        if takserver_path:
            root_ca_path = os.path.join(takserver_path, "tak/certs/files/root-ca.pem")
        else:
            root_ca_path = None  # No TAK server found

        #print("Using TAK Root CA:", root_ca_path)

        context.load_verify_locations(root_ca_path)
        context.check_hostname = False

        try:
            reader, writer = await asyncio.open_connection(s_addr, s_port, ssl=context)

            for msg in cot_messages:
                writer.write(msg.encode('utf-8'))
                await writer.drain()  # Ensure the message is fully sent
                await asyncio.sleep(0.1)  # Prevent message flooding
                # print(msg)

            self.logger.info(f"Sent {len(cot_messages)} CoT messages (latest position + track history)")
            await asyncio.sleep(1.0)  # Add a small delay before closing, prevents [SSL: APPLICATION_DATA_AFTER_CLOSE_NOTIFY] error
            writer.close()
            await writer.wait_closed()

        except Exception as e:
            print(f"Error sending to TAK: {e}")



if __name__ == "__main__":
    rc = 0
    try:
        run()
    except Exception:
        rc = 1

    sys.exit(rc)
