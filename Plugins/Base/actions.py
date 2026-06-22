#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base Plugin Actions"""

import json
import os
import time
import uuid
from typing import Any, Dict, Union

from fissure.Sensor_Node.SensorNode import SensorNode
from fissure.utils import FISSURE_ROOT


PLUGIN_NAME = "Base"


ACTION_TAGS = {
    "signal_geolocate": ["All"],

    "fixed_detection": ["All"],
    "scan_detection": ["All"],
    "hackrf_sweep_detection": ["All"],
    "rtl_power_detection": ["All"],
    "lfm_beacon_detection": ["All"],

    "iq_record": ["All"],

    "promote_to_soi": ["All"],

    "take_photo": ["All"],
    "motion_detector": ["All"],
    "take_video": ["All"],
}


ACTION_HARDWARE = {
    "hackrf_sweep_detection": ["HackRF"],
    "rtl_power_detection": ["RTL2832U"],
    "signal_geolocate": ["USRP B20xmini", "USRP B2x0"],
    "fixed_detection": ["USRP B20xmini", "USRP B2x0"],
    "scan_detection": ["USRP B20xmini", "USRP B2x0"],
    "lfm_beacon_detection": ["RTL2832U"],
    "iq_record": ["USRP B20xmini", "USRP B2x0"],
}


async def signal_geolocate(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    component.logger.info(
        f"Signal geolocation with parameters: {parameters}"
    )

    op_params = dict(parameters or {})

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "signal_geolocate.py",
        {"parameters": op_params},
        node_uid,
    )


fixed_detection_schema = {
    "params": [
        {
            "name": "freq_mhz",
            "label": "Frequency (MHz)",
            "type": "number",
            "default": 915.0,
        },
        {
            "name": "min_detection_interval_s",
            "label": "Min. interval (s)",
            "type": "number",
            "default": 10.0,
        },
        {
            "name": "description",
            "label": "Description",
            "type": "string",
            "default": "Fixed detection",
        },
    ]
}

async def fixed_detection(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    component.logger.info(
        f"Fixed Detection action with parameters: {parameters}"
    )

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "fixed_detection.py",
        parameters,
        node_uid,
        wait=True,
    )


scan_detection_schema = {
    "params": [
        {
            "name": "dwell_s",
            "label": "Dwell (s)",
            "type": "number",
            "default": 10.0,
        },
        {
            "name": "alert_interval_s",
            "label": "Min Alert Interval (s)",
            "type": "number",
            "default": 10.0,
        },
        {
            "name": "description",
            "label": "Description",
            "type": "string",
            "default": "Scan detection across preset bands",
        },
    ]
}

async def scan_detection(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    component.logger.info(
        f"Scan Detection action with parameters: {parameters}"
    )

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
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
        {
            "name": "alert_interval_s",
            "label": "Alert Interval (s)",
            "type": "number",
            "default": 5.0,
        },
        {
            "name": "detection_threshold_db",
            "label": "Detection Threshold (dB)",
            "type": "number",
            "default": 12.0,
        },
        {
            "name": "description",
            "label": "Description",
            "type": "string",
            "default": "HackRF sweep detection",
        },
    ]
}

async def hackrf_sweep_detection(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    component.logger.info(
        f"HackRF sweep detection action with parameters: {parameters}"
    )

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
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
        {
            "name": "alert_interval_s",
            "label": "Alert Interval (s)",
            "type": "number",
            "default": 5.0,
        },
        {
            "name": "detection_threshold_db",
            "label": "Detection Threshold (dB)",
            "type": "number",
            "default": 8.0,
        },
        {
            "name": "description",
            "label": "Description",
            "type": "string",
            "default": "RTL-SDR rtl_power detection",
        },
    ]
}

async def rtl_power_detection(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    component.logger.info(
        f"rtl_power detection action with parameters: {parameters}"
    )

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "rtl_power_detection.py",
        parameters,
        node_uid,
    )


lfm_beacon_detection_schema = {
    "params": [
        {
            "name": "freq_mhz",
            "label": "Frequency (MHz)",
            "type": "number",
            "default": 433.0,
        },
        {
            "name": "min_detection_interval_s",
            "label": "Min. interval (s)",
            "type": "number",
            "default": 1.0,
        },
        {
            "name": "description",
            "label": "Description",
            "type": "string",
            "default": "LFM beacon detection",
        },
    ]
}

async def lfm_beacon_detection(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    component.logger.info(
        f"LFM Beacon Detection action with parameters: {parameters}"
    )

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "lfm_beacon_detection.py",
        parameters,
        node_uid,
        wait=True,
    )


