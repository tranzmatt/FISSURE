#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wi-Fi Plugin Actions"""

from typing import Any, Dict, Union

from fissure.Sensor_Node.SensorNode import SensorNode
from fissure.utils.hardware import get_default_wifi_interface


PLUGIN_NAME = "WiFi"


ACTION_TAGS = {
    "wifi_discovery_edge_light": ["All", "WiFi", "802.11x"],
    "wifi_discovery_edge_oui": ["All", "WiFi", "802.11x"],
    "wifi_discovery_edge_logger": ["All", "WiFi", "802.11x"],
    "wifi_geolocate_target": ["All", "WiFi", "802.11x"],
    "wifi_geolocate_all": ["All", "WiFi", "802.11x"],
}


ACTION_HARDWARE = {
    "wifi_discovery_edge_light": ["802.11x Adapter"],
    "wifi_discovery_edge_oui": ["802.11x Adapter"],
    "wifi_discovery_edge_logger": ["802.11x Adapter"],
    "wifi_geolocate_target": ["802.11x Adapter"],
    "wifi_geolocate_all": ["802.11x Adapter"],
}


def _resolve_wifi_parameters(
    component: SensorNode,
    parameters: Dict[str, Any],
) -> Dict[str, Any]:
    op_params = dict(parameters or {})

    if not op_params.get("wifi_interface"):
        op_params["wifi_interface"] = get_default_wifi_interface(
            component.settings_dict
        )

    return op_params


wifi_discovery_edge_light_schema = {
    "params": [
        {
            "name": "lna_gain_db",
            "label": "LNA Gain (dB)",
            "type": "number",
            "default": 20,
        },
    ]
}

async def wifi_discovery_edge_light(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    component.logger.info(
        f"WiFi light discovery action with parameters: {parameters}"
    )

    op_params = _resolve_wifi_parameters(component, parameters)

    component.logger.info(
        f"Resolved WiFi light discovery parameters: {op_params}"
    )

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "wifi_discovery_edge_light.py",
        {"parameters": op_params},
        node_uid,
    )


wifi_discovery_edge_oui_schema = {
    "params": [
        {
            "name": "oui_filter",
            "label": "OUI Filter",
            "type": "string",
            "default": "00:11:22",
        },
        {
            "name": "alert_on_new_target",
            "label": "Alert on New Target",
            "type": "string",
            "default": "true",
            "options": ["true", "false"],
        },
    ]
}

async def wifi_discovery_edge_oui(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    component.logger.info(
        f"WiFi OUI discovery action with parameters: {parameters}"
    )

    op_params = _resolve_wifi_parameters(component, parameters)

    component.logger.info(
        f"Resolved WiFi OUI discovery parameters: {op_params}"
    )

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "wifi_discovery_edge_oui.py",
        {"parameters": op_params},
        node_uid,
    )


wifi_discovery_edge_logger_schema = {
    "params": [
        {
            "name": "batch_unique_devices",
            "label": "Batch Unique Devices",
            "type": "number",
            "default": 500,
        },
        {
            "name": "min_log_interval_s",
            "label": "Min Log Interval (s)",
            "type": "number",
            "default": 5.0,
        },
        {
            "name": "alert_every_unique",
            "label": "Alert Every Unique Devices",
            "type": "number",
            "default": 100,
        },
        {
            "name": "create_artifacts",
            "label": "Create Artifacts",
            "type": "string",
            "default": "true",
            "options": ["true", "false"],
        },
        {
            "name": "artifact_name_prefix",
            "label": "Artifact Name Prefix",
            "type": "string",
            "default": "Wi-Fi Urban Logger Batch",
        },
    ]
}

async def wifi_discovery_edge_logger(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    component.logger.info(
        f"WiFi urban logger action with parameters: {parameters}"
    )

    op_params = _resolve_wifi_parameters(component, parameters)

    component.logger.info(
        f"Resolved WiFi urban logger parameters: {op_params}"
    )

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "wifi_discovery_edge_logger.py",
        {"parameters": op_params},
        node_uid,
    )


async def wifi_geolocate_target(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    component.logger.info(
        f"WiFi target geolocation action with parameters: {parameters}"
    )

    op_params = _resolve_wifi_parameters(component, parameters)

    component.logger.info(
        f"Resolved WiFi target geolocation parameters: {op_params}"
    )

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "wifi_geolocate_target.py",
        {"parameters": op_params},
        node_uid,
    )


async def wifi_geolocate_all(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    component.logger.info(
        f"WiFi geolocate all action with parameters: {parameters}"
    )

    op_params = _resolve_wifi_parameters(component, parameters)

    component.logger.info(
        f"Resolved WiFi geolocate all parameters: {op_params}"
    )

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "wifi_geolocate_all.py",
        {"parameters": op_params},
        node_uid,
    )