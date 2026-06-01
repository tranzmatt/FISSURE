#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""TPMS Receiver
"""
import asyncio
import json
import logging
from multiprocessing import Process
import socket
import subprocess
from typing import Any, Dict, Union

from fissure.utils.hardware import findRTL2832U
from fissure.utils.plugins.operations import Operation

class OperationMain(Operation):
    """TPMS Receiver
    """
    def __init__(self, dev: str, frequency: float = 315e6, gain: float = 49, whitelist: list[str] = None, sensor_node_id: Union[int, str] = 0, logger: logging.Logger = logging.getLogger(__name__), alert_callback=None, tak_cot_callback=None) -> None:
        """
        Parameters
        ----------
        dev : str
            RTL-SDR device serial number
        frequency : float, optional
            Frequency to listen on (typically 315e6 or 433e6), by default 315e6
        gain : float, optional
            RTL-SDR gain, by default 49
        whitelist : list[str], optional
            List of TPMS IDs to report, by default None (report all)
        sensor_node_id : Union[int, str], optional
            The ID of the sensor node, by default 0
        logger : logging.Logger, optional
            Logger instance, by default logging.getLogger(__name__)
        alert_callback : Callable, optional
            Alert callback function, by default None
        tak_cot_callback : Callable, optional
            TAK CoT callback function, by default None
        """
        super().__init__(sensor_node_id=sensor_node_id, logger=logger, alert_callback=alert_callback, tak_cot_callback=tak_cot_callback)
        self.dev = dev
        self.frequency = float(frequency)
        self.gain = float(gain)
        if whitelist == 'None' or whitelist is None:
            self.whitelist = None
        elif isinstance(whitelist, str):
            self.whitelist = whitelist.strip('[]').split(',')
        else:
            self.whitelist = whitelist

        # ensure device is present
        scan_results, _ = findRTL2832U(guess_serial=self.dev)
        if not scan_results[3] == self.dev:
            self.logger.error(f"RTL2832U device with serial {self.dev} not found. Available devices: {scan_results}")

        # prepare tpms receiver command
        self.cmd = ['rtl_433', '-d', f':{dev}', '-M', 'level', '-f', f'{frequency}', '-g', f'{gain}', '-v', '-F', 'syslog:127.0.0.1:1514']

        self.resource_args = {
            'dev': self.dev
        }

    @staticmethod
    def get_resources(dev: str = '') -> Dict[str, Any]:
        """Get resources for the operation

        Parameters
        ----------
        dev : str
            Device serial number

        Returns
        -------
        Dict[str, Any]
            Resources dictionary
        """
        return {
            'rtl': {
                'type': 'sdr',
                'model': 'RTL2832U',
                'serial': dev,
                'description': 'RTL-SDR device',
                'required': True
            }
        }

    @staticmethod
    def get_interfaces() -> Dict[str, Any]:
        """
        Get the interfaces available for the plugin script.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing the interfaces for the plugin script.
        """
        return {
            'alert': {
                'type': 'alert',
                'channel': 'fissure', # FISSURE zmq
                'direction': 'out',
                'description': 'TPMS detections.'
            },
            'tak': {
                'type': 'tak',
                'channel': 'fissure', # FISSURE zmq
                'direction': 'out',
                'description': 'TPMS detections in TAK CoT format.'
            }
        }

    async def run(self) -> None:
        """Run the operation
        """
        # start rtl_433 process
        self.logger.debug(f"Starting rtl_433 with command: {' '.join(self.cmd)}")
        self.rtl_433_stdout = asyncio.Queue()
        def run_rtl_433(cmd, queue):
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                queue.put_nowait(line)
            proc.stdout.close()
            proc.wait()
        self.rtl_433 = Process(target=run_rtl_433, args=(' '.join(self.cmd), self.rtl_433_stdout))
        self.rtl_433.start()

        # parse messages
        self.logger.debug("Binding to UDP socket on localhost:1514...")
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.client_socket.bind(('localhost', 1514))
            self.client_socket.setblocking(False)
            self.client_socket.settimeout(0)
        except OSError as e:
            if 'Errno 98' in str(e): # address already in use
                subprocess.run(['fuser', '-k', '1514/udp']) # kill as user
                try:
                    self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self.client_socket.bind(('localhost', 1514))
                except OSError as e:
                    if 'Errno 98' in str(e): # address already in use
                        subprocess.run(['sudo', 'fuser', '-k', '1514/udp']) # kill as sudo
                        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        self.client_socket.bind(('localhost', 1514))
                    else:
                        self.logger.error(f"Failed to bind UDP socket: {e}")
            else:
                self.logger.error(f"Failed to bind UDP socket: {e}")

        self.logger.info("TPMS Receiver started and listening for data.")
        while not self._stop:
            await asyncio.sleep(0)
            if self._stop:
                self.logger.info(f"Stop signal received. Stopping {self.__class__.__name__} channel scan...")
                break

            # non-blocking receive
            try:
                data = self.client_socket.recvfrom(512)
            except BlockingIOError:
                continue
            except socket.timeout:
                continue
            except Exception as e:
                self.logger.error(f"Socket error: {e}")
                return
            if not data:
                continue

            self.logger.debug(f"Received data: {data}")
            data = data[0].decode('utf-8')
            data = json.loads(data[data.index('rtl_433 - - - {') + 14:])

            # Find the actual key that matches "id" (case-insensitive)
            id_key = None
            for key in data.keys():
                if 'id' in key.lower():
                    id_key = key
                    break
            if id_key is not None:
                id = data.pop(id_key)
                if self.whitelist is None or id in self.whitelist:
                    # Find any key that contains "pressure" (case-insensitive)
                    pressure_key = next((key for key in data.keys() if "pressure" in key.lower()), None)
                    self.logger.debug(f"TPMS id={id} {pressure_key}={data.get(pressure_key)}")

                    if pressure_key is not None:
                        await self.alert_callback(self.sensor_node_id, self.opid, f"TPMS id={id} {pressure_key}={data.get(pressure_key)}")

                        # remove time field to avoid confusion with TAK time field
                        if 'time' in data.keys():
                            _ = data.pop('time')

                        await self.tak_cot_callback(self.sensor_node_id, self.opid, uid=id, remarks=json.dumps(data, separators=(',', ':')), lat=True, lon=True, alt=True, time=True, type='a-h-G-E-S')

    async def stop(self) -> None:
        """Stop the operation
        """
        if hasattr(self, 'client_socket') and self.client_socket:
            self.client_socket.close()
        if hasattr(self, 'rtl_433'):
            self.rtl_433.terminate()

if __name__ == "__main__":
    """Run the plugin script directly for testing purposes.
    """
    from fissure.utils.plugins.test_operation import run_test
    run_test(
        OperationMain,
        {
            'dev': '00000001',
            'frequency': 315e6,
            'gain': 49,
            'whitelist': None,
            'logger': logging.getLogger('OperationMain')
        },
        {
            'dev': '00000001'
        }
    )