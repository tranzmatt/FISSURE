#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""TPMS transmitter
"""
import os
import sys
from typing import Any, Dict, Union
import logging

from fissure.utils.plugins.operations_gr import OperationGR

# add gr_flowgraphs
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from gr_flowgraphs.TPMS_FSK_USRPB210_Transmit import TPMS_FSK_USRPB210_Transmit

class OperationMain(OperationGR):
    """TPMS Transmitter
    """
    def __init__(self, dev: str = '', sensor_node_id: Union[int, str] = 0, logger: logging.Logger = logging.getLogger(__name__), alert_callback: callable = None, tak_cot_callback: callable = None) -> None:
        """
        Parameters
        ----------
        dev : str, optional
            The Ettus USRP serial number, by default '' will use the first available device found
        sensor_node_id : Union[int, str], optional
            The ID of the sensor node, by default 0
        logger : logging.Logger, optional
            Logger instance, by default None
        alert_callback : Callable, optional
            Alert callback function, by default None
        tak_cot_callback : Callable, optional
            TAK CoT callback function, by default None
        """
        super().__init__(TPMS_FSK_USRPB210_Transmit, sensor_node_id, logger, alert_callback, tak_cot_callback)
        self.dev = dev

        self.resource_args = {
            'dev': self.dev
        }

    @staticmethod
    def get_resources(dev: str = '') -> Dict[str, Any]:
        """
        Get the resources required by the plugin script.

        Parameters
        ----------
        dev : str
            The network device name (e.g., 'wlan0').

        Returns
        -------
        Dict[str, Any]
            A dictionary containing the resources for the plugin script.
        """
        return {
            'usrp': {
                'type': 'sdr',
                'model': 'USRP B2x0',
                'serial': dev,
                'description': 'Ettus USRP B2x0.',
                'required': True
            }
        }

if __name__ == "__main__":
    """Run the plugin script directly for testing purposes.
    """
    from fissure.utils.plugins.test_operation import run_test
    run_test(
        OperationMain,
        {
            'dev': '31EABF4'
        },
        {
            'dev': '31EABF4'
        }
    )