#! /usr/bin/env python3
"""Motion Detector Operation

Modernized to match WinTAK action-schema patterns:

- Uses UI schema params (sensitivity/max_watch_s/consecutive_frames/photo_count/photo_interval_s/...)
- Removes camera_index from UI (hardcoded to 0)
- Uses sensitivity presets instead of raw threshold knobs
- Normalizes/clamps parameters early in __init__
- Stop-aware; deterministic
- On trigger:
  - captures N photos
  - bundles into zip artifact
  - optionally emits TAK pin and/or dashboard alert (both toggleable)
- Python 3.8-safe typing
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Callable, Dict, Union

try:
    import cv2
    import numpy as np
except Exception:  # pragma: no cover
    cv2 = None
    np = None

try:
    from fissure.utils.plugins.operations import Operation
    from fissure.utils import FISSURE_ROOT
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from fissure.utils.plugins.operations import Operation
    from fissure.utils import FISSURE_ROOT


def _to_float(v: Any, default: float) -> float:
    try:
        if v is None:
            return float(default)
        return float(v)
    except Exception:
        return float(default)


def _to_int(v: Any, default: int) -> int:
    try:
        if v is None:
            return int(default)
        return int(float(v))
    except Exception:
        return int(default)


def _to_str(v: Any, default: str) -> str:
    if v is None:
        return default
    s = str(v).strip()
    return s if s else default


def _clamp(x: float, lo: float, hi: float) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def _to_bool_yn(v: Any, default: bool = True) -> bool:
    if v is None:
        return default
    s = str(v).strip().lower()
    if s in ("1", "true", "t", "yes", "y", "on"):
        return True
    if s in ("0", "false", "f", "no", "n", "off"):
        return False
    return default


class OperationMain(Operation):
    """Motion Detector Operation"""

    def __init__(
        self,
        # --- parameters (from UI schema) ---
        sensitivity: str = "medium",
        max_watch_s: float = 300.0,
        consecutive_frames: int = 3,
        photo_count: int = 5,
        photo_interval_s: float = 0.7,
        artifact_name: str = "Motion capture evidence",
        emit_tak_pin: Union[str, bool] = "yes",
        emit_alert: Union[str, bool] = "yes",
        description: str = "Motion Detector",
        # --- optional/back-compat (not in minimal schema) ---
        operation_id: str = "",
        source_id: str = "",
        tak_icon: str = "a-h-G-E-S",
        warmup_frames: int = 5,
        # --- framework plumbing ---
        node_uid: str = "",
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback: Union[Callable, None] = None,
        tak_cot_callback: Union[Callable, None] = None,
        status_callback: Union[Callable, None] = None,
        artifact_manager=None,
    ) -> None:
        super().__init__(
            node_uid=node_uid,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
            status_callback=status_callback,
            artifact_manager=artifact_manager,
        )

        # ---- normalize schema params ----
        self.sensitivity = _to_str(sensitivity, "medium").lower()
        if self.sensitivity not in ("low", "medium", "high"):
            self.sensitivity = "medium"

        mw = _to_float(max_watch_s, 300.0)
        # 0/None => infinite watch
        self.max_watch_s = 0.0 if mw <= 0.0 else _clamp(mw, 1.0, 24.0 * 3600.0)

        self.consecutive_frames = int(_clamp(float(_to_int(consecutive_frames, 3)), 1.0, 50.0))

        self.photo_count = int(_clamp(float(_to_int(photo_count, 5)), 1.0, 50.0))
        self.photo_interval_s = _clamp(_to_float(photo_interval_s, 0.7), 0.05, 10.0)

        self.artifact_name = _to_str(artifact_name, "Motion capture evidence")
        self.emit_tak_pin = _to_bool_yn(emit_tak_pin, True)
        self.emit_alert = _to_bool_yn(emit_alert, True)
        self.description = _to_str(description, "Motion Detector")

        opid_in = _to_str(operation_id, "")
        self.operation_id = opid_in if opid_in else str(self.opid or uuid.uuid4())

        self.source_id = _to_str(source_id, "")
        self.tak_icon = _to_str(tak_icon, "a-h-G-E-S")
        self.warmup_frames = int(_clamp(float(_to_int(warmup_frames, 5)), 0.0, 60.0))

        # ---- minimal UI philosophy: hardcode camera selection ----
        self.camera_index = 0

        # ---- internal loop pace (not exposed) ----
        self.frame_interval_s = 0.10

        # ---- sensitivity presets (replaces raw threshold knobs) ----
        # Tune as needed; these are reasonable starting points.
        if self.sensitivity == "low":
            self.diff_threshold = 60
            self.min_contour_area = 900
            self.motion_area_threshold = 9000
        elif self.sensitivity == "high":
            self.diff_threshold = 35
            self.min_contour_area = 350
            self.motion_area_threshold = 3500
        else:
            self.diff_threshold = 50
            self.min_contour_area = 500
            self.motion_area_threshold = 5000

        self.logger.info(
            "motion_detector init params: "
            f"sensitivity={self.sensitivity}, max_watch_s={self.max_watch_s}, "
            f"consecutive_frames={self.consecutive_frames}, "
            f"photo_count={self.photo_count}, photo_interval_s={self.photo_interval_s}, "
            f"emit_tak_pin={self.emit_tak_pin}, emit_alert={self.emit_alert}, "
            f"operation_id={self.operation_id}"
        )

        self.resource_args = {"camera_index": self.camera_index}

    async def run(self) -> None:
        if cv2 is None or np is None:
            if self.status_callback:
                await self.status_callback("OpenCV not available")
            self.logger.error("cv2/numpy import failed; cannot run motion detector.")
            return

        if not self.artifact_manager:
            raise RuntimeError("motion_detector requires artifact_manager")

        folder = os.path.join(FISSURE_ROOT, "artifacts", self.operation_id, "files")
        os.makedirs(folder, exist_ok=True)

        meta: Dict[str, Any] = {
            "role": "motion_capture_v1",
            "node_uid": self.node_uid,
            "operation_id": self.operation_id,
            "created_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "camera_index": self.camera_index,
            "watch": {
                "sensitivity": self.sensitivity,
                "diff_threshold": self.diff_threshold,
                "min_contour_area": self.min_contour_area,
                "motion_area_threshold": self.motion_area_threshold,
                "consecutive_frames": self.consecutive_frames,
                "frame_interval_s": self.frame_interval_s,
                "max_watch_s": (None if self.max_watch_s <= 0.0 else self.max_watch_s),
            },
            "capture": {
                "photo_count": self.photo_count,
                "photo_interval_s": self.photo_interval_s,
            },
        }

        if self.status_callback:
            await self.status_callback("Initializing camera")

        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            if self.status_callback:
                await self.status_callback("No camera found")
            self.logger.warning(f"Camera not available (index={self.camera_index})")
            try:
                cap.release()
            except Exception:
                pass
            return

        # Warm-up for auto-exposure/whitebalance settling
        for _ in range(max(0, self.warmup_frames)):
            if self._stop:
                break
            cap.read()
            await asyncio.sleep(0)

        if self._stop:
            cap.release()
            if self.status_callback:
                await self.status_callback("Stopped")
            return

        if self.status_callback:
            await self.status_callback("Watching for motion")

        start = time.time()
        prev_gray = None
        motion_streak = 0
        triggered = False
        trigger_stats: Dict[str, Any] = {}

        # Kernel for morphology (keep consistent with your original)
        kernel = np.ones((5, 5), np.uint8)

        # ---- watch loop ----
        while not self._stop:
            if self.max_watch_s > 0.0 and (time.time() - start) > self.max_watch_s:
                break

            ret, frame = cap.read()
            if not ret or frame is None:
                self.logger.warning("Failed to read frame; continuing")
                await asyncio.sleep(self.frame_interval_s)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if prev_gray is None:
                prev_gray = gray
                await asyncio.sleep(self.frame_interval_s)
                continue

            diff = cv2.absdiff(gray, prev_gray)
            _, diff_thresh = cv2.threshold(diff, self.diff_threshold, 255, cv2.THRESH_BINARY)

            diff_thresh = cv2.dilate(diff_thresh, kernel, iterations=2)
            diff_thresh = cv2.erode(diff_thresh, kernel, iterations=2)

            contours, _ = cv2.findContours(diff_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            motion_area = 0
            big_contours = 0
            for c in contours:
                a = float(cv2.contourArea(c))
                if a >= float(self.min_contour_area):
                    motion_area += int(a)
                    big_contours += 1

            if motion_area >= int(self.motion_area_threshold):
                motion_streak += 1
            else:
                motion_streak = 0

            if motion_streak >= self.consecutive_frames:
                triggered = True
                trigger_stats = {
                    "motion_area": motion_area,
                    "big_contours": big_contours,
                    "motion_streak": motion_streak,
                    "trigger_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                break

            prev_gray = gray
            await asyncio.sleep(self.frame_interval_s)

        if not triggered:
            cap.release()
            if self.status_callback:
                await self.status_callback("No motion (timeout)" if not self._stop else "Stopped")
            return

        # ---- triggered: capture photos ----
        if self.status_callback:
            await self.status_callback("Motion detected! Capturing photos")

        captured = 0
        for i in range(self.photo_count):
            if self._stop:
                break

            ret, frame = cap.read()
            if not ret or frame is None:
                self.logger.error("Failed to read frame during capture")
                break

            fname = os.path.join(folder, f"photo_{i+1:02d}.jpg")
            ok = cv2.imwrite(fname, frame)
            if not ok:
                self.logger.error(f"Failed to write image: {fname}")
                break

            captured += 1
            await asyncio.sleep(self.photo_interval_s)

        cap.release()

        if self._stop:
            if self.status_callback:
                await self.status_callback("Stopped")
            return

        if captured <= 0:
            if self.status_callback:
                await self.status_callback("Motion detected (no photos captured)")
            return

        # Write metadata sidecar into folder for bundling
        meta["trigger"] = trigger_stats
        meta["capture"]["captured"] = captured

        meta_path = os.path.join(folder, "metadata.json")
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed writing metadata.json: {e!r}")

        if self.status_callback:
            await self.status_callback("Bundling evidence")

        artifact_id = self.artifact_manager.create_zip_artifact_from_folder(
            source_id=self.source_id,
            operation_id=self.operation_id,
            folder=folder,
            name=self.artifact_name,
            metadata=meta,
            arc_prefix=f"motion_{self.operation_id}",
        )

        self.logger.info(f"Motion evidence registered: artifact_id={artifact_id}, opid={self.operation_id}")

        # Dashboard alert (toggleable)
        if self.emit_alert and self.alert_callback:
            try:
                payload = {
                    "type": "motion_alert",
                    "artifact_id": artifact_id,
                    "operation_id": self.operation_id,
                    "count": captured,
                    "motion": trigger_stats,
                    "sensitivity": self.sensitivity,
                }
                await asyncio.wait_for(
                    self.alert_callback(
                        self.node_uid,
                        self.opid,
                        json.dumps(payload),
                        self.logger,
                    ),
                    timeout=2.0,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger.exception("alert_callback failed for motion_alert")

        # TAK pin (toggleable)
        if self.emit_tak_pin and self.tak_cot_callback:
            try:
                short_id = str(artifact_id)[:8]
                tak_msg = {
                    "msg_type": "pin",
                    "uid": f"motion_{artifact_id}",
                    "remarks": f"Motion detected [{short_id}] (photos={captured})",
                    "lat": True,
                    "lon": True,
                    "alt": True,
                    "time": True,
                    "tak_icon": self.tak_icon,
                    "opid": self.opid,
                    "alert_kind": "motion_alert",
                    "alert_summary": f"Motion detected (photos={captured})",
                    "artifact_id": artifact_id,
                    "operation_id": self.operation_id,
                    "node_uid": self.node_uid,
                    "name": self.artifact_name,
                    "motion_area": trigger_stats.get("motion_area"),
                    "big_contours": trigger_stats.get("big_contours"),
                }
                await self.tak_cot_callback(tak_msg)
            except Exception:
                self.logger.exception("tak_cot_callback failed for motion pin")

        if self.status_callback:
            await self.status_callback("Idle")


if __name__ == "__main__":
    from fissure.utils.plugins.test_operation import run_test
    run_test(OperationMain, {}, {})