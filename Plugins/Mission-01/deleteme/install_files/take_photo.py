#! /usr/bin/env python3
"""Take Photo Operation

Captures N images from a webcam and registers them as a single zip artifact.

- Writes files to:  FISSURE_ROOT/artifacts/<operation_id>/files/
- Registers zip via: artifact_manager.create_zip_artifact_from_folder(...)
- Stop-aware: if stop requested mid-capture, exits cleanly without creating artifact.

Modernized:
- UI schema params passed into __init__ (OperationMain(**params))
- Early normalization + clamping
- Python 3.8-safe typing (no tuple[...] etc.)
- Minimal UI; warmup/source_id/operation_id kept optional/back-compat
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Callable, Union

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

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
    """Take Photo Operation"""

    def __init__(
        self,
        # --- parameters (from UI schema) ---
        count: int = 5,
        interval_s: float = 0.3,
        name: str = "Photo capture evidence",
        emit_tak_pin: Union[str, bool] = "yes",
        emit_alert: Union[str, bool] = "yes",
        description: str = "Take Photo",
        # --- optional/back-compat params (not shown in schema UI) ---
        operation_id: str = "",
        source_id: str = "",
        warmup_frames: int = 2,
        # --- framework plumbing ---
        sensor_node_id: Union[int, str] = 0,
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback: Union[Callable, None] = None,
        tak_cot_callback: Union[Callable, None] = None,
        status_callback: Union[Callable, None] = None,
        artifact_manager=None,
    ) -> None:
        super().__init__(
            sensor_node_id=sensor_node_id,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
            status_callback=status_callback,
            artifact_manager=artifact_manager,
        )

        # --- normalize schema params ---
        self.count = int(_clamp(float(_to_int(count, 5)), 1.0, 50.0))
        self.interval_s = _clamp(_to_float(interval_s, 0.3), 0.05, 10.0)

        self.camera_index = 0

        self.name = _to_str(name, "Photo capture evidence")
        self.emit_tak_pin = _to_bool_yn(emit_tak_pin, True)
        self.emit_alert = _to_bool_yn(emit_alert, True)
        self.description = _to_str(description, "Take Photo")

        # --- optional/back-compat ---
        opid_in = _to_str(operation_id, "")
        self.operation_id = opid_in if opid_in else str(self.opid or uuid.uuid4())
        self.source_id = _to_str(source_id, "")
        self.warmup_frames = int(_clamp(float(_to_int(warmup_frames, 2)), 0.0, 30.0))

        self.logger.info(
            "take_photo init params: "
            f"operation_id={self.operation_id}, count={self.count}, interval_s={self.interval_s}, "
            f"camera_index={self.camera_index}, name={self.name}, "
            f"emit_tak_pin={self.emit_tak_pin}, emit_alert={self.emit_alert}"
        )

        self.resource_args = {"camera_index": self.camera_index}

    async def run(self) -> None:
        if cv2 is None:
            if self.status_callback:
                await self.status_callback("OpenCV not available")
            self.logger.error("cv2 import failed; cannot capture photos.")
            return

        if not self.artifact_manager:
            raise RuntimeError("take_photo requires artifact_manager to be passed in")

        folder = os.path.join(FISSURE_ROOT, "artifacts", self.operation_id, "files")
        os.makedirs(folder, exist_ok=True)

        meta = {
            "role": "photo_capture_v1",
            "sensor_node_id": self.sensor_node_id,
            "operation_id": self.operation_id,
            "created_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "camera_index": self.camera_index,
            "count": self.count,
            "interval_s": self.interval_s,
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

        # Warm-up frames (helps some webcams auto-exposure)
        for _ in range(max(0, self.warmup_frames)):
            if self._stop:
                break
            _ = cap.read()
            await asyncio.sleep(0)

        # Capture loop
        for i in range(self.count):
            if self._stop:
                break

            if self.status_callback:
                await self.status_callback(f"Taking photo ({i+1}/{self.count})")

            ret, frame = cap.read()
            if not ret:
                self.logger.error("Failed to read frame from camera")
                break

            fname = os.path.join(folder, f"photo_{i+1:02d}.jpg")
            ok = cv2.imwrite(fname, frame)
            if not ok:
                self.logger.error(f"Failed to write image: {fname}")
                break

            await asyncio.sleep(self.interval_s)

        cap.release()

        if self._stop:
            if self.status_callback:
                await self.status_callback("Stopped")
            return

        photos = [f for f in os.listdir(folder) if f.lower().endswith(".jpg")]
        if not photos:
            if self.status_callback:
                await self.status_callback("No photos captured")
            return

        meta_path = os.path.join(folder, "metadata.json")
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed writing metadata.json: {e!r}")

        if self.status_callback:
            await self.status_callback("Bundling photos")

        artifact_id = self.artifact_manager.create_zip_artifact_from_folder(
            source_id=self.source_id,
            operation_id=self.operation_id,
            folder=folder,
            name=self.name,
            metadata=meta,
            arc_prefix=f"photo_{self.operation_id}",
        )

        self.logger.info(
            f"Photo bundle registered: artifact_id={artifact_id}, opid={self.operation_id}"
        )

        # TAK pin
        if self.emit_tak_pin and self.tak_cot_callback:
            try:
                short_id = str(artifact_id)[:8]
                tak_msg = {
                    "msg_type": "pin",
                    "uid": f"photo_{artifact_id}",
                    "remarks": f"Photo capture [{short_id}] (count={len(photos)})",
                    "lat": True,
                    "lon": True,
                    "alt": True,
                    "time": True,
                    "tak_icon": "a-h-G-E-S",
                    "opid": self.opid,
                    "alert_kind": "photo_capture",
                    "alert_summary": f"Photo capture (count={len(photos)})",
                    "artifact_id": artifact_id,
                    "operation_id": self.operation_id,
                    "sensor_node_id": self.sensor_node_id,
                    "name": self.name,
                }
                await self.tak_cot_callback(tak_msg)
                self.logger.info(f"TAK pin emitted for photo artifact_id={artifact_id}")
            except Exception:
                self.logger.exception("Failed emitting TAK pin for photo capture")

        # Optional alert
        if self.emit_alert and self.alert_callback:
            try:
                payload = {
                    "type": "artifact_ready",
                    "artifact_id": artifact_id,
                    "operation_id": self.operation_id,
                    "name": self.name,
                    "role": "photo_capture_v1",
                    "count": len(photos),
                }
                await asyncio.wait_for(
                    self.alert_callback(
                        self.sensor_node_id,
                        self.opid,
                        json.dumps(payload),
                        self.logger,
                    ),
                    timeout=2.0,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger.exception("alert_callback failed while reporting artifact_ready")

        if self.status_callback:
            await self.status_callback("Idle")


if __name__ == "__main__":
    from fissure.utils.plugins.test_operation import run_test
    run_test(OperationMain, {}, {})