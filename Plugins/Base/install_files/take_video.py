#! /usr/bin/env python3
"""Take Video Operation

Modernized to match WinTAK action-schema patterns:

- UI schema params passed into __init__ (OperationMain(**params))
- Minimal UI knobs: duration/fps/name + toggles; camera_index removed (hardcoded 0)
- Normalizes/clamps early in __init__
- Stop-aware; no partial artifact on stop
- Registers zip artifact (video.avi + metadata.json)
- Optionally emits TAK pin and/or dashboard alert

Python 3.8-safe typing.
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
    """Take Video Operation"""

    def __init__(
        self,
        # --- parameters (from UI schema) ---
        duration_s: float = 10.0,
        fps: float = 15.0,
        artifact_name: str = "Video capture evidence",
        emit_tak_pin: Union[str, bool] = "yes",
        emit_alert: Union[str, bool] = "yes",
        description: str = "Take Video",
        # --- optional/back-compat (not in minimal schema) ---
        operation_id: str = "",
        source_id: str = "",
        tak_icon: str = "a-h-G-E-S",
        codec: str = "MJPG",
        warmup_frames: int = 5,
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
        self.duration_s = _clamp(_to_float(duration_s, 10.0), 1.0, 60.0)
        self.fps = _clamp(_to_float(fps, 15.0), 1.0, 60.0)
        self.artifact_name = _to_str(artifact_name, "Video capture evidence")
        self.emit_tak_pin = _to_bool_yn(emit_tak_pin, True)
        self.emit_alert = _to_bool_yn(emit_alert, True)
        self.description = _to_str(description, "Take Video")

        # --- optional/back-compat ---
        opid_in = _to_str(operation_id, "")
        self.operation_id = opid_in if opid_in else str(self.opid or uuid.uuid4())
        self.source_id = _to_str(source_id, "")
        self.tak_icon = _to_str(tak_icon, "a-h-G-E-S")
        self.codec = _to_str(codec, "MJPG").upper()
        self.warmup_frames = int(_clamp(float(_to_int(warmup_frames, 5)), 0.0, 60.0))

        # Minimal UI philosophy: hardcode camera selection
        self.camera_index = 0

        self.logger.info(
            "take_video init params: "
            f"operation_id={self.operation_id}, duration_s={self.duration_s}, fps={self.fps}, "
            f"artifact_name={self.artifact_name}, emit_tak_pin={self.emit_tak_pin}, emit_alert={self.emit_alert}, "
            f"codec={self.codec}"
        )

        self.resource_args = {"camera_index": self.camera_index}

    async def run(self) -> None:
        if cv2 is None:
            if self.status_callback:
                await self.status_callback("OpenCV not available")
            self.logger.error("cv2 import failed; cannot record video.")
            return

        if not self.artifact_manager:
            raise RuntimeError("take_video requires artifact_manager")

        folder = os.path.join(FISSURE_ROOT, "artifacts", self.operation_id, "files")
        os.makedirs(folder, exist_ok=True)

        meta = {
            "role": "video_capture_v1",
            "sensor_node_id": self.sensor_node_id,
            "operation_id": self.operation_id,
            "created_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "camera_index": self.camera_index,
            "duration_s": self.duration_s,
            "fps": self.fps,
            "codec": self.codec,
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

        # Warm-up
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

        # Determine size
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

        frame0 = None
        if width <= 0 or height <= 0:
            ret, frame0 = cap.read()
            if not ret or frame0 is None:
                cap.release()
                if self.status_callback:
                    await self.status_callback("Camera read failed")
                return
            height, width = frame0.shape[:2]

        # Writer
        fourcc = cv2.VideoWriter_fourcc(*self.codec)
        video_path = os.path.join(folder, "video.avi")
        writer = cv2.VideoWriter(video_path, fourcc, self.fps, (width, height))

        if not writer.isOpened():
            cap.release()
            if self.status_callback:
                await self.status_callback("VideoWriter init failed")
            self.logger.error(
                f"VideoWriter failed (codec={self.codec}, size={(width, height)}, fps={self.fps})"
            )
            return

        if self.status_callback:
            await self.status_callback(f"Recording video ({self.duration_s:.0f}s)")

        start = time.time()
        frames_written = 0

        try:
            if frame0 is not None and not self._stop:
                writer.write(frame0)
                frames_written += 1

            while not self._stop and (time.time() - start) < self.duration_s:
                ret, frame = cap.read()
                if not ret or frame is None:
                    self.logger.warning("Frame read failed during recording; stopping early")
                    break

                writer.write(frame)
                frames_written += 1

                await asyncio.sleep(0)
        finally:
            try:
                writer.release()
            except Exception:
                pass
            try:
                cap.release()
            except Exception:
                pass

        if self._stop:
            if self.status_callback:
                await self.status_callback("Stopped")
            # Remove partial file
            try:
                if os.path.isfile(video_path):
                    os.remove(video_path)
            except Exception:
                pass
            return

        if frames_written <= 0 or (not os.path.isfile(video_path)) or os.path.getsize(video_path) == 0:
            if self.status_callback:
                await self.status_callback("No video captured")
            return

        meta["frames_written"] = frames_written
        meta["file_bytes"] = int(os.path.getsize(video_path))

        try:
            with open(os.path.join(folder, "metadata.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed writing metadata.json: {e!r}")

        if self.status_callback:
            await self.status_callback("Bundling video")

        artifact_id = self.artifact_manager.create_zip_artifact_from_folder(
            source_id=self.source_id,
            operation_id=self.operation_id,
            folder=folder,
            name=self.artifact_name,
            metadata=meta,
            arc_prefix=f"video_{self.operation_id}",
        )

        self.logger.info(f"Video bundle registered: artifact_id={artifact_id}, opid={self.operation_id}")

        # Dashboard alert (toggleable)
        if self.emit_alert and self.alert_callback:
            try:
                payload = {
                    "type": "video_capture",
                    "artifact_id": artifact_id,
                    "operation_id": self.operation_id,
                    "duration_s": self.duration_s,
                    "fps": self.fps,
                    "frames_written": frames_written,
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
                self.logger.exception("alert_callback failed while reporting video_capture")

        # TAK pin (toggleable)
        if self.emit_tak_pin and self.tak_cot_callback:
            try:
                short_id = str(artifact_id)[:8]
                tak_msg = {
                    "msg_type": "pin",
                    "uid": f"video_{artifact_id}",
                    "remarks": f"Video capture ({self.duration_s:.0f}s) [{short_id}]",
                    "lat": True,
                    "lon": True,
                    "alt": True,
                    "time": True,
                    "tak_icon": self.tak_icon,
                    "opid": self.opid,
                    "alert_kind": "video_capture",
                    "alert_summary": f"Video capture ({self.duration_s:.0f}s)",
                    "artifact_id": artifact_id,
                    "operation_id": self.operation_id,
                    "sensor_node_id": self.sensor_node_id,
                    "name": self.artifact_name,
                }
                await self.tak_cot_callback(tak_msg)
            except Exception:
                self.logger.exception("tak_cot_callback failed while emitting video pin")

        if self.status_callback:
            await self.status_callback("Idle")


if __name__ == "__main__":
    from fissure.utils.plugins.test_operation import run_test
    run_test(OperationMain, {}, {})