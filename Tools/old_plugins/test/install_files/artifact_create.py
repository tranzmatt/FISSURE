#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""Artifact Creation Test Operation
"""
import asyncio
import logging
import os
import sys
from typing import Callable, Union

try:
    from fissure.utils.plugins.operations import Operation, ArtifactManager
except ImportError:
    # add fissure to path and import modules
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
    from fissure.utils.plugins.operations import Operation, ArtifactManager

class OperationMain(Operation):
    """Artifact Creation Test Operation"""
    def __init__(self, frequency: int = 10, sensor_node_id: Union[int, str] = 0, logger: logging.Logger = logging.getLogger(__name__), alert_callback: Union[Callable, None] = None, tak_cot_callback: Union[Callable, None] = None, artifact_manager: Union[ArtifactManager, None] = None) -> None:
        """Initialize the Artifact Creation Test Operation.

        Parameters
        ----------
        frequency : int, optional
            The frequency in seconds at which to create artifacts, by default 1
        sensor_node_id : Union[int, str], optional
            The ID of the sensor node, by default 0
        logger : logging.Logger, optional
            Logger instance for logging, by default None
        alert_callback : Union[Callable, None], optional
            Callback function for alerts, by default None for logger-only alerts
        tak_cot_callback : Union[Callable, None], optional
            Callback function for TAK CoT messages, by default None for logger-only TAK CoT messages
        artifact_manager : Union[ArtifactManager, None], optional
            ArtifactManager instance for managing artifacts, by default None to use the global artifact manager
        """
        # templated common init
        super().__init__(sensor_node_id=sensor_node_id, logger=logger, alert_callback=alert_callback, tak_cot_callback=tak_cot_callback, artifact_manager=artifact_manager)

        # developer defined init
        self.frequency = int(frequency)

        self._stop = False

    async def run(self) -> None:
        """Run the Artifact Creation Test Operation."""
        self.logger.info("Starting Artifact Creation Test Operation")
        count = 0
        while not self._stop:
            count += 1
            self.logger.info(f"Creating test artifact number {count}")
            art_fname = self.artifact_manager.get_filename_for_artifact(self.opid, '.txt')
            with open(art_fname, 'w') as art_fd:
                self.logger.debug(f"Writing to artifact file: {art_fname}")
                art_fd.write(f"This is test artifact number {count}\n")
            self.logger.debug(f"Finished writing to artifact file: {art_fname}")
            _ = self.create_artifact(
                file_path=art_fname,
                name=f"Test artifact {count}",
                artifact_type="text/plain",
                metadata={"description": f"Test artifact number {count}"}
            )
            self.logger.debug(f"Created artifact {count} with ID {_}")
            self.logger.info(f"Artifact creation test operation count={count}")
            await asyncio.sleep(self.frequency)

if __name__ == "__main__":
    """Run the plugin script as a standalone program for testing purposes.
    """
    from fissure.utils.plugins.test_operation import run_test
    run_test(
        OperationMain,
        {'frequency': 10},
        {}
    )