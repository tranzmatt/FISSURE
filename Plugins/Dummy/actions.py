#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dummy Plugin Actions"""

from typing import Any, Dict, Union

from fissure.Sensor_Node.SensorNode import SensorNode


PLUGIN_NAME = "Dummy"


ACTION_TAGS = {
    "dummy_artifact": ["All"],
    "dummy_alert": ["All"],
    "dummy_alert_burst": ["All"],
    "dummy_detection": ["All"],
    "dummy_soi": ["All"],
    "dummy_target": ["All"],
    "dummy_status": ["All"],
    "dummy_cot_types": ["All"],
}


dummy_artifact_schema = {
    "params": [
        {"name": "file_count", "label": "File Count", "type": "number", "default": 3},
        {"name": "file_size_kb", "label": "File Size (KB)", "type": "number", "default": 64},
        {"name": "description", "label": "Description", "type": "string", "default": "Create a dummy zip artifact"},
    ]
}

async def dummy_artifact(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    component.logger.info(f"Dummy Artifact action with parameters: {parameters}")

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "dummy_artifact.py",
        parameters,
        sensor_node_id,
    )


dummy_alert_schema = {
    "params": [
        {"name": "period_s", "label": "Period (s)", "type": "number", "default": 60.0},
        {"name": "uid", "label": "TAK UID", "type": "string", "default": "dummy_alert"},
        {"name": "description", "label": "Description", "type": "string", "default": "Periodic dummy alert"},
        {
            "name": "plot_pin",
            "label": "Plot as Pin",
            "type": "string",
            "default": "true",
            "option": ["true", "false"],
        },
    ]
}

async def dummy_alert(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    component.logger.info(f"Dummy Alert action with parameters: {parameters}")

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "dummy_alert.py",
        parameters,
        sensor_node_id,
    )


dummy_alert_burst_schema = {
    "params": [
        {"name": "interval_seconds", "label": "Interval (s)", "type": "number", "default": 10},
        {"name": "count", "label": "Count", "type": "number", "default": 10},
        {
            "name": "plot_pin",
            "label": "Plot as Pin",
            "type": "string",
            "default": "true",
            "option": ["true", "false"],
        },
        {"name": "description", "label": "Description", "type": "string", "default": "Dummy alert burst"},
    ]
}

async def dummy_alert_burst(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    component.logger.info(f"Dummy Alert Burst action with parameters: {parameters}")

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "dummy_alert_burst.py",
        parameters,
        sensor_node_id,
    )


dummy_detection_schema = {
    "params": [
        {"name": "period_s", "label": "Period (s)", "type": "number", "default": 60.0},
        {"name": "freq_mhz", "label": "Frequency (MHz)", "type": "number", "default": 915.0},
        {"name": "power_dbm", "label": "Power (dBm)", "type": "number", "default": -40.0},
        {"name": "description", "label": "Description", "type": "string", "default": "Periodic dummy detection"},
    ]
}

async def dummy_detection(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    component.logger.info(f"Dummy Detection action with parameters: {parameters}")

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "dummy_detection.py",
        parameters,
        sensor_node_id,
    )


dummy_soi_schema = {
    "params": [
        {"name": "frequency_mhz", "label": "Frequency (MHz)", "type": "number", "default": 915.0},
        {"name": "model_label", "label": "Model Label", "type": "string", "default": "dummy_protocol"},
        {"name": "model_confidence", "label": "Model Confidence (%)", "type": "number", "default": 87},
        {"name": "description", "label": "Description", "type": "string", "default": "Dummy SOI"},
    ]
}

async def dummy_soi(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    component.logger.info(f"Dummy SOI action with parameters: {parameters}")

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "dummy_soi.py",
        parameters,
        sensor_node_id,
    )


dummy_target_schema = {
    "params": [
        {"name": "frequency_mhz", "label": "Frequency (MHz)", "type": "number", "default": 311.0},
        {
            "name": "display_label",
            "label": "Display Label",
            "type": "string",
            "default": "Garage Door Opener",
            "option": [
                "Garage Door Opener",
                "Key Fob",
                "TPMS",
                "Wireless Camera",
                "Weather Station",
                "Unknown",
            ],
        },
        {"name": "ce_m", "label": "CE (m)", "type": "number", "default": 50.0},
        {"name": "description", "label": "Description", "type": "string", "default": "Dummy Target"},
    ]
}

async def dummy_target(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    component.logger.info(f"Dummy Target action with parameters: {parameters}")

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "dummy_target.py",
        parameters,
        sensor_node_id,
    )


dummy_status_schema = {
    "params": [
        {
            "name": "profile",
            "label": "Profile",
            "type": "string",
            "default": "phases",
            "option": [
                "phases",
                "processing",
                "busy",
                "idle",
            ],
        },
        {"name": "step_s", "label": "Step Duration (s)", "type": "number", "default": 2.0},
        {"name": "description", "label": "Description", "type": "string", "default": "Dummy Status"},
    ]
}

async def dummy_status(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    component.logger.info(f"Dummy Status action with parameters: {parameters}")

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "dummy_status.py",
        parameters,
        sensor_node_id,
    )


dummy_cot_types_schema = {
    "params": [
        {
            "name": "scope",
            "label": "Scope",
            "type": "string",
            "default": "all",
            "option": ["all", "a-*", "b-*"],
        },
        {
            "name": "limit_mode",
            "label": "Limit Mode",
            "type": "string",
            "default": "all",
            "option": ["all", "first_n"],
        },
        {
            "name": "first_n",
            "label": "First N",
            "type": "number",
            "default": 250,
        },
        {
            "name": "expand_dots",
            "label": "Expand '.' Wildcards",
            "type": "string",
            "default": "yes",
            "option": ["yes", "no"],
        },
        {
            "name": "description",
            "label": "Description",
            "type": "string",
            "default": "Dummy CoT Types",
        },
    ]
}

async def dummy_cot_types(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    component.logger.info(f"Dummy CoT Types action with parameters: {parameters}")

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "dummy_cot_types.py",
        parameters,
        sensor_node_id,
    )