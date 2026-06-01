#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""WiFi Plugin Actions
"""
import os
import sys
from typing import Any, Dict, Union

from fissure.Sensor_Node.SensorNode import SensorNode
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from wifi_lib.query_iface import choose_interface as _choose_interface # make hidden when action functions are being searched

async def scan(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    WiFi Scan Action

    Parameters
    ----------
    component : SensorNode
        The sensor node instance.
    parameters : Dict[str, Any]
        The parameters for the WiFi scan operation.
    sensor_node_id : Union[int, str], optional
        The ID of the sensor node, by default 0
    """
    component.logger.info(f"WiFi AP scan with parameters: {parameters}")
    parameters['dev'] = _choose_interface(component.logger)
    parameters['dwell'] = parameters.get('dwell', 0.1)
    await component.run_plugin_operation(component, 'wifi', 'wifi_scan_ap.py', parameters, sensor_node_id)