import os
import json
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from fnmatch import fnmatch


class FilesystemListener:
    def __init__(self, component, listener_name, parameters, loop, alert_callback):
        self.component = component
        self.listener_name = listener_name
        self.loop = loop
        self.alert_callback = alert_callback

        # Determine if monitoring a folder or a specific file
        if "filepath" in parameters:
            self.directory_path = os.path.dirname(parameters["filepath"])
            self.file_pattern = os.path.basename(parameters["filepath"])
            self.mode = "file_changes"  # Set mode to file changes
            # print(f"Configured for specific file monitoring: {self.file_pattern} in {self.directory_path}")
        else:
            self.directory_path = parameters.get("folder", ".")
            self.file_pattern = parameters.get("file_pattern", "*.txt")
            self.mode = "new_files"  # Set mode to new files
            # print(f"Configured for directory monitoring: {self.directory_path} with pattern: {self.file_pattern}")

        self.event_handler = AlertFileHandler(
            component, self.file_pattern, loop, self.alert_callback, mode=self.mode
        )
        self.observer = None  # Initialize as None
        self.is_enabled = False

    def enable(self):
        if not self.is_enabled:
            print(f"Enabling Filesystem Listener: {self.listener_name}")

            # Ensure any previous observer is fully stopped
            if self.observer is not None:
                print("Stopping the existing observer before creating a new one.")
                self.observer.stop()
                self.observer.join()

            # Create a new observer instance
            self.observer = Observer()
            # print(f"Monitoring directory: {self.directory_path}")
            # print(f"Looking for files matching pattern: {self.file_pattern}")
            self.observer.schedule(
                self.event_handler, self.directory_path, recursive=False
            )
            self.observer.start()
            # print("Filesystem observer started")
            self.is_enabled = True

    def disable(self):
        if self.is_enabled and self.observer is not None:
            # print(f"Disabling Filesystem Listener: {self.listener_name}")
            self.observer.stop()
            self.observer.join()
            self.observer = None  # Ensure the old observer is not reused
            self.is_enabled = False

    def is_active(self):
        return self.is_enabled


class AlertFileHandler(FileSystemEventHandler):
    def __init__(self, component, file_pattern, loop, alert_callback, mode="new_files"):
        super().__init__()
        self.component = component
        self.file_pattern = file_pattern
        self.loop = loop
        self.alert_callback = alert_callback
        self.mode = mode  # "new_files" or "file_changes"
        self.file_positions = {}  # Track the last read position for "file_changes" mode

    def on_created(self, event):
        print(f"on_created event triggered for: {event.src_path}")
        if self.mode == "new_files":
            if not event.is_directory and fnmatch(os.path.basename(event.src_path), self.file_pattern):
                # print(f"New file detected: {event.src_path}")
                self.process_file_async(event.src_path, read_all=True)

    def on_modified(self, event):
        # Ignore directory modifications in "file_changes" mode
        if event.is_directory:
            # print(f"Ignoring directory modification event: {event.src_path}")
            return

        print(f"on_modified event triggered for: {event.src_path}")
        if self.mode == "file_changes":
            if fnmatch(os.path.basename(event.src_path), self.file_pattern):
                # print(f"File modified: {event.src_path}")
                self.process_file_async(event.src_path, read_all=False)

    def process_file_async(self, file_path, read_all=False):
        """Helper method to asynchronously process the file."""
        asyncio.run_coroutine_threadsafe(
            self.process_file(file_path, read_all), self.loop
        )

    async def process_file(self, file_path, read_all=False):
        try:
            # print(f"Processing file: {file_path} (Read all: {read_all})")
            
            if file_path not in self.file_positions:
                self.file_positions[file_path] = 0

            with open(file_path, "r") as f:
                if read_all:
                    f.seek(0)  # Read the whole file for new files
                    lines = f.readlines()
                    for line in lines:
                        await self.process_alert(line.strip(), file_path)
                else:
                    # For modified files, read only new lines
                    f.seek(self.file_positions[file_path])  # Move to the last read position
                    lines = f.readlines()
                    self.file_positions[file_path] = f.tell()  # Update the read position

                    if lines:
                        # print(f"Read {len(lines)} new lines, displaying the last one.")
                        await self.process_alert(lines[-1].strip(), file_path)

        except Exception as e:
            print(f"Error processing file {file_path}: {e}")

    async def process_alert(self, line, file_path):
        """Process a single alert line from the file."""
        # print(f"Read line: {line}")
        if line:
            try:
                alert_data = json.loads(line)
                node_uid = alert_data.get("node_uid", 0)
                alert_text = alert_data.get("alert_text", "")
                # print(f"Alert found: {alert_text} (Node ID: {node_uid})")
                await self.alert_callback(self.component, node_uid, alert_text)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON in file {file_path}: {e}")