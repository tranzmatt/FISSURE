import asyncio
import zmq
import zmq.asyncio


class ZMQSubscriberListener:
    def __init__(self, component, listener_name, parameters, loop, alert_callback):
        self.component = component
        self.listener_name = listener_name
        self.loop = loop
        self.alert_callback = alert_callback

        self.ip_address = parameters.get("ip_address", "localhost")
        self.port = parameters.get("port", "55555")
        self.topic_filter = parameters.get("topic_filter", "alerts").encode('utf-8')

        self.is_enabled = False

        # ZMQ components
        self.context = None
        self.socket = None

        self.url = f"tcp://{self.ip_address}:{self.port}"
        print(f"Configured ZMQ SUB Listener for {self.url} with topic '{self.topic_filter.decode('utf-8')}'")

    def enable(self):
        if not self.is_enabled:
            print(f"Enabling ZMQ SUB Listener: {self.listener_name}")
            
            # Create a new context and socket
            self.context = zmq.asyncio.Context()
            self.socket = self.context.socket(zmq.SUB)
            
            if self.topic_filter:
                self.socket.setsockopt(zmq.SUBSCRIBE, self.topic_filter)
                print(f"Subscribed to topic: {self.topic_filter.decode('utf-8')}")
            else:
                self.socket.setsockopt(zmq.SUBSCRIBE, b"")
                print("Subscribed to all topics")
            
            try:
                self.socket.connect(self.url)
                print(f"Connected to ZMQ SUB at {self.url}")
            except Exception as e:
                print(f"Failed to connect to {self.url}: {e}")
            
            self.is_enabled = True
            asyncio.ensure_future(self.listen_for_messages())

    def disable(self):
        if self.is_enabled:
            print(f"Disabling ZMQ SUB Listener: {self.listener_name}")
            
            if self.socket:
                self.socket.disconnect(self.url)
                self.socket.close()
                self.socket = None
            
            if self.context:
                self.context.term()
                self.context = None
            
            self.is_enabled = False

    def is_active(self):
        return self.is_enabled

    async def listen_for_messages(self):
        try:
            print("Listening for messages...")
            while self.is_enabled:
                message = await self.socket.recv()
                print(f"Raw message received: {message}")
                await self.process_message(message)
        except Exception as e:
            print(f"Error in ZMQ SUB Listener '{self.listener_name}': {e}")

    async def process_message(self, message):
        try:
            # ZMQ messages often include the topic as the first part
            topic, alert_text = message.split(b' ', 1)
            alert_text = alert_text.decode('utf-8').strip()
            print(f"Received message on topic '{topic.decode('utf-8')}': {alert_text}")

            # Call the alert callback to forward to the dashboard
            await self.alert_callback(self.component, node_uid="", alert_text=alert_text)
        except Exception as e:
            print(f"Failed to process ZMQ message: {e}")