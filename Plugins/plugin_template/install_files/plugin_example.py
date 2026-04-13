#! /usr/bin/env python3
"""Example Plugin Script
This script serves as an example of how to create a plugin script for FISSURE. The script can directly implement functionality or wrap existing code.
"""
import asyncio
import logging
import os
from typing import List, Dict, Any, Union
import uuid

from fissure.Sensor_Node.utils.resources import Resource
import inspect

# Optional: Define default values for arguments
EXAMPLE_ARG = "default_value"
EXAMPLE_ARG2 = 42
EXAMPLE_ARG3 = [1, 2, 3]

class PluginExample(object):
    """
    Example plugin script class

    This class can be modified to implement specific functionality for the plugin.
    """
    def __init__(self, example_arg: str = EXAMPLE_ARG, example_arg2: int = EXAMPLE_ARG2, example_arg3: List[int] = EXAMPLE_ARG3, sensor_node_id: Union[int, str] = 0, logger: logging.Logger = None, alert_callback: callable = None) -> None:
        """
        Initialize the plugin with given keyword arguments.

        Parameters
        ----------
        **kwargs : dict
            Keyword arguments for the plugin script.
        """
        self.logger = logger if logger is not None else logging.getLogger(__name__)
        self.sensor_node_id = sensor_node_id
        self.alert_callback = alert_callback
        self.opid = str(uuid.uuid4())  # Generate a unique operation ID
        self.example_arg = example_arg
        self.example_arg2 = example_arg2
        self.example_arg3 = example_arg3
        self._stop = False
        self._running = None # Use None to indicate that the operation has not started yet

        # define resources
        pid = os.getpid()  # Get the current process ID
        resources = get_resources()
        self.resource = [
            Resource(
                pid=pid,
                op_uuid=self.opid,
                type=res_info.get('type'),
                model=res_info.get('model'),
                serial=res_info.get('serial'),
                logger=self.logger
            )
        for res_name, res_info in resources.items()]

    async def setup(self) -> None:
        """
        Setup the environment for the operation.

        This method can be modified to implement specific setup functionality for the plugin.
        """
        self.logger.info("Setting up operation environment...")
        
        self._resources = [] # track resources that were successfully allocated
        for res in self.resource:
            if not res.allocated:
                if not res.allocate():
                    self.logger.error(f"Failed to allocate resource: {res}")
                    await self.teardown()
                    return False
                self._resources.append(res)
        self.logger.info("Operation environment setup complete.")
        return True

    async def teardown(self) -> None:
        """
        Teardown the environment for the operation.

        This method can be modified to implement specific teardown functionality for the plugin.
        """
        self.logger.info("Tearing down operation environment...")

        if hasattr(self, '_resources'):
            while len(self._resources) > 0:
                res = self._resources.pop()
                res.release()

        self.logger.info("Operation environment teardown complete.")

    async def run(self) -> None:
        """
        Run the plugin functionality.

        This method must be modified to implement specific functionality for the plugin.
        """
        self._running = True
        counter = 0
        while not self._stop:
            # Plugin logic goes here
            report_str = f"{counter:<2} Example Plugin is running...\n\texample_arg: {self.example_arg}\n\texample_arg2: {self.example_arg2}\n\texample_arg3: {self.example_arg3}"
            print(report_str)
            await self.alert_callback(self.sensor_node_id, self.opid, report_str)
            await asyncio.sleep(1)
            counter += 1
        print("Example Plugin stopped.")
        self._running = False

    def running(self) -> bool:
        """
        Check if the plugin is currently running.

        Returns
        -------
        bool
            True if the plugin is running, False otherwise.
        """
        return self._running

    async def stop(self) -> None:
        """
        Stop the plugin functionality.

        This method must be modified to implement specific stop functionality for the plugin.
        """
        self._stop = True

def main(**kwargs) -> object:
    """
    Main function to run the example plugin script.

    This function can be called when the plugin script is executed.

    Parameters
    ----------
    **kwargs : dict
        Keyword arguments for variables in the plugin script.

    Returns
    -------
    object
        An instance of the PluginExample class with the provided arguments.
    """
    # Get input arguments for PluginExample.__init__ from kwargs
    # Only pass arguments that are accepted by PluginExample.__init__
    sig = inspect.signature(PluginExample.__init__)
    valid_args = {k: v for k, v in kwargs.items() if k in sig.parameters and k != 'self'}
    for arg in kwargs:
        if arg not in valid_args:
            kwargs["logger"].warning(f"Warning: Argument '{arg}' is not used by PluginExample and will be ignored.")
    kwargs = valid_args
    kwargs["logger"].info(f"Initializing Example Plugin with arguments: {kwargs}")
    example_plugin = PluginExample(**kwargs)
    return example_plugin

def get_arguments() -> dict:
    """
    Get the arguments for the plugin script.

    This function should be modified to return specific arguments required by the plugin script.

    Returns
    -------
    dict
        A dictionary containing the arguments for the plugin script.
    """
    return {
        'example_arg': {
            'default': EXAMPLE_ARG,
            'type': str,
            'description': 'This is an example argument for the plugin script.',
            'required': True,
            'choices': ['option1', 'option2', 'default_value'],
        },
        'example_arg2': {
            'default': EXAMPLE_ARG2,
            'type': int,
            'description': 'This is another example argument for the plugin script.',
            'required': False,
        },
        'example_arg3': {
            'default': EXAMPLE_ARG3,
            'type': List[int],
            'description': 'This is a list argument for the plugin script. Using Typing for type hinting.',
            'required': False,
            'nargs': '*', # use regex quanitifiers, e.g. '*', '+', '?', or dict {'min': 1, 'max': 3}
        },
    }

def get_resources() -> Dict[str, Any]:
    """
    Get the resources required by the plugin script.

    This function should be modified to return specific resources required by the plugin script. If no resrources are needed, it can return an empty dictionary.

    Returns
    -------
    Dict[str, Any]
        A dictionary containing the resources for the plugin script.
    """
    # Example resources, modify as needed
    return {
        'example_sdr': {
            'type': 'example',
            'model': 'example_model',
            'serial': 'example_serial',
            'description': 'This is an example resource for the plugin script with a specific model and serial number.',
            'required': True
        }
    }

def get_interfaces() -> Dict[str, Any]:
    """
    Get the interfaces available for the plugin script.

    This function should be modified to return specific interfaces required by the plugin script. If no interfaces are needed, it can return an empty dictionary.

    Returns
    -------
    Dict[str, Any]
        A dictionary containing the interfaces for the plugin script.
    """
    return {
        'example_interface': {
            'type': 'alert',
            'channel': 'fissure', # FISSURE zmq
            'direction': 'out',
            'description': 'This is an example interface for the plugin script.'
        }
    }