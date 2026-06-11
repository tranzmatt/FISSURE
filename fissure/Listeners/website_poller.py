import asyncio
import aiohttp
import json

class WebsitePollerListener:
    def __init__(self, component, listener_name, parameters, loop, alert_callback):
        self.component = component
        self.listener_name = listener_name
        self.loop = loop
        self.alert_callback = alert_callback

        self.url = parameters.get("url", "")
        self.check_interval = int(parameters.get("check_interval", "60"))

        self.is_enabled = False
        self.session = None

        self.last_seen_alerts = set()
        print(f"Configured Website Poller for {self.url} with interval {self.check_interval} seconds")

    def enable(self):
        if not self.is_enabled:
            print(f"Enabling Website Poller: {self.listener_name}")
            self.is_enabled = True
            self.session = aiohttp.ClientSession()
            asyncio.ensure_future(self.poll_website())

    def disable(self):
        if self.is_enabled:
            print(f"Disabling Website Poller: {self.listener_name}")
            self.is_enabled = False
            if self.session:
                asyncio.ensure_future(self.session.close())
            self.session = None

    def is_active(self):
        return self.is_enabled

    async def poll_website(self):
        while self.is_enabled:
            try:
                async with self.session.get(self.url) as response:
                    if response.status == 200:
                        content = await response.text()
                        lines = content.strip().split('\n')
                        new_alerts = []
                        for line in lines:
                            try:
                                alert_data = json.loads(line)
                                alert_key = f"{alert_data['node_uid']}:{alert_data['alert_text']}"
                                if alert_key not in self.last_seen_alerts:
                                    print(f"New alert found: {alert_data['alert_text']}")
                                    await self.alert_callback(self.component, node_uid=alert_data['node_uid'], alert_text=alert_data['alert_text'])
                                    new_alerts.append(alert_key)
                            except json.JSONDecodeError as e:
                                print(f"Failed to parse JSON line: {e}")
                        self.last_seen_alerts.update(new_alerts)
                    else:
                        print(f"Failed to fetch {self.url}: Status {response.status}")
            except Exception as e:
                print(f"Error while polling {self.url}: {e}")
            await asyncio.sleep(self.check_interval)
