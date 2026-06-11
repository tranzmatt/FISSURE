import asyncio
import json


class TCPUDPListener:
    def __init__(self, component, listener_name, parameters, loop, alert_callback):
        self.component = component
        self.listener_name = listener_name
        self.loop = loop
        self.alert_callback = alert_callback

        self.ip_address = parameters.get("ip_address", "localhost")
        self.port = int(parameters.get("port", "5000"))
        self.protocol = parameters.get("protocol", "TCP").upper()

        self.is_enabled = False
        self.server = None

        print(f"Configured {self.protocol} Listener for {self.ip_address}:{self.port}")


    def enable(self):
        if not self.is_enabled:
            print(f"Enabling {self.protocol} Listener: {self.listener_name}")
            self.is_enabled = True
            if self.protocol == "TCP":
                asyncio.ensure_future(self.start_tcp_server())
            elif self.protocol == "UDP":
                asyncio.ensure_future(self.start_udp_server())


    def disable(self):
        if self.is_enabled:
            print(f"Disabling {self.protocol} Listener: {self.listener_name}")
            self.is_enabled = False
            if self.server:
                if self.protocol == "UDP":
                    # Properly close the UDP transport
                    transport, _ = self.server
                    transport.close()
                else:
                    # For TCP server
                    self.server.close()
                    asyncio.ensure_future(self.server.wait_closed())
                self.server = None


    def is_active(self):
        return self.is_enabled


    async def start_tcp_server(self):
        self.server = await asyncio.start_server(
            self.handle_tcp_connection, self.ip_address, self.port
        )
        print(f"TCP server started on {self.ip_address}:{self.port}")


    async def handle_tcp_connection(self, reader, writer):
        while self.is_enabled:
            try:
                data = await reader.readline()
                if not data:
                    break
                message = data.decode('utf-8').strip()
                print(f"Received TCP message: {message}")
                await self.process_message(message)
            except Exception as e:
                print(f"Error in TCP connection: {e}")


    async def start_udp_server(self):
        print(f"Starting UDP server on {self.ip_address}:{self.port}")
        loop = asyncio.get_running_loop()
        self.server = await loop.create_datagram_endpoint(
            lambda: UDPHandler(self),
            local_addr=(self.ip_address, self.port)
        )
        

    async def process_message(self, message):
        try:
            alert_data = json.loads(message)
            alert_text = alert_data.get("alert_text", "")
            node_uid = alert_data.get("node_uid", 0)
            print(f"Alert found: {alert_text} (Node UID: {node_uid})")
            await self.alert_callback(self.component, node_uid=node_uid, alert_text=alert_text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON message: {e}")


class UDPHandler(asyncio.DatagramProtocol):
    def __init__(self, listener):
        super().__init__()
        self.listener = listener


    def datagram_received(self, data, addr):
        message = data.decode('utf-8').strip()
        print(f"Received UDP message: {message}")
        asyncio.run_coroutine_threadsafe(self.listener.process_message(message), self.listener.loop)