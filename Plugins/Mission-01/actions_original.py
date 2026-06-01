#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mission-01 Plugin Actions
"""
import os
import sys
from typing import Any, Dict, Union

from fissure.Sensor_Node.SensorNode import SensorNode
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from wifi_lib.query_iface import choose_interface as _choose_interface # make hidden when action functions are being searched

from fissure.utils import FISSURE_ROOT
from fissure.utils.hardware import get_default_wifi_interface

import json
import uuid
import time
import glob


ACTION_TAGS = {
    # Examples
    # "record_iq": ["All"],
    # "garage_door_capture": ["Garage Door Opener"],
    # "tpms_scan": ["TPMS"],
    # "wifi_scan": ["WiFi", "802.11x"],

    # WiFi
    "wifi_discovery_edge_light": ["All"],
    "wifi_discovery_edge_oui": ["All"],
    "wifi_discovery_edge_logger": ["All"],
    "wifi_geolocate_target": ["All"],
    "wifi_geolocate_all": ["All"],

    # RF / Geolocation
    "signal_geolocate": ["All"],

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

    # These are generic / no filtering needed, so omit them:
    # "dummy_alert": ...
    # "dummy_status": ...
    # "dummy_target": ...
}


wifi_discovery_edge_light_schema = {
    "params": [
        {"name": "lna_gain_db", "label": "LNA Gain (dB)", "type": "number", "default": 20},
    ]
}
async def wifi_discovery_edge_light(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    This version is intended for lighter-volume environments.

    Behavior:
    - Creates targets for discovered Wi-Fi APs after a minimum sample count
    - Does NOT create artifacts
    - Sends one alert per newly created Wi-Fi target via alert_callback
    - Does NOT send separate TAK alert pins

    Parameters
    ----------
    component : SensorNode
        The sensor node instance.
    parameters : Dict[str, Any]
        The parameters for the WiFi geolocation operation.
    sensor_node_id : Union[int, str], optional
        The ID of the sensor node, by default 0
    """
    component.logger.info(f"WiFi AP geolocation with parameters: {parameters}")

    op_params = dict(parameters or {})

    if not op_params.get("wifi_interface"):
        op_params["wifi_interface"] = get_default_wifi_interface(component.settings_dict)

    component.logger.info(f"Resolved WiFi geolocation operation parameters: {op_params}")

    await component.run_plugin_operation(
        component,
        'Mission-01',
        'wifi_discovery_edge_light.py',
        {"parameters": op_params},
        sensor_node_id,
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
    sensor_node_id: Union[int, str] = 0
) -> None:
    """
    WiFi Discovery Action filtered by OUI.

    Behavior:
    - Only processes APs matching the provided OUI prefix list
    - Creates targets for matching APs
    - Sends one table-only alert per newly created Wi-Fi target
    - Does NOT create artifacts
    - Does NOT perform edge geolocation
    """
    component.logger.info(f"WiFi OUI discovery with parameters: {parameters}")

    op_params = dict(parameters or {})

    if not op_params.get("wifi_interface"):
        op_params["wifi_interface"] = get_default_wifi_interface(component.settings_dict)

    component.logger.info(f"Resolved WiFi OUI discovery parameters: {op_params}")

    await component.run_plugin_operation(
        component,
        'Mission-01',
        'wifi_discovery_edge_oui.py',
        {"parameters": op_params},
        sensor_node_id,
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
    sensor_node_id: Union[int, str] = 0
) -> None:
    """
    WiFi urban/high-volume logger.

    Behavior:
    - Does NOT create targets
    - Does NOT geolocate
    - Maintains one summarized record per BSSID per batch
    - Throttles repeated updates for the same device
    - Writes periodic CSV batches of Wi-Fi observations
    - Sends summary alerts at configured unique-device intervals
    - Optionally packages each batch as a zip artifact
    """
    component.logger.info(f"WiFi urban logger with parameters: {parameters}")

    op_params = dict(parameters or {})

    if not op_params.get("wifi_interface"):
        op_params["wifi_interface"] = get_default_wifi_interface(component.settings_dict)

    component.logger.info(f"Resolved WiFi urban logger parameters: {op_params}")

    await component.run_plugin_operation(
        component,
        'Mission-01',
        'wifi_discovery_edge_logger.py',
        {"parameters": op_params},
        sensor_node_id,
    )


