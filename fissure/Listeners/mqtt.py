import asyncio
import json
import paho.mqtt.client as mqtt

class MQTTListener:
    def __init__(self, component, listener_name, parameters, loop, alert_callback):
        self.component = component
        self.listener_name = listener_name
        self.loop = loop
        self.alert_callback = alert_callback

        self.broker_address = parameters.get("broker_address", "localhost")
        self.port = int(parameters.get("port", "1883"))
        self.topic = parameters.get("topic", "fissure/alerts")
        self.username = parameters.get("username", None)
        self.password = parameters.get("password", None)

        self.is_enabled = False
        self.client = None

        print(f"Configured MQTT Listener for {self.broker_address}:{self.port} on topic '{self.topic}'")

    def enable(self):
        if not self.is_enabled:
            print(f"Enabling MQTT Listener: {self.listener_name}")
            self.is_enabled = True
            self.client = mqtt.Client()
            self.client.on_message = self.on_message
            self.client.on_connect = self.on_connect
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            self.client.connect(self.broker_address, self.port, 60)
            self.client.loop_start()

    def disable(self):
        if self.is_enabled:
            print(f"Disabling MQTT Listener: {self.listener_name}")
            self.is_enabled = False
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
                self.client = None

    def is_active(self):
        return self.is_enabled

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected to MQTT Broker with result code {rc}")
        client.subscribe(self.topic)
        print(f"Subscribed to MQTT topic: {self.topic}")

    def on_message(self, client, userdata, msg):
        message = msg.payload.decode('utf-8').strip()
        print(f"Received MQTT message on topic '{msg.topic}': {message}")
        asyncio.run_coroutine_threadsafe(self.process_message(message), self.loop)

    async def process_message(self, message):
        try:
            alert_data = json.loads(message)
            alert_text = alert_data.get("alert_text", "")
            node_uid = alert_data.get("node_uid", 0)
            print(f"Alert found: {alert_text} (Node UID: {node_uid})")
            await self.alert_callback(self.component, node_uid=node_uid, alert_text=alert_text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON from MQTT message: {e}")
