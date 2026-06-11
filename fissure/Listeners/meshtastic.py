import asyncio
import json
import meshtastic
from meshtastic.serial_interface import SerialInterface
from pubsub import pub


class MeshtasticListener:
    def __init__(self, component, listener_name, parameters, loop, alert_callback):
        self.component = component
        self.listener_name = listener_name
        self.loop = loop
        self.alert_callback = alert_callback

        self.serial_port = parameters.get("serial_port", "/dev/ttyUSB0")
        self.baud_rate = int(parameters.get("baud_rate", "115200"))

        self.is_enabled = False
        self.interface = None

        print(f"Configured Meshtastic Listener for {self.serial_port} at {self.baud_rate} baud")


    def enable(self):
        if not self.is_enabled:
            print(f"Enabling Meshtastic Listener: {self.listener_name}")
            self.is_enabled = True
            self.interface = SerialInterface(self.serial_port)
            pub.subscribe(self.on_meshtastic_message, "meshtastic.receive.text")
            print(f"Meshtastic interface established on {self.serial_port}")


    def disable(self):
        if self.is_enabled:
            print(f"Disabling Meshtastic Listener: {self.listener_name}")
            self.is_enabled = False
            if self.interface:
                self.interface.close()
                self.interface = None
            pub.unsubscribe(self.on_meshtastic_message, "meshtastic.receive.text")


    def is_active(self):
        return self.is_enabled


    def on_meshtastic_message(self, packet, interface=None):
        raw_text = packet.get("decoded", {}).get("text", "")
        if raw_text:
            print(f"Received Meshtastic message: {raw_text}")
            asyncio.run_coroutine_threadsafe(self.process_message(raw_text), self.loop)


    async def process_message(self, message):
        try:
            # Replace curly quotes with standard quotes for valid JSON parsing
            message = message.replace('“', '"').replace('”', '"')

            alert_data = json.loads(message)
            alert_text = alert_data.get("alert_text", "")
            node_uid = alert_data.get("node_uid", 0)
            print(f"Alert found: {alert_text} (Node UID: {node_uid})")
            await self.alert_callback(self.component, node_uid=node_uid, alert_text=alert_text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON from Meshtastic message: {e}")
