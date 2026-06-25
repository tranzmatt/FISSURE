#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mission-01 Plugin Actions

Operator-facing wrapper actions for a curated mission workflow.

Implementation files live in:
- Base
- WiFi
- Dummy

Mission-01 should not contain duplicate operation/install files. These actions
only delegate to operation files in the source plugins.
"""

import uuid
from typing import Any, Dict, List, Tuple

from fissure.Sensor_Node.SensorNode import SensorNode
from fissure.utils.hardware import get_default_wifi_interface
import fissure.utils.hardware


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
    "usrp_b2x0_geolocate": ["All"],

    # Detections
    "fixed_detection": ["All"],
    "scan_detection": ["All"],
    "hackrf_sweep_detection": ["All"],
    "rtl_power_detection": ["All"],
    "lfm_beacon_detection": ["All"],

    # IQ Data
    "iq_record": ["All"],
    "iq_playback": ["All"],

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
    "usrp_b2x0_geolocate": ["USRP B20xmini", "USRP B2x0"],
    "fixed_detection": ["USRP B20xmini", "USRP B2x0"],
    "scan_detection": ["USRP B20xmini", "USRP B2x0"],
    "lfm_beacon_detection": ["RTL2832U"],
    "iq_record": ["USRP B20xmini", "USRP B2x0"],
    "iq_playback": ["USRP B20xmini", "USRP B2x0"],
}


_COMMON_WIFI_PARAMS = [
    {
        "name": "wifi_interface",
        "label": "Wi-Fi Interface",
        "type": "string",
        "default": "",
    },
]


_COMMON_USRP_B2X0_TYPES = ["USRP B20xmini", "USRP B2x0"]


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


def _resolve_compatible_sdr_parameters(
    component: SensorNode,
    parameters: Dict[str, Any],
    compatible_types: List[str],
    *,
    flow_graph_name: str = "",
) -> Dict[str, Any]:
    op_params = dict(parameters or {})

    if str(op_params.get("hardware_type", "") or "").strip():
        return op_params

    sdr_uid, sdr_entry = fissure.utils.hardware.get_compatible_sdr(
        getattr(component, "settings_dict", {}) or {},
        compatible_types,
    )

    if not sdr_entry:
        label = f" for {flow_graph_name}" if flow_graph_name else ""
        raise ValueError(
            f"No compatible SDR configured{label}. Compatible types: {compatible_types}"
        )

    op_params.update(
        fissure.utils.hardware.sdr_entry_to_operation_parameters(
            sdr_uid,
            sdr_entry,
        )
    )

    return op_params


async def _run_operation(
    component: SensorNode,
    plugin_name: str,
    filename: str,
    parameters: Dict[str, Any],
    node_uid: str = "",
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
        node_uid,
        wait=wait,
    )


# =============================================================================
# WiFi
# =============================================================================

wifi_discovery_edge_light_schema = {
    "params": _COMMON_WIFI_PARAMS + [
        {"name": "lna_gain_db", "label": "LNA Gain (dB)", "type": "number", "default": 20},
        {"name": "channel_hop_s", "label": "Channel Hop Interval (s)", "type": "number", "default": 1.0},
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
    op_params = _resolve_wifi_parameters(component, parameters, node_uid)
    op_params["alert_on_new_target"] = _to_bool(
        op_params.get("alert_on_new_target"),
        default=True,
    )

    await _run_operation(
        component,
        WIFI_PLUGIN,
        "wifi_discovery_edge_light.py",
        op_params,
        node_uid,
        wrap_parameters=True,
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
        {"name": "channel_hop_s", "label": "Channel Hop Interval (s)", "type": "number", "default": 1.0},
    ]
}

async def wifi_discovery_edge_oui(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    op_params = _resolve_wifi_parameters(component, parameters, node_uid)
    op_params["alert_on_new_target"] = _to_bool(
        op_params.get("alert_on_new_target"),
        default=True,
    )

    await _run_operation(
        component,
        WIFI_PLUGIN,
        "wifi_discovery_edge_oui.py",
        op_params,
        node_uid,
        wrap_parameters=True,
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
    op_params = _resolve_wifi_parameters(component, parameters, node_uid)
    op_params["create_artifacts"] = _to_bool(
        op_params.get("create_artifacts"),
        default=True,
    )

    await _run_operation(
        component,
        WIFI_PLUGIN,
        "wifi_discovery_edge_logger.py",
        op_params,
        node_uid,
        wrap_parameters=True,
    )


wifi_geolocate_target_schema = {
    "params": _COMMON_WIFI_PARAMS + [
        {"name": "target_id", "label": "Target ID", "type": "string", "default": ""},
        {"name": "emit_every_s", "label": "Emit Interval (s)", "type": "number", "default": 1.0},
        {"name": "meas_every_s", "label": "Measurement Interval (s)", "type": "number", "default": 0.2},
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
    op_params = _resolve_wifi_parameters(component, parameters, node_uid)
    op_params["search_similar_targets"] = _to_bool(
        op_params.get("search_similar_targets"),
        default=False,
    )

    await _run_operation(
        component,
        WIFI_PLUGIN,
        "wifi_geolocate_target.py",
        op_params,
        node_uid,
        wrap_parameters=True,
    )


wifi_geolocate_all_schema = {
    "params": _COMMON_WIFI_PARAMS + [
        {"name": "target_ids", "label": "Target IDs", "type": "string", "default": ""},
        {"name": "emit_every_s", "label": "Emit Interval (s)", "type": "number", "default": 1.0},
        {"name": "meas_every_s", "label": "Measurement Interval (s)", "type": "number", "default": 0.2},
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
    op_params = _resolve_wifi_parameters(component, parameters, node_uid)
    op_params["search_similar_targets"] = _to_bool(
        op_params.get("search_similar_targets"),
        default=True,
    )

    await _run_operation(
        component,
        WIFI_PLUGIN,
        "wifi_geolocate_all.py",
        op_params,
        node_uid,
        wrap_parameters=True,
    )


# =============================================================================
# Base RF / Detection / Geolocation
# =============================================================================

async def signal_geolocate(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "signal_geolocate.py",
        parameters,
        node_uid,
        wrap_parameters=True,
    )


async def lfm_beacon_geolocate(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "lfm_beacon_geolocate.py",
        parameters,
        node_uid,
        wrap_parameters=True,
    )


usrp_b2x0_geolocate_schema = {
    "params": [
        {"name": "target_id", "label": "Target ID", "type": "string", "default": ""},
        {"name": "frequency_mhz", "label": "Frequency (MHz)", "type": "number", "default": 915.0},
        {"name": "sample_rate", "label": "Sample Rate (S/s)", "type": "number", "default": 1000000.0},
        {"name": "gain_db", "label": "RX Gain (dB)", "type": "number", "default": 65.0},
        {"name": "emit_every_s", "label": "Emit Interval (s)", "type": "number", "default": 1.0},
        {"name": "meas_every_s", "label": "Measurement Interval (s)", "type": "number", "default": 0.2},
        {
            "name": "detect_frequency",
            "label": "Detect Frequency",
            "type": "string",
            "default": "true",
            "options": ["true", "false"],
        },
        {
            "name": "description",
            "label": "Description",
            "type": "string",
            "default": "USRP B2x0 geolocation",
        },
    ]
}

async def usrp_b2x0_geolocate(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    op_params = _resolve_compatible_sdr_parameters(
        component,
        parameters,
        _COMMON_USRP_B2X0_TYPES,
        flow_graph_name="usrp_b2x0_geolocate",
    )
    op_params["detect_frequency"] = _to_bool(
        op_params.get("detect_frequency"),
        default=True,
    )

    await _run_operation(
        component,
        BASE_PLUGIN,
        "usrp_b2x0_geolocate.py",
        op_params,
        node_uid,
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
    node_uid: str = "",
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "fixed_detection.py",
        parameters,
        node_uid,
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
    node_uid: str = "",
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "scan_detection.py",
        parameters,
        node_uid,
    )


hackrf_sweep_detection_schema = {
    "params": [
        {
            "name": "band_range_mhz",
            "label": "Band Range (MHz)",
            "type": "string",
            "default": "300-600",
            "options": [
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
    node_uid: str = "",
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "hackrf_sweep_detection.py",
        parameters,
        node_uid,
    )


rtl_power_detection_schema = {
    "params": [
        {
            "name": "segment_range_mhz",
            "label": "Segment Range (MHz)",
            "type": "string",
            "default": "300-600",
            "options": [
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
    node_uid: str = "",
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "rtl_power_detection.py",
        parameters,
        node_uid,
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
    node_uid: str = "",
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "lfm_beacon_detection.py",
        parameters,
        node_uid,
        wait=True,
    )


# =============================================================================
# Base IQ Data
# =============================================================================

iq_record_schema = {
    "params": [
        {
            "name": "flow_graph_name",
            "label": "Flow Graph",
            "type": "string",
            "default": "iq_recorder_b2x0",
            "options": ["iq_recorder_b2x0"],
        },
        {"name": "base_file_name", "label": "Base File Name", "type": "string", "default": "capture.sigmf-data"},
        {"name": "artifact_format", "label": "Artifact Format", "type": "string", "default": "raw", "options": ["raw", "zip"]},
        {"name": "frequency_mhz", "label": "Frequency (MHz)", "type": "number", "default": 915.0},
        {"name": "sample_rate_msps", "label": "Sample Rate (MS/s)", "type": "number", "default": 1.0},
        {"name": "rx_gain", "label": "RX Gain", "type": "number", "default": 70.0},
        {"name": "rx_channel", "label": "RX Channel", "type": "string", "default": "A:A"},
        {"name": "rx_antenna", "label": "RX Antenna", "type": "string", "default": "TX/RX"},
        {"name": "file_length", "label": "File Length", "type": "number", "default": 100000},
        {"name": "number_of_files", "label": "Number of Files", "type": "number", "default": 1},
        {"name": "file_interval", "label": "File Interval (s)", "type": "number", "default": 0.0},
        {"name": "data_type", "label": "Data Type", "type": "string", "default": "Complex Float 32", "options": ["Complex Float 32"]},
        {"name": "sigmf_enabled", "label": "SigMF Enabled", "type": "string", "default": "true", "options": ["true", "false"]},
        {"name": "description", "label": "Description", "type": "string", "default": "IQ recording"},
    ]
}

async def iq_record(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    op_params = dict(parameters or {})
    flow_graph_name = str(
        op_params.get("flow_graph_name", "iq_recorder_b2x0")
        or "iq_recorder_b2x0"
    ).strip()

    if flow_graph_name != "iq_recorder_b2x0":
        raise ValueError(f"Unsupported IQ recorder flow graph: {flow_graph_name}")

    op_params = _resolve_compatible_sdr_parameters(
        component,
        op_params,
        _COMMON_USRP_B2X0_TYPES,
        flow_graph_name=flow_graph_name,
    )

    await _run_operation(
        component,
        BASE_PLUGIN,
        "iq_record.py",
        op_params,
        node_uid,
    )


iq_playback_schema = {
    "params": [
        {
            "name": "flow_graph_name",
            "label": "Flow Graph",
            "type": "string",
            "default": "iq_playback_b2x0",
            "options": ["iq_playback_b2x0", "iq_playback_single_b2x0"],
        },
        {"name": "playback_file_mode", "label": "Playback File Mode", "type": "string", "default": "node_path", "options": ["node_path"]},
        {"name": "filepath", "label": "File Path", "type": "string", "default": ""},
        {"name": "frequency_mhz", "label": "Frequency (MHz)", "type": "number", "default": 915.0},
        {"name": "tx_frequency", "label": "TX Frequency (MHz)", "type": "number", "default": 915.0},
        {"name": "sample_rate_msps", "label": "Sample Rate (MS/s)", "type": "number", "default": 1.0},
        {"name": "tx_gain", "label": "TX Gain", "type": "number", "default": 70.0},
        {"name": "tx_channel", "label": "TX Channel", "type": "string", "default": "A:A"},
        {"name": "tx_antenna", "label": "TX Antenna", "type": "string", "default": "TX/RX"},
        {"name": "data_type", "label": "Data Type", "type": "string", "default": "Complex Float 32", "options": ["Complex Float 32"]},
        {"name": "description", "label": "Description", "type": "string", "default": "IQ playback"},
    ]
}

async def iq_playback(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    op_params = dict(parameters or {})
    flow_graph_name = str(
        op_params.get("flow_graph_name", "iq_playback_b2x0")
        or "iq_playback_b2x0"
    ).strip()

    if flow_graph_name not in {"iq_playback_b2x0", "iq_playback_single_b2x0"}:
        raise ValueError(f"Unsupported IQ playback flow graph: {flow_graph_name}")

    op_params = _resolve_compatible_sdr_parameters(
        component,
        op_params,
        _COMMON_USRP_B2X0_TYPES,
        flow_graph_name=flow_graph_name,
    )

    await _run_operation(
        component,
        BASE_PLUGIN,
        "iq_playback.py",
        op_params,
        node_uid,
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
    node_uid: str = "",
) -> None:
    await _run_operation(
        component,
        BASE_PLUGIN,
        "promote_to_soi.py",
        parameters,
        node_uid,
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
    node_uid: str = "",
) -> None:
    await _run_operation(
        component,
        DUMMY_PLUGIN,
        "dummy_artifact.py",
        parameters,
        node_uid,
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
            "options": ["true", "false"],
        },
    ]
}

async def dummy_alert(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    await _run_operation(
        component,
        DUMMY_PLUGIN,
        "dummy_alert.py",
        parameters,
        node_uid,
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
            "options": ["true", "false"],
        },
        {"name": "description", "label": "Description", "type": "string", "default": "Dummy alert burst"},
    ]
}

async def dummy_alert_burst(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    await _run_operation(
        component,
        DUMMY_PLUGIN,
        "dummy_alert_burst.py",
        parameters,
        node_uid,
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
    node_uid: str = "",
) -> None:
    await _run_operation(
        component,
        DUMMY_PLUGIN,
        "dummy_detection.py",
        parameters,
        node_uid,
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
    node_uid: str = "",
) -> None:
    await _run_operation(
        component,
        DUMMY_PLUGIN,
        "dummy_soi.py",
        parameters,
        node_uid,
    )


dummy_target_schema = {
    "params": [
        {"name": "frequency_mhz", "label": "Frequency (MHz)", "type": "number", "default": 311.0},
        {
            "name": "display_label",
            "label": "Display Label",
            "type": "string",
            "default": "Garage Door Opener",
            "options": [
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
    node_uid: str = "",
) -> None:
    await _run_operation(
        component,
        DUMMY_PLUGIN,
        "dummy_target.py",
        parameters,
        node_uid,
    )


dummy_status_schema = {
    "params": [
        {
            "name": "profile",
            "label": "Profile",
            "type": "string",
            "default": "phases",
            "options": ["phases", "processing", "busy", "idle"],
        },
        {"name": "step_s", "label": "Step Duration (s)", "type": "number", "default": 2.0},
        {"name": "description", "label": "Description", "type": "string", "default": "Dummy Status"},
    ]
}

async def dummy_status(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    await _run_operation(
        component,
        DUMMY_PLUGIN,
        "dummy_status.py",
        parameters,
        node_uid,
    )


dummy_cot_types_schema = {
    "params": [
        {
            "name": "scope",
            "label": "Scope",
            "type": "string",
            "default": "all",
            "options": ["all", "a-*", "b-*"],
        },
        {
            "name": "limit_mode",
            "label": "Limit Mode",
            "type": "string",
            "default": "all",
            "options": ["all", "first_n"],
        },
        {"name": "first_n", "label": "First N", "type": "number", "default": 250},
        {
            "name": "expand_dots",
            "label": "Expand '.' Wildcards",
            "type": "string",
            "default": "yes",
            "options": ["yes", "no"],
        },
        {"name": "description", "label": "Description", "type": "string", "default": "Dummy CoT Types"},
    ]
}

async def dummy_cot_types(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    await _run_operation(
        component,
        DUMMY_PLUGIN,
        "dummy_cot_types.py",
        parameters,
        node_uid,
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
            "options": ["yes", "no"],
        },
        {
            "name": "emit_alert",
            "label": "Emit Alert",
            "type": "string",
            "default": "yes",
            "options": ["yes", "no"],
        },
        {"name": "description", "label": "Description", "type": "string", "default": "Take Photo"},
    ]
}

async def take_photo(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    op_params = dict(parameters or {})
    op_params.setdefault("operation_id", str(uuid.uuid4()))

    await _run_operation(
        component,
        BASE_PLUGIN,
        "take_photo.py",
        op_params,
        node_uid,
        wait=True,
    )


motion_detector_schema = {
    "params": [
        {
            "name": "sensitivity",
            "label": "Sensitivity",
            "type": "string",
            "default": "medium",
            "options": ["low", "medium", "high"],
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
            "options": ["yes", "no"],
        },
        {
            "name": "emit_alert",
            "label": "Emit Alert",
            "type": "string",
            "default": "yes",
            "options": ["yes", "no"],
        },
        {"name": "description", "label": "Description", "type": "string", "default": "Motion Detector"},
    ]
}

async def motion_detector(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    op_params = dict(parameters or {})
    op_params.setdefault("operation_id", str(uuid.uuid4()))

    await _run_operation(
        component,
        BASE_PLUGIN,
        "motion_detector.py",
        op_params,
        node_uid,
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
            "options": ["yes", "no"],
        },
        {
            "name": "emit_alert",
            "label": "Emit Alert",
            "type": "string",
            "default": "yes",
            "options": ["yes", "no"],
        },
        {"name": "description", "label": "Description", "type": "string", "default": "Take Video"},
    ]
}

async def take_video(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    op_params = dict(parameters or {})
    op_params.setdefault("operation_id", str(uuid.uuid4()))

    await _run_operation(
        component,
        BASE_PLUGIN,
        "take_video.py",
        op_params,
        node_uid,
        wait=True,
    )