async def lfm_beacon_geolocate(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    component.logger.info(
        f"LFM beacon geolocation with parameters: {parameters}"
    )

    op_params = dict(parameters or {})

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "lfm_beacon_geolocate.py",
        {"parameters": op_params},
        node_uid,
    )


promote_to_soi_schema = {
    "params": [
        {
            "name": "frequency_mhz",
            "label": "Frequency (MHz)",
            "type": "number",
            "default": 915.0,
        },
        {
            "name": "description",
            "label": "Description",
            "type": "string",
            "default": "Promote to SOI",
        },
    ]
}

async def promote_to_soi(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:

    component.logger.info(
        f"Promote to SOI action with parameters: {parameters}"
    )

    freq = parameters.get("frequency_mhz")

    if freq is None:
        raise ValueError("Missing required parameter: frequency_mhz")

    try:
        freq = float(freq)
    except Exception:
        raise ValueError(f"Invalid frequency_mhz: {freq!r}")

    data_type = parameters.get(
        "data_type",
        "Complex Float 32",
    )

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

    async def _send(
        status: str,
        stage: str,
        extra: Dict[str, Any] = None,
    ) -> None:

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
                node_uid=node_uid,
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
            component.logger.exception(
                f"SOI update failed (status={status})"
            )

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
        return bool(folder) and os.path.isfile(
            os.path.join(folder, filename)
        )

    async def _abort(stage: str, msg: str) -> None:
        component.logger.warning(msg)

        await _send(
            status="FAILED",
            stage=stage,
            extra={"error": msg},
        )

    await _send(
        status="STARTED",
        stage="starting",
        extra={"files_present": False},
    )

    try:
        op1_params = {
            "frequency_mhz": freq
        }

        op1_id = await component.run_plugin_operation(
            component,
            PLUGIN_NAME,
            "signal_conditioning.py",
            op1_params,
            node_uid,
            wait=True,
        )

        operation_id = op1_id

        capture_folder = os.path.join(
            FISSURE_ROOT,
            "artifacts",
            op1_id,
            "files",
        )

        if not _has_capture_files(capture_folder):
            await _abort(
                stage="capture_failed",
                msg=f"Capture produced no files. folder={capture_folder}",
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
        component.logger.error(
            f"signal_conditioning failed: {e!r}"
        )

        await _send(
            status="FAILED",
            stage="capture_failed",
            extra={"error": repr(e)},
        )

        return

    try:
        op2_params = {
            "folder": capture_folder,
            "data_type": data_type,
        }

        await component.run_plugin_operation(
            component,
            PLUGIN_NAME,
            "feature_extraction.py",
            op2_params,
            node_uid,
            wait=True,
        )

        if not _exists(capture_folder, "tsi_features.json"):
            await _abort(
                stage="features_failed",
                msg=f"Feature extraction missing tsi_features.json",
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
        component.logger.error(
            f"feature_extraction failed: {e!r}"
        )

        await _send(
            status="FAILED",
            stage="features_failed",
            extra={
                "folder": capture_folder,
                "error": repr(e),
            },
        )

        return

    try:
        op3_params = {
            "folder": capture_folder,
            "features_file": "tsi_features.json",
            "min_models": 2,
            "use_batch_consensus": True,
        }

        await component.run_plugin_operation(
            component,
            PLUGIN_NAME,
            "classify_features_dt.py",
            op3_params,
            node_uid,
            wait=True,
        )

        report_path = os.path.join(
            capture_folder,
            "classification_report.json",
        )

        if not os.path.isfile(report_path):
            await _abort(
                stage="classification_failed",
                msg="Classifier missing classification_report.json",
            )
            return

        try:
            with open(report_path, "r", encoding="utf-8") as f:
                rep = json.load(f)

            model_label = rep.get("batch", {}).get("label")

            conf01 = rep.get("batch", {}).get("confidence")

            model_conf_pct = (
                round(conf01 * 100)
                if conf01 is not None
                else None
            )

        except Exception as e:
            component.logger.warning(
                f"Failed reading classification report: {e!r}"
            )

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
        component.logger.error(
            f"classify_features_dt failed: {e!r}"
        )

        await _send(
            status="FAILED",
            stage="classification_failed",
            extra={
                "folder": capture_folder,
                "error": repr(e),
            },
        )

        return

    try:
        artifact_id = (
            component.artifact_manager.create_zip_artifact_from_folder(
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
        )

        component.logger.info(
            f"SOI evidence artifact registered: {artifact_id}"
        )

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
        component.logger.error(
            f"artifact bundling failed: {e!r}"
        )

        await _send(
            status="FAILED",
            stage="evidence_bundle_failed",
            extra={
                "folder": capture_folder,
                "error": repr(e),
            },
        )

        return

    component.logger.info(
        f"promote_to_soi complete: "
        f"soi_id={soi_id}, "
        f"op_id={operation_id}, "
        f"label={model_label}, "
        f"conf={model_conf_pct}%"
    )


take_photo_schema = {
    "params": [
        {
            "name": "count",
            "label": "Photo Count",
            "type": "number",
            "default": 5,
        },
        {
            "name": "interval_s",
            "label": "Interval (s)",
            "type": "number",
            "default": 0.3,
        },
        {
            "name": "name",
            "label": "Artifact Name",
            "type": "string",
            "default": "Photo capture evidence",
        },
    ]
}

async def take_photo(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:

    component.logger.info(
        f"take_photo action with parameters: {parameters}"
    )

    op_id = str(
        parameters.get("operation_id") or uuid.uuid4()
    )

    op_params = dict(parameters or {})
    op_params["operation_id"] = op_id

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
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
        {
            "name": "max_watch_s",
            "label": "Max Watch (s)",
            "type": "number",
            "default": 300.0,
        },
        {
            "name": "photo_count",
            "label": "Photo Count",
            "type": "number",
            "default": 5,
        },
    ]
}

async def motion_detector(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:

    component.logger.info(
        f"motion_detector action with parameters: {parameters}"
    )

    op_params = dict(parameters or {})

    op_params.setdefault(
        "operation_id",
        str(uuid.uuid4()),
    )

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "motion_detector.py",
        op_params,
        node_uid,
        wait=True,
    )


take_video_schema = {
    "params": [
        {
            "name": "duration_s",
            "label": "Duration (s)",
            "type": "number",
            "default": 10.0,
        },
        {
            "name": "fps",
            "label": "FPS",
            "type": "number",
            "default": 30.0,
        },
        {
            "name": "artifact_name",
            "label": "Artifact Name",
            "type": "string",
            "default": "Video capture evidence",
        },
    ]
}

async def take_video(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:

    component.logger.info(
        f"take_video action with parameters: {parameters}"
    )

    op_params = dict(parameters or {})

    op_params.setdefault(
        "operation_id",
        str(uuid.uuid4()),
    )

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "take_video.py",
        op_params,
        node_uid,
        wait=True,
    )


iq_record_schema = {
    "params": [
        {
            "name": "flow_graph_name",
            "label": "Flow Graph",
            "type": "string",
            "default": "iq_recorder_b2x0",
            "options": [
                "iq_recorder_b2x0",
            ],
        },
        {
            "name": "base_file_name",
            "label": "Base File Name",
            "type": "string",
            "default": "capture.sigmf-data",
        },
        {
            "name": "artifact_format",
            "label": "Artifact Format",
            "type": "string",
            "default": "raw",
            "options": [
                "raw",
                "zip",
            ],
        },
        {
            "name": "frequency_mhz",
            "label": "Frequency (MHz)",
            "type": "number",
            "default": 915.0,
        },
        {
            "name": "sample_rate_mhz",
            "label": "Sample Rate (MHz)",
            "type": "number",
            "default": 1.0,
        },
        {
            "name": "rx_gain",
            "label": "RX Gain",
            "type": "number",
            "default": 20.0,
        },
        {
            "name": "rx_channel",
            "label": "RX Channel",
            "type": "string",
            "default": "A:A",
        },
        {
            "name": "rx_antenna",
            "label": "RX Antenna",
            "type": "string",
            "default": "TX/RX",
        },
        {
            "name": "file_length",
            "label": "File Length",
            "type": "number",
            "default": 100000,
        },
        {
            "name": "number_of_files",
            "label": "Number of Files",
            "type": "number",
            "default": 1,
        },
        {
            "name": "file_interval",
            "label": "File Interval (s)",
            "type": "number",
            "default": 0.0,
        },
        {
            "name": "data_type",
            "label": "Data Type",
            "type": "string",
            "default": "Complex Float 32",
            "options": [
                "Complex Float 32",
            ],
        },
        {
            "name": "sigmf_enabled",
            "label": "SigMF Enabled",
            "type": "string",
            "default": "true",
            "options": [
                "true",
                "false",
            ],
        },
        {
            "name": "description",
            "label": "Description",
            "type": "string",
            "default": "IQ recording",
        },
    ]
}
async def iq_record(
    component: SensorNode,
    parameters: Dict[str, Any],
    node_uid: str = "",
) -> None:
    component.logger.info(
        f"IQ Record action with parameters: {parameters}"
    )

    await component.run_plugin_operation(
        component,
        PLUGIN_NAME,
        "iq_record.py",
        parameters,
        node_uid,
    )