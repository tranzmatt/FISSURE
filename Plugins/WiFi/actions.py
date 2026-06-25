#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wi-Fi Plugin Actions"""

from typing import Any, Dict

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


_COMMON_WIFI_PARAMS = [
    {
        "name": "wifi_interface",
        "label": "Wi-Fi Interface",
        "type": "string",
        "default": "",
    },
]


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)

    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "f", "no", "n", "off"}:
        return False
    return default


def _default_source_id(
    component: SensorNode,
    node_uid: str = "",
) -> str:
    return (
        str(node_uid or "").strip()
        or str(getattr(component, "uuid", "") or "").strip()
        or "sensor_node"
    )


def _resolve_wifi_parameters(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> Dict[str, Any]:
    op_params = dict(parameters or {})

    if not str(op_params.get("wifi_interface", "") or "").strip():
        op_params["wifi_interface"] = get_default_wifi_interface(
            getattr(component, "settings_dict", {}) or {}
        )

    op_params.setdefault("node_uid", node_uid)
    op_params.setdefault("source_id", _default_source_id(component, node_uid))

    return op_params


async def _run_wifi_operation(
    component: SensorNode,
    operation_filename: str,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        operation_filename,
        {"parameters": parameters},
        node_uid,
    )


wifi_discovery_edge_light_schema = {
    "params": _COMMON_WIFI_PARAMS + [
        {
            "name": "lna_gain_db",
            "label": "LNA Gain (dB)",
            "type": "number",
            "default": 20,
        },
        {
            "name": "channel_hop_s",
            "label": "Channel Hop Interval (s)",
            "type": "number",
            "default": 1.0,
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


async def wifi_discovery_edge_light(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    component.logger.info(
        f"WiFi light discovery action with parameters: {parameters}"
    )

    op_params = _resolve_wifi_parameters(component, parameters, node_uid)
    op_params["alert_on_new_target"] = _to_bool(
        op_params.get("alert_on_new_target"),
        default=True,
    )

    component.logger.info(
        f"Resolved WiFi light discovery parameters: {op_params}"
    )

    await _run_wifi_operation(
        component,
        "wifi_discovery_edge_light.py",
        op_params,
        node_uid,
    )


wifi_discovery_edge_oui_schema = {
    "params": _COMMON_WIFI_PARAMS + [
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
        {
            "name": "channel_hop_s",
            "label": "Channel Hop Interval (s)",
            "type": "number",
            "default": 1.0,
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

    op_params = _resolve_wifi_parameters(component, parameters, node_uid)
    op_params["alert_on_new_target"] = _to_bool(
        op_params.get("alert_on_new_target"),
        default=True,
    )

    component.logger.info(
        f"Resolved WiFi OUI discovery parameters: {op_params}"
    )

    await _run_wifi_operation(
        component,
        "wifi_discovery_edge_oui.py",
        op_params,
        node_uid,
    )


wifi_discovery_edge_logger_schema = {
    "params": _COMMON_WIFI_PARAMS + [
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

    op_params = _resolve_wifi_parameters(component, parameters, node_uid)
    op_params["create_artifacts"] = _to_bool(
        op_params.get("create_artifacts"),
        default=True,
    )

    component.logger.info(
        f"Resolved WiFi urban logger parameters: {op_params}"
    )

    await _run_wifi_operation(
        component,
        "wifi_discovery_edge_logger.py",
        op_params,
        node_uid,
    )


wifi_geolocate_target_schema = {
    "params": _COMMON_WIFI_PARAMS + [
        {
            "name": "target_id",
            "label": "Target ID",
            "type": "string",
            "default": "",
        },
        {
            "name": "emit_every_s",
            "label": "Emit Interval (s)",
            "type": "number",
            "default": 1.0,
        },
        {
            "name": "meas_every_s",
            "label": "Measurement Interval (s)",
            "type": "number",
            "default": 0.2,
        },
        {
            "name": "search_similar_targets",
            "label": "Search Similar Targets",
            "type": "string",
            "default": "false",
            "options": ["true", "false"],
        },
    ]
}


async def wifi_geolocate_target(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    component.logger.info(
        f"WiFi target geolocation action with parameters: {parameters}"
    )

    op_params = _resolve_wifi_parameters(component, parameters, node_uid)
    op_params["search_similar_targets"] = _to_bool(
        op_params.get("search_similar_targets"),
        default=False,
    )

    component.logger.info(
        f"Resolved WiFi target geolocation parameters: {op_params}"
    )

    await _run_wifi_operation(
        component,
        "wifi_geolocate_target.py",
        op_params,
        node_uid,
    )


wifi_geolocate_all_schema = {
    "params": _COMMON_WIFI_PARAMS + [
        {
            "name": "target_ids",
            "label": "Target IDs",
            "type": "string",
            "default": "",
        },
        {
            "name": "emit_every_s",
            "label": "Emit Interval (s)",
            "type": "number",
            "default": 1.0,
        },
        {
            "name": "meas_every_s",
            "label": "Measurement Interval (s)",
            "type": "number",
            "default": 0.2,
        },
        {
            "name": "search_similar_targets",
            "label": "Search Similar Targets",
            "type": "string",
            "default": "true",
            "options": ["true", "false"],
        },
    ]
}


async def wifi_geolocate_all(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    component.logger.info(
        f"WiFi geolocate all action with parameters: {parameters}"
    )

    op_params = _resolve_wifi_parameters(component, parameters, node_uid)
    op_params["search_similar_targets"] = _to_bool(
        op_params.get("search_similar_targets"),
        default=True,
    )

    component.logger.info(
        f"Resolved WiFi geolocate all parameters: {op_params}"
    )

    await _run_wifi_operation(
        component,
        "wifi_geolocate_all.py",
        op_params,
        node_uid,
    )