async def wifi_geolocate_target(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    WiFi Geolocation of a Single Target using Hub Multilateration and Multiple Nodes.

    Parameters
    ----------
    component : SensorNode
        The sensor node instance.
    parameters : Dict[str, Any]
        The parameters for the WiFi geolocation operation.
    sensor_node_id : Union[int, str], optional
        The ID of the sensor node, by default 0
    """
    component.logger.info(f"WiFi AP geolocation with parameters: {parameters}")

    op_params = dict(parameters or {})

    if not op_params.get("wifi_interface"):
        op_params["wifi_interface"] = get_default_wifi_interface(component.settings_dict)

    component.logger.info(f"Resolved WiFi geolocation operation parameters: {op_params}")

    await component.run_plugin_operation(
        component,
        'Mission-01',
        'wifi_geolocate_target.py',
        {"parameters": op_params},
        sensor_node_id,
    )


async def wifi_geolocate_all(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    WiFi Geolocation Action that Updates All Known Targets

    Parameters
    ----------
    component : SensorNode
        The sensor node instance.
    parameters : Dict[str, Any]
        The parameters for the WiFi geolocation operation.
    sensor_node_id : Union[int, str], optional
        The ID of the sensor node, by default 0
    """
    component.logger.info(f"WiFi AP geolocation with parameters: {parameters}")

    op_params = dict(parameters or {})

    if not op_params.get("wifi_interface"):
        op_params["wifi_interface"] = get_default_wifi_interface(component.settings_dict)

    component.logger.info(f"Resolved WiFi geolocation operation parameters: {op_params}")

    await component.run_plugin_operation(
        component,
        'Mission-01',
        'wifi_geolocate_all.py',
        {"parameters": op_params},
        sensor_node_id,
    )


async def usrp_b2x0_geolocate(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    USRP B2x0 Geolocation of a Single Target using Hub Multilateration.

    Parameters
    ----------
    component : SensorNode
        The sensor node instance.
    parameters : Dict[str, Any]
        The parameters for the geolocation operation.
        Expected to be supplied by the hub from the selected target.
    sensor_node_id : Union[int, str], optional
        The ID of the sensor node, by default 0
    """
    component.logger.info(f"USRP B2x0 geolocation with parameters: {parameters}")

    op_params = dict(parameters or {})

    component.logger.info(f"Resolved USRP B2x0 geolocation operation parameters: {op_params}")

    await component.run_plugin_operation(
        component,
        'Mission-01',
        'usrp_b2x0_geolocate.py',
        {"parameters": op_params},
        sensor_node_id,
    )


dummy_artifact_schema = {
    "params": [
        {"name": "file_count", "label": "File Count", "type": "number", "default": 3},
        {"name": "file_size_kb", "label": "File Size (KB)", "type": "number", "default": 64},
        {"name": "description", "label": "Description", "type": "string", "default": "Create a dummy zip artifact"},
    ]
}
async def dummy_artifact(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    Dummy Artifact Action

    Parameters
    ----------
    component : SensorNode
        The sensor node instance.
    parameters : Dict[str, Any]
        The parameters for the Dummy Artifact operation.
    sensor_node_id : Union[int, str], optional
        The ID of the sensor node, by default 0
    """
    component.logger.info(f"Dummy Artifact action with parameters: {parameters}")
    await component.run_plugin_operation(component, 'Mission-01', 'dummy_artifact.py', parameters, sensor_node_id)


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
async def dummy_alert(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    Dummy Alert Action

    Parameters
    ----------
    component : SensorNode
        The sensor node instance.
    parameters : Dict[str, Any]
        The parameters for the Dummy Alert operation.
    sensor_node_id : Union[int, str], optional
        The ID of the sensor node, by default 0
    """
    component.logger.info(f"Dummy Alert action with parameters: {parameters}")
    await component.run_plugin_operation(component, 'Mission-01', 'dummy_alert.py', parameters, sensor_node_id)


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
async def dummy_alert_burst(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    Dummy Alert Burst Action

    Parameters
    ----------
    component : SensorNode
        The sensor node instance.
    parameters : Dict[str, Any]
        The parameters for the Dummy Alert Burst operation.
    sensor_node_id : Union[int, str], optional
        The ID of the sensor node, by default 0
    """
    component.logger.info(f"Dummy Alert Burst action with parameters: {parameters}")
    await component.run_plugin_operation(component, 'Mission-01', 'dummy_alert_burst.py', parameters, sensor_node_id)


dummy_detection_schema = {
    "params": [
        {"name": "period_s", "label": "Period (s)", "type": "number", "default": 60.0},
        {"name": "freq_mhz", "label": "Frequency (MHz)", "type": "number", "default": 915.0},
        {"name": "power_dbm", "label": "Power (dBm)", "type": "number", "default": -40.0},
        {"name": "description", "label": "Description", "type": "string", "default": "Periodic dummy detection"},
    ]
}
async def dummy_detection(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    Dummy Detection Action

    Parameters
    ----------
    component : SensorNode
        The sensor node instance.
    parameters : Dict[str, Any]
        The parameters for the Dummy Detection operation.
    sensor_node_id : Union[int, str], optional
        The ID of the sensor node, by default 0
    """
    component.logger.info(f"Dummy Detection action with parameters: {parameters}")
    await component.run_plugin_operation(component, 'Mission-01', 'dummy_detection.py', parameters, sensor_node_id)


fixed_detection_schema = {
    "params": [
        {"name": "freq_mhz", "label": "Frequency (MHz)", "type": "number", "default": 915.0},
        {"name": "min_detection_interval_s", "label": "Min. interval (s)", "type": "number", "default": 10.0},
        {"name": "description", "label": "Description", "type": "string", "default": "Fixed detection"},
    ]
}
async def fixed_detection(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    Fixed Detection Action

    Parameters
    ----------
    component : SensorNode
        The sensor node instance.
    parameters : Dict[str, Any]
        The parameters for the Fixed Detection operation.
    sensor_node_id : Union[int, str], optional
        The ID of the sensor node, by default 0
    """
    component.logger.info(f"Fixed Detection action with parameters: {parameters}")
    await component.run_plugin_operation(component, 'Mission-01', 'fixed_detection.py', parameters, sensor_node_id, wait=True)


scan_detection_schema = {
    "params": [
        {"name": "dwell_s", "label": "Dwell (s)", "type": "number", "default": 10.0},
        {"name": "alert_interval_s", "label": "Min Alert Interval (s)", "type": "number", "default": 10.0},
        {"name": "description", "label": "Description", "type": "string", "default": "Scan detection across preset bands"},
    ]
}
async def scan_detection(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    Scan Detection Action

    Parameters
    ----------
    component : SensorNode
        The sensor node instance.
    parameters : Dict[str, Any]
        The parameters for the Scan Detection operation.
    sensor_node_id : Union[int, str], optional
        The ID of the sensor node, by default 0
    """
    component.logger.info(f"Scan Detection action with parameters: {parameters}")
    await component.run_plugin_operation(component, 'Mission-01', 'scan_detection.py', parameters, sensor_node_id)


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
async def hackrf_sweep_detection(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    hackrf_sweep Detection Action

    Parameters
    ----------
    component : SensorNode
        The sensor node instance.
    parameters : Dict[str, Any]
        The parameters for the hackrf_sweep Detection operation.
    sensor_node_id : Union[int, str], optional
        The ID of the sensor node, by default 0
    """
    component.logger.info(f"hackrf_sweep Detection action with parameters: {parameters}")
    await component.run_plugin_operation(component, 'Mission-01', 'hackrf_sweep_detection.py', parameters, sensor_node_id)



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
async def rtl_power_detection(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    rtl_power Detection Action

    Parameters
    ----------
    component : SensorNode
        The sensor node instance.
    parameters : Dict[str, Any]
        The parameters for the rtl_power Detection operation.
    sensor_node_id : Union[int, str], optional
        The ID of the sensor node, by default 0
    """
    component.logger.info(f"rtl_power Detection action with parameters: {parameters}")
    await component.run_plugin_operation(component, 'Mission-01', 'rtl_power_detection.py', parameters, sensor_node_id)


promote_to_soi_schema = {
    "params": [
        {"name": "frequency_mhz", "label": "Frequency (MHz)", "type": "number", "default": 915.0},
        {"name": "description", "label": "Description", "type": "string", "default": "Promote to SOI"},
    ]
}
async def promote_to_soi(component: "SensorNode", parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    Promotes a detected frequency to a SOI, runs capture + feature extraction + ML classification,
    bundles evidence, and reports lifecycle updates back to HIPRFISR.

    Key semantics
    -------------
    soi_id        : stable lifecycle ID (uuid4) generated immediately (WinTAK row key)
    operation_id  : capture operation id (op1_id) once signal conditioning completes
    artifact_id   : evidence zip artifact id once registered
    model_confidence: percent integer (0–100)
    """

    component.logger.info(f"Promote to SOI action with parameters: {parameters}")

    # ==============================================================
    # 0) Normalize inputs + create stable SOI lifecycle ID
    # ==============================================================

    freq = parameters.get("frequency_mhz")
    if freq is None:
        raise ValueError("Missing required parameter: frequency_mhz")

    # Normalize: WinTAK sends strings; coerce early
    try:
        freq = float(freq)
    except Exception:
        raise ValueError(f"Invalid frequency_mhz: {freq!r}")

    data_type = parameters.get("data_type", "Complex Float 32")

    soi_id = str(uuid.uuid4())

    operation_id = ""
    artifact_id = ""
    model_label = None
    model_conf_pct = None

    STAGE_ORDER = {
        "STARTED": 10,
        "CAPTURE_COMPLETE": 20,
        "FEATURES_READY": 30,
        "MODEL_ANALYZED": 40,
        "EVIDENCE_READY": 50,
        "FAILED": 90,
    }

    async def _send(status: str, stage: str, extra: Dict[str, Any] = None) -> None:
        summary = {
            "stage": stage,
            "stage_order": STAGE_ORDER.get(status, 0),
            "folder": None,
            "files_present": None,
            "model_classification": model_label,
            "model_confidence": model_conf_pct,
        }
        if extra:
            summary.update(extra)

        try:
            await component.send_soi_update(
                sensor_node_id=sensor_node_id,
                soi_id=soi_id,
                frequency_mhz=freq,
                status=status,
                operation_id=operation_id,
                artifact_id=artifact_id,
                summary=summary,
                lat=True,
                lon=True,
                alt=True,
                observation_time=True,
            )
        except Exception:
            component.logger.exception(f"SOI update failed (status={status})")

    # ==============================================================
    # Helpers: abort gate + prerequisite checks
    # ==============================================================

    def _has_capture_files(folder: str) -> bool:
        if not folder or not os.path.isdir(folder):
            return False
        try:
            for name in os.listdir(folder):
                p = os.path.join(folder, name)
                if os.path.isfile(p) and os.path.getsize(p) > 0:
                    return True
        except Exception:
            return False
        return False


    def _exists(folder: str, filename: str) -> bool:
        return bool(folder) and os.path.isfile(os.path.join(folder, filename))

    async def _abort(stage: str, msg: str) -> None:
        component.logger.warning(msg)
        await _send(status="FAILED", stage=stage, extra={"error": msg})

    # ==============================================================
    # 1) STARTED (row appears immediately)
    # ==============================================================

    await _send(
        status="STARTED",
        stage="starting",
        extra={"files_present": False},
    )

    # ==============================================================
    # 2) Signal conditioning / capture (op1)
    # ==============================================================

    try:
        op1_params = {"frequency_mhz": freq}

        op1_id = await component.run_plugin_operation(
            component,
            "Mission-01",
            "signal_conditioning.py",
            op1_params,
            sensor_node_id,
            wait=True,
        )

        operation_id = op1_id
        capture_folder = os.path.join(FISSURE_ROOT, "artifacts", op1_id, "files")

        # NEW: hard gate — if user hit stop and capture exited early, don't proceed
        if not _has_capture_files(capture_folder):
            await _abort(
                stage="capture_failed",
                msg=f"Capture produced no files (likely stopped/aborted). folder={capture_folder}",
            )
            return

        await _send(
            status="CAPTURE_COMPLETE",
            stage="capture_complete",
            extra={
                "folder": capture_folder,
                "files_present": True,
            },
        )

    except Exception as e:
        component.logger.error(f"signal_conditioning failed: {e!r}")
        await _send(status="FAILED", stage="capture_failed", extra={"error": repr(e)})
        return

    # ==============================================================
    # 3) Feature extraction (op2)
    # ==============================================================

    try:
        op2_params = {
            "folder": capture_folder,
            "data_type": data_type,
        }

        await component.run_plugin_operation(
            component,
            "Mission-01",
            "feature_extraction.py",
            op2_params,
            sensor_node_id,
            wait=True,
        )

        # NEW: hard gate — do not proceed if features are missing
        if not _exists(capture_folder, "tsi_features.json"):
            await _abort(
                stage="features_failed",
                msg=f"Feature extraction did not produce tsi_features.json (likely stopped/aborted). folder={capture_folder}",
            )
            return

        await _send(
            status="FEATURES_READY",
            stage="features_ready",
            extra={
                "folder": capture_folder,
                "features_file": "tsi_features.json",
            },
        )

    except Exception as e:
        component.logger.error(f"feature_extraction failed: {e!r}")
        await _send(status="FAILED", stage="features_failed", extra={"folder": capture_folder, "error": repr(e)})
        return

    # ==============================================================
    # 4) Model classification (op3)
    # ==============================================================

    try:
        op3_params = {
            "folder": capture_folder,
            "features_file": "tsi_features.json",
            "min_models": 2,
            "use_batch_consensus": True,
        }

        await component.run_plugin_operation(
            component,
            "Mission-01",
            "classify_features_dt.py",
            op3_params,
            sensor_node_id,
            wait=True,
        )

        # NEW (recommended): hard gate — classifier should produce the report
        report_path = os.path.join(capture_folder, "classification_report.json")
        if not os.path.isfile(report_path):
            await _abort(
                stage="classification_failed",
                msg=f"Classifier did not produce classification_report.json. folder={capture_folder}",
            )
            return

        # Read rollup
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                rep = json.load(f)
            model_label = rep.get("batch", {}).get("label")
            conf01 = rep.get("batch", {}).get("confidence")
            model_conf_pct = round(conf01 * 100) if conf01 is not None else None
        except Exception as e:
            component.logger.warning(f"Failed reading classification report: {e!r}")

        await _send(
            status="MODEL_ANALYZED",
            stage="model_analyzed",
            extra={
                "folder": capture_folder,
                "model_classification": model_label,
                "model_confidence": model_conf_pct,
            },
        )

    except Exception as e:
        component.logger.error(f"classify_features_dt failed: {e!r}")
        await _send(status="FAILED", stage="classification_failed", extra={"folder": capture_folder, "error": repr(e)})
        return

    # ==============================================================
    # 5) Bundle + register evidence artifact
    # ==============================================================

    try:
        artifact_id = component.artifact_manager.create_zip_artifact_from_folder(
            source_id=component.uuid,
            operation_id=operation_id,
            folder=capture_folder,
            name=f"SOI evidence @ {freq} MHz",
            metadata={
                "role": "soi_evidence_v1",
                "frequency_mhz": freq,
                "soi_id": soi_id,
                "operation_id": operation_id,
                "model_classification": model_label,
                "model_confidence": model_conf_pct,
            },
            arc_prefix=f"soi_{operation_id}",
        )

        component.logger.info(f"SOI evidence artifact registered: {artifact_id}")

        await _send(
            status="EVIDENCE_READY",
            stage="evidence_ready",
            extra={
                "folder": capture_folder,
                "artifact_id": artifact_id,
                "model_classification": model_label,
                "model_confidence": model_conf_pct,
            },
        )

    except Exception as e:
        component.logger.error(f"artifact bundling failed: {e!r}")
        await _send(status="FAILED", stage="evidence_bundle_failed", extra={"folder": capture_folder, "error": repr(e)})
        return

    # ==============================================================
    # 6) Done
    # ==============================================================

    component.logger.info(
        f"promote_to_soi complete: soi_id={soi_id}, op_id={operation_id}, "
        f"label={model_label}, conf={model_conf_pct}%"
    )


dummy_soi_schema = {
    "params": [
        {"name": "frequency_mhz", "label": "Frequency (MHz)", "type": "number", "default": 915.0},
        {"name": "model_label", "label": "Model Label", "type": "string", "default": "dummy_protocol"},
        {"name": "model_confidence", "label": "Model Confidence (%)", "type": "number", "default": 87},
        {"name": "description", "label": "Description", "type": "string", "default": "Dummy SOI"},
    ]
}
async def dummy_soi(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    component.logger.info(f"Dummy SOI action with parameters: {parameters}")
    await component.run_plugin_operation(component, "Mission-01", "dummy_soi.py", parameters, sensor_node_id)


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
async def dummy_target(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    Dummy Target Action
    
    :param component: Description
    :type component: SensorNode
    :param parameters: Description
    :type parameters: Dict[str, Any]
    :param sensor_node_id: Description
    :type sensor_node_id: Union[int, str]
    """
    component.logger.info(f"Dummy Target action with parameters: {parameters}")
    await component.run_plugin_operation(component, "Mission-01", "dummy_target.py", parameters, sensor_node_id)


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
async def dummy_status(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    Dummy Status Action

    Cycles through multiple node status messages, then completes.
    """
    component.logger.info(f"Dummy Status action with parameters: {parameters}")
    await component.run_plugin_operation(component, 'Mission-01', 'dummy_status.py', parameters, sensor_node_id)


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
async def take_photo(component: "SensorNode", parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    Take Photo Action

    Captures a burst of photos from the system webcam (if available),
    bundles them into a zip artifact, and (optionally) emits an alert
    with the resulting artifact_id.

    Parameters (optional)
    ---------------------
    count        : int   (default 5)
    interval_s   : float (default 0.3)
    camera_index : int   (default 0)
    name         : str   (default "Photo capture evidence")
    """
    component.logger.info(f"take_photo action with parameters: {parameters}")

    # Provide a stable op id if caller didn't supply one
    op_id = str(parameters.get("operation_id") or uuid.uuid4())

    op_params = dict(parameters or {})
    op_params["operation_id"] = op_id  # used for folder naming + artifact metadata

    await component.run_plugin_operation(
        component,
        "Mission-01",
        "take_photo.py",
        op_params,
        sensor_node_id,
        wait=True,   # make it deterministic for demo; remove if you want async fire-and-forget
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
        {
            "name": "max_watch_s",
            "label": "Max Watch (s)",
            "type": "number",
            "default": 300.0,
        },
        {
            "name": "consecutive_frames",
            "label": "Consecutive Frames",
            "type": "number",
            "default": 3,
        },
        {
            "name": "photo_count",
            "label": "Photo Count",
            "type": "number",
            "default": 5,
        },
        {
            "name": "photo_interval_s",
            "label": "Photo Interval (s)",
            "type": "number",
            "default": 0.7,
        },
        {
            "name": "artifact_name",
            "label": "Artifact Name",
            "type": "string",
            "default": "Motion capture evidence",
        },
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
        {
            "name": "description",
            "label": "Description",
            "type": "string",
            "default": "Motion Detector",
        },
    ]
}
async def motion_detector(component: "SensorNode", parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    Motion Detector Action

    Watches the webcam for motion. When motion is detected:
    - sends a dashboard alert
    - drops a TAK pin (lat/lon/alt/time auto-filled)
    - captures a burst of photos and registers a zip artifact
    - includes artifact_id in alert + TAK remarks

    Parameters (optional)
    ---------------------
    camera_index            : int   default 0
    max_watch_s             : float default 300.0   # stop watching after N seconds (0/None = infinite)
    diff_threshold          : int   default 50      # pixel diff threshold (0-255)
    min_contour_area        : int   default 500     # ignore tiny motion blobs
    motion_area_threshold   : int   default 5000    # sum area threshold to trigger
    consecutive_frames      : int   default 3       # require motion for N consecutive frames
    frame_interval_s        : float default 0.10    # watch loop pace
    warmup_frames           : int   default 5       # camera settle frames

    photo_count             : int   default 5
    photo_interval_s        : float default 0.7
    artifact_name           : str   default "Motion capture evidence"
    tak_icon                : str   default "a-h-G-E-S"
    """
    component.logger.info(f"motion_detector action with parameters: {parameters}")

    op_params = dict(parameters or {})
    op_params.setdefault("operation_id", str(uuid.uuid4()))

    await component.run_plugin_operation(
        component,
        "Mission-01",
        "motion_detector.py",
        op_params,
        sensor_node_id,
        wait=True,  # deterministic for testing; change to False if you want it to run in background
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
async def take_video(component: "SensorNode", parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    Take Video Action

    Records a short video clip from the system webcam and registers it as a zip artifact.
    Also emits a TAK pin and a dashboard alert containing the artifact_id.

    Parameters (optional)
    ---------------------
    duration_s    : float default 10.0
    fps           : float default 15.0
    camera_index  : int   default 0
    artifact_name : str   default "Video capture evidence"
    tak_icon      : str   default "a-h-G-E-S"
    codec         : str   default "MJPG"   # safest with OpenCV, outputs AVI
    warmup_frames : int   default 5
    """
    component.logger.info(f"take_video action with parameters: {parameters}")

    op_params = dict(parameters or {})
    op_params.setdefault("operation_id", str(uuid.uuid4()))

    await component.run_plugin_operation(
        component,
        "Mission-01",
        "take_video.py",
        op_params,
        sensor_node_id,
        wait=True,
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
async def dummy_cot_types(component, parameters,  sensor_node_id: Union[int, str] = 0) -> None:
    component.logger.info(f"Dummy CoT Types action with parameters: {parameters}")
    await component.run_plugin_operation(component, 'Mission-01', 'dummy_cot_types.py', parameters, sensor_node_id)


lfm_beacon_detection_schema = {
    "params": [
        {"name": "freq_mhz", "label": "Frequency (MHz)", "type": "number", "default": 433.0},
        {"name": "min_detection_interval_s", "label": "Min. interval (s)", "type": "number", "default": 1.0},
        {"name": "description", "label": "Description", "type": "string", "default": "LFM beacon detection"},
    ]
}
async def lfm_beacon_detection(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    LFM Beacon Detection Action
    """
    component.logger.info(f"LFM Beacon Detection action with parameters: {parameters}")
    await component.run_plugin_operation(
        component,
        'Mission-01',
        'lfm_beacon_detection.py',
        parameters,
        sensor_node_id,
        wait=True
    )


async def lfm_beacon_geolocate(component: SensorNode, parameters: Dict[str, Any], sensor_node_id: Union[int, str] = 0) -> None:
    """
    LFM Beacon Geolocation of a Single Target using Hub Multilateration.

    Parameters
    ----------
    component : SensorNode
        The sensor node instance.
    parameters : Dict[str, Any]
        The parameters for the LFM beacon geolocation operation.
        Expected to be supplied by the hub from the selected target.
    sensor_node_id : Union[int, str], optional
        The ID of the sensor node, by default 0
    """
    component.logger.info(f"LFM beacon geolocation with parameters: {parameters}")

    op_params = dict(parameters or {})

    component.logger.info(f"Resolved LFM beacon geolocation operation parameters: {op_params}")

    await component.run_plugin_operation(
        component,
        'Mission-01',
        'lfm_beacon_geolocate.py',
        {"parameters": op_params},
        sensor_node_id,
    )