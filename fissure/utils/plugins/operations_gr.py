#! /usr/bin/env python3
"""GNU Radio Flowgraph Plugin Operations Base Class and Decorators
"""
import asyncio
from gnuradio import gr
import logging
from typing import Union

from fissure.utils.plugins.operations import Operation

def setup_decorator(func):
    """Decorator for setup method in OperationGR class
    """
    async def wrapper(self, *args, **kwargs) -> bool:
        self.logger.debug(f"{self.__class__.__name__} setting up GR top block...")
        # initialize the gr top block
        self.tb_obj = self.tb()

        # call the decorated setup function
        status = await func(self, *args, **kwargs)
        self.logger.debug(f"{self.__class__.__name__} GR top block set up.")
        return status
    return wrapper

def run_decorator(func):
    """Decorator for run method in OperationGR class
    """
    async def wrapper(self, *args, **kwargs) -> None:
        # call the decorated run function
        await func(self, *args, **kwargs)

        self.logger.debug(f"{self.__class__.__name__} GR top block starting...")
        self.tb_obj.start()
        self.logger.debug(f"{self.__class__.__name__} GR top block started.")
        while not self._stop:
            await asyncio.sleep(0.1)
    return wrapper

def stop_decorator(func):
    """Decorator for stop method in OperationGR class
    """
    async def wrapper(self, *args, **kwargs) -> None:
        self.logger.debug(f"{self.__class__.__name__} GR top block stopping...")
        self.tb_obj.stop()
        self.tb_obj.wait()
        self.logger.debug(f"{self.__class__.__name__} GR top block stopped.")

        # call the decorated stop function
        await func(self, *args, **kwargs)
    return wrapper

def teardown_decorator(func):
    """Decorator for teardown method in OperationGR class
    """
    async def wrapper(self, *args, **kwargs) -> None:
        # call the decorated teardown function
        await func(self, *args, **kwargs)

        self.tb_obj = None
        self.logger.debug(f"{self.__class__.__name__} torn down.")
    return wrapper

class OperationGR(Operation):
    """GNU Radio Flowgraph Plugin Operations Base Class
    """
    def __init__(self, tb: gr.top_block, sensor_node_id: Union[int, str] = 0, logger: logging.Logger = logging.getLogger(__name__), alert_callback: callable = None, tak_cot_callback: callable = None) -> None:
        super().__init__(sensor_node_id, logger, alert_callback, tak_cot_callback)
        if not callable(tb):
            logger.error(f"tb {tb} is not callable")
        elif not issubclass(tb, gr.top_block):
            logger.error(f"tb {tb} is not a subclass of gr.top_block")
        self.tb = tb

    def __init_subclass__(cls, **kwargs):
        # apply decorators to subclass methods
        setattr(cls, 'setup', setup_decorator(cls.setup))
        setattr(cls, 'stop', stop_decorator(cls.stop))
        setattr(cls, 'teardown', teardown_decorator(cls.teardown))

    async def run(self) -> None:
        """Run the operation

        The default run method starts the GNU Radio top block and keeps it running until stop is called.
        """
        self.logger.debug(f"{self.__class__.__name__} GR top block starting...")
        self.tb_obj.start()
        self.logger.debug(f"{self.__class__.__name__} GR top block started.")
        while not self._stop:
            await asyncio.sleep(0.1)
