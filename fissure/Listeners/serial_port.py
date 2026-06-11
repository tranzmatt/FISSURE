import asyncio
import serial
import json
import threading


class SerialPortListener:
    def __init__(self, component, listener_name, parameters, loop, alert_callback):
        self.component = component
        self.listener_name = listener_name
        self.loop = loop
        self.alert_callback = alert_callback

        self.port = parameters.get("serial_port", "/dev/ttyUSB0")
        self.baud_rate = int(parameters.get("baud_rate", "9600"))

        self.is_enabled = False
        self.serial_connection = None
        self.read_thread = None

        print(f"Configured Serial Port Listener for {self.port} at {self.baud_rate} baud")


    def enable(self):
        if not self.is_enabled:
            print(f"Enabling Serial Port Listener: {self.listener_name}")
            self.is_enabled = True
            try:
                self.serial_connection = serial.Serial(self.port, self.baud_rate, timeout=1)
                self.read_thread = threading.Thread(target=self.read_from_serial, daemon=True)
                self.read_thread.start()
                print(f"Connected to serial port {self.port}")
            except Exception as e:
                print(f"Error connecting to serial port {self.port}: {e}")


    def disable(self):
        if self.is_enabled:
            print(f"Disabling Serial Port Listener: {self.listener_name}")
            self.is_enabled = False
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            self.serial_connection = None


    def is_active(self):
        return self.is_enabled


    def read_from_serial(self):
        print("Listening for data on serial port...")
        try:
            while self.is_enabled and self.serial_connection and self.serial_connection.is_open:
                line = self.serial_connection.readline().decode('utf-8').strip()
                if line:
                    print(f"Received serial data: {line}")
                    asyncio.run_coroutine_threadsafe(self.process_message(line), self.loop)
        except Exception as e:
            print(f"Error reading from serial port {self.port}: {e}")


    async def process_message(self, message):
        try:
            alert_data = json.loads(message)
            alert_text = alert_data.get("alert_text", "")
            node_uid = alert_data.get("node_uid", 0)
            print(f"Alert found: {alert_text} (Node UID: {node_uid})")
            await self.alert_callback(self.component, node_uid=node_uid, alert_text=alert_text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON from serial data: {e}")
