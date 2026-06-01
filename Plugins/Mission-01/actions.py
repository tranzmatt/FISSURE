#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mission-01 Plugin Actions

Operator-facing wrapper actions for a curated mission workflow.

Implementation files live in:
- Base
- WiFi
- Dummy

Mission-01 should not contain duplicate operation/install files.
"""

from typing import Any, Dict, Union

from fissure.Sensor_Node.SensorNode import SensorNode


BASE_PLUGIN = "Base"
WIFI_PLUGIN = "WiFi"
DUMMY_PLUGIN = "Dummy"


ACTION_TAGS = {
    # WiFi
    "wifi_discovery_edge_light": ["All", "WiFi", "802.11x"],
    "wifi_discovery_edge_oui": ["All", "WiFi", "802.11x"],
    "wifi_discovery_edge_logger": ["All", "WiFi", "802.11x"],
    "wifi_geolocate_target": ["All", "WiFi", "802.11x"],
    "wifi_geolocate_all": ["All", "WiFi", "802.11x"],

    # RF / Geolocation
    "signal_geolocate": ["All"],
    "lfm_beacon_geolocate": ["All"],

    # Detections
    "fixed_detection": ["All"],
    "scan_detection": ["All"],
    "hackrf_sweep_detection": ["All"],
    "rtl_power_detection": ["All"],
    "lfm_beacon_detection": ["All"],

    # SOI / Processing
    "promote_to_soi": ["All"],

    # Dummy / Testing
    "dummy_artifact": ["All"],
    "dummy_alert": ["All"],
    "dummy_alert_burst": ["All"],
    "dummy_detection": ["All"],
    "dummy_soi": ["All"],
    "dummy_target": ["All"],
    "dummy_status": ["All"],
    "dummy_cot_types": ["All"],

    # Camera / Physical
    "take_photo": ["All"],
    "motion_detector": ["All"],
    "take_video": ["All"],
}


ACTION_HARDWARE = {
    "hackrf_sweep_detection": ["HackRF"],
    "rtl_power_detection": ["RTL2832U"],

    "wifi_discovery_edge_light": ["802.11x Adapter"],
    "wifi_discovery_edge_oui": ["802.11x Adapter"],
    "wifi_discovery_edge_logger": ["802.11x Adapter"],
    "wifi_geolocate_target": ["802.11x Adapter"],
    "wifi_geolocate_all": ["802.11x Adapter"],

    "signal_geolocate": ["USRP B20xmini", "USRP B2x0"],
    "fixed_detection": ["USRP B20xmini", "USRP B2x0"],
    "scan_detection": ["USRP B20xmini", "USRP B2x0"],
    "lfm_beacon_detection": ["RTL2832U"],
}


async def _run_operation(
    component: SensorNode,
    plugin_name: str,
    filename: str,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str],
    *,
    wrap_parameters: bool = False,
    wait: bool = False,
) -> None:
    payload = {"parameters": dict(parameters or {})} if wrap_parameters else dict(parameters or {})

    component.logger.info(
        f"Mission-01 delegating to {plugin_name}/{filename} with parameters: {payload}"
    )

    await component.run_plugin_operation(
        component,
        plugin_name,
        filename,
        payload,
        sensor_node_id,
        wait=wait,
    )


# =============================================================================
# WiFi
# =============================================================================

wifi_discovery_edge_light_schema = {
    "params": [
        {"name": "lna_gain_db", "label": "LNA Gain (dB)", "type": "number", "default": 20},
    ]
}

async def wifi_discovery_edge_light(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        WIFI_PLUGIN,
        "wifi_discovery_edge_light.py",
        parameters,
        sensor_node_id,
        wrap_parameters=True,
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
            "option": ["true", "false"],
        },
    ]
}

async def wifi_discovery_edge_oui(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        WIFI_PLUGIN,
        "wifi_discovery_edge_oui.py",
        parameters,
        sensor_node_id,
        wrap_parameters=True,
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
            "option": ["true", "false"],
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
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        WIFI_PLUGIN,
        "wifi_discovery_edge_logger.py",
        parameters,
        sensor_node_id,
        wrap_parameters=True,
    )


async def wifi_geolocate_target(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        WIFI_PLUGIN,
        "wifi_geolocate_target.py",
        parameters,
        sensor_node_id,
        wrap_parameters=True,
    )


async def wifi_geolocate_all(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        WIFI_PLUGIN,
        "wifi_geolocate_all.py",
        parameters,
        sensor_node_id,
        wrap_parameters=True,
    )


# =============================================================================
# Base RF / Detection / Geolocation
# =============================================================================

async def signal_geolocate(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "signal_geolocate.py",
        parameters,
        sensor_node_id,
        wrap_parameters=True,
    )


async def lfm_beacon_geolocate(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "lfm_beacon_geolocate.py",
        parameters,
        sensor_node_id,
        wrap_parameters=True,
    )


fixed_detection_schema = {
    "params": [
        {"name": "freq_mhz", "label": "Frequency (MHz)", "type": "number", "default": 915.0},
        {"name": "min_detection_interval_s", "label": "Min. interval (s)", "type": "number", "default": 10.0},
        {"name": "description", "label": "Description", "type": "string", "default": "Fixed detection"},
    ]
}

async def fixed_detection(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "fixed_detection.py",
        parameters,
        sensor_node_id,
        wait=True,
    )


scan_detection_schema = {
    "params": [
        {"name": "dwell_s", "label": "Dwell (s)", "type": "number", "default": 10.0},
        {"name": "alert_interval_s", "label": "Min Alert Interval (s)", "type": "number", "default": 10.0},
        {"name": "description", "label": "Description", "type": "string", "default": "Scan detection across preset bands"},
    ]
}

async def scan_detection(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "scan_detection.py",
        parameters,
        sensor_node_id,
    )


hackrf_sweep_detection_schema = {
    "params": [
        {
            "name": "band_range_mhz",
            "label": "Band Range (MHz)",
            "type": "string",
            "default": "300-600",
            "option": [
                "1-300",
                "300-600",
                "600-900",
                "900-1500",
                "1500-2000",
                "2000-2600",
                "2600-3000",
            ],
        },
        {"name": "alert_interval_s", "label": "Alert Interval (s)", "type": "number", "default": 5.0},
        {"name": "detection_threshold_db", "label": "Detection Threshold (dB)", "type": "number", "default": 12.0},
        {"name": "description", "label": "Description", "type": "string", "default": "HackRF sweep detection"},
    ]
}

async def hackrf_sweep_detection(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "hackrf_sweep_detection.py",
        parameters,
        sensor_node_id,
    )


rtl_power_detection_schema = {
    "params": [
        {
            "name": "segment_range_mhz",
            "label": "Segment Range (MHz)",
            "type": "string",
            "default": "300-600",
            "option": [
                "24-300",
                "300-600",
                "600-900",
                "900-1200",
                "1200-1500",
                "1500-1764",
            ],
        },
        {"name": "alert_interval_s", "label": "Alert Interval (s)", "type": "number", "default": 5.0},
        {"name": "detection_threshold_db", "label": "Detection Threshold (dB)", "type": "number", "default": 8.0},
        {"name": "description", "label": "Description", "type": "string", "default": "RTL-SDR rtl_power detection"},
    ]
}

async def rtl_power_detection(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "rtl_power_detection.py",
        parameters,
        sensor_node_id,
    )


lfm_beacon_detection_schema = {
    "params": [
        {"name": "freq_mhz", "label": "Frequency (MHz)", "type": "number", "default": 433.0},
        {"name": "min_detection_interval_s", "label": "Min. interval (s)", "type": "number", "default": 1.0},
        {"name": "description", "label": "Description", "type": "string", "default": "LFM beacon detection"},
    ]
}

async def lfm_beacon_detection(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "lfm_beacon_detection.py",
        parameters,
        sensor_node_id,
        wait=True,
    )


# =============================================================================
# Base SOI / Processing
# =============================================================================

promote_to_soi_schema = {
    "params": [
        {"name": "frequency_mhz", "label": "Frequency (MHz)", "type": "number", "default": 915.0},
        {"name": "description", "label": "Description", "type": "string", "default": "Promote to SOI"},
    ]
}

async def promote_to_soi(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "promote_to_soi.py",
        parameters,
        sensor_node_id,
        wait=True,
    )


# =============================================================================
# Dummy
# =============================================================================

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
    await _run_operation(
        component,
        DUMMY_PLUGIN,
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
    await _run_operation(
        component,
        DUMMY_PLUGIN,
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
    await _run_operation(
        component,
        DUMMY_PLUGIN,
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
    await _run_operation(
        component,
        DUMMY_PLUGIN,
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
    await _run_operation(
        component,
        DUMMY_PLUGIN,
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
    await _run_operation(
        component,
        DUMMY_PLUGIN,
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
            "option": ["phases", "processing", "busy", "idle"],
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
    await _run_operation(
        component,
        DUMMY_PLUGIN,
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
        {"name": "first_n", "label": "First N", "type": "number", "default": 250},
        {
            "name": "expand_dots",
            "label": "Expand '.' Wildcards",
            "type": "string",
            "default": "yes",
            "option": ["yes", "no"],
        },
        {"name": "description", "label": "Description", "type": "string", "default": "Dummy CoT Types"},
    ]
}

async def dummy_cot_types(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        DUMMY_PLUGIN,
        "dummy_cot_types.py",
        parameters,
        sensor_node_id,
    )


# =============================================================================
# Base Camera / Physical
# =============================================================================

take_photo_schema = {
    "params": [
        {"name": "count", "label": "Photo Count", "type": "number", "default": 5},
        {"name": "interval_s", "label": "Interval (s)", "type": "number", "default": 0.3},
        {"name": "name", "label": "Artifact Name", "type": "string", "default": "Photo capture evidence"},
        {
            "name": "emit_tak_pin",
            "label": "Emit TAK Pin",
            "type": "string",
            "default": "yes",
            "option": ["yes", "no"],
        },
        {
            "name": "emit_alert",
            "label": "Emit Alert",
            "type": "string",
            "default": "yes",
            "option": ["yes", "no"],
        },
        {"name": "description", "label": "Description", "type": "string", "default": "Take Photo"},
    ]
}

async def take_photo(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "take_photo.py",
        parameters,
        sensor_node_id,
        wait=True,
    )


motion_detector_schema = {
    "params": [
        {
            "name": "sensitivity",
            "label": "Sensitivity",
            "type": "string",
            "default": "medium",
            "option": ["low", "medium", "high"],
        },
        {"name": "max_watch_s", "label": "Max Watch (s)", "type": "number", "default": 300.0},
        {"name": "consecutive_frames", "label": "Consecutive Frames", "type": "number", "default": 3},
        {"name": "photo_count", "label": "Photo Count", "type": "number", "default": 5},
        {"name": "photo_interval_s", "label": "Photo Interval (s)", "type": "number", "default": 0.7},
        {"name": "artifact_name", "label": "Artifact Name", "type": "string", "default": "Motion capture evidence"},
        {
            "name": "emit_tak_pin",
            "label": "Emit TAK Pin",
            "type": "string",
            "default": "yes",
            "option": ["yes", "no"],
        },
        {
            "name": "emit_alert",
            "label": "Emit Alert",
            "type": "string",
            "default": "yes",
            "option": ["yes", "no"],
        },
        {"name": "description", "label": "Description", "type": "string", "default": "Motion Detector"},
    ]
}

async def motion_detector(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "motion_detector.py",
        parameters,
        sensor_node_id,
        wait=True,
    )


take_video_schema = {
    "params": [
        {"name": "duration_s", "label": "Duration (s)", "type": "number", "default": 10.0},
        {"name": "fps", "label": "FPS", "type": "number", "default": 30.0},
        {"name": "artifact_name", "label": "Artifact Name", "type": "string", "default": "Video capture evidence"},
        {
            "name": "emit_tak_pin",
            "label": "Emit TAK Pin",
            "type": "string",
            "default": "yes",
            "option": ["yes", "no"],
        },
        {
            "name": "emit_alert",
            "label": "Emit Alert",
            "type": "string",
            "default": "yes",
            "option": ["yes", "no"],
        },
        {"name": "description", "label": "Description", "type": "string", "default": "Take Video"},
    ]
}

async def take_video(
    component: SensorNode,
    parameters: Dict[str, Any],
    sensor_node_id: Union[int, str] = 0,
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "take_video.py",
        parameters,
        sensor_node_id,
        wait=True,
    )