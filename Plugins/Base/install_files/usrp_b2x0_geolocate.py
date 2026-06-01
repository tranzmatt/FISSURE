#! /usr/bin/env python3
"""USRP B2x0 Geolocate

Hub-side multilateration geolocation using the fixed threshold B2x0 detector
as a subprocess, mirroring the working LFM beacon geolocate pattern.
"""
import asyncio
import json
import logging
import os
import sys
import time
from typing import Any, Callable, Dict, Optional, Union

try:
    from fissure.utils.plugins.operations import Operation
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from fissure.utils.plugins.operations import Operation


class OperationMain(Operation):
    def __init__(
        self,
        sensor_node_id: Union[int, str] = 0,
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback: Union[Callable, None] = None,
        tak_cot_callback: Union[Callable, None] = None,
        status_callback: Union[Callable, None] = None,
        target_callback: Union[Callable, None] = None,
        artifact_manager=None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            sensor_node_id=sensor_node_id,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
            status_callback=status_callback,
            target_callback=target_callback,
            artifact_manager=artifact_manager,
        )

        self.parameters: Dict[str, Any] = parameters or {}

        self.target_id: str = ""
        self.frequency_mhz: float = 2412.0
        self.min_detection_interval_s: float = 1.0
        self.description: str = "USRP B2x0 geolocation"

        self.gpsd_host: str = "127.0.0.1"
        self.gpsd_port: int = 2947
        self.gps_refresh_interval: float = 1.0

        self._gps_stop = asyncio.Event()
        self._current_position: Dict[str, Any] = {"lat": None, "lon": None, "alt": 0.0}
        self._last_emit_time: float = 0.0

    def _apply_parameters_from_runner(self) -> None:
        p = getattr(self, "parameters", None)
        self.logger.info(f"_apply_parameters_from_runner self.parameters={p!r} type={type(p)}")

        if not isinstance(p, dict):
            return

        self.target_id = str(p.get("target_id", self.target_id)).strip()

        try:
            self.frequency_mhz = float(p.get("frequency_mhz", p.get("freq_mhz", self.frequency_mhz)))
        except Exception:
            self.frequency_mhz = 2412.0

        try:
            self.min_detection_interval_s = float(
                p.get("min_detection_interval_s", p.get("emit_every_s", self.min_detection_interval_s))
            )
        except Exception:
            self.min_detection_interval_s = 1.0

        self.description = str(p.get("description", self.description)).strip() or "USRP B2x0 geolocation"
        self.gpsd_host = str(p.get("gpsd_host", self.gpsd_host))
        self.gpsd_port = int(p.get("gpsd_port", self.gpsd_port))
        self.gps_refresh_interval = float(p.get("gps_refresh_interval", self.gps_refresh_interval))

    async def _gps_loop(self) -> None:
        self.logger.info("Starting GPS loop (GPSD)")
        buf = ""

        while (not self._stop) and (not self._gps_stop.is_set()):
            try:
                reader, writer = await asyncio.open_connection(self.gpsd_host, self.gpsd_port)
                writer.write(b'?WATCH={"enable":true,"json":true}\n')
                await writer.drain()

                while (not self._stop) and (not self._gps_stop.is_set()):
                    data = await reader.read(4096)
                    if not data:
                        await asyncio.sleep(0.5)
                        continue

                    buf += data.decode(errors="ignore")

                    while "\n" in buf:
                        if self._stop or self._gps_stop.is_set():
                            break

                        line, buf = buf.split("\n", 1)
                        if not line.strip():
                            continue

                        try:
                            msg = json.loads(line)
                        except Exception:
                            continue

                        if msg.get("class") == "TPV" and msg.get("mode", 0) >= 2:
                            lat = msg.get("lat")
                            lon = msg.get("lon")
                            alt = msg.get("altMSL") or msg.get("altHAE") or 0.0

                            if lat is not None and lon is not None:
                                self._current_position.update({
                                    "lat": float(lat),
                                    "lon": float(lon),
                                    "alt": float(alt),
                                })

                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

            except Exception as e:
                self.logger.warning(f"GPS error: {e}")
                await asyncio.sleep(2.0)

    async def _emit_detection(
        self,
        *,
        frequency_hz: float,
        metric_db: float,
        det_time: float,
    ) -> None:
        if not self.tak_cot_callback:
            return

        detection = {
            "event_type": "detection",
            "detection_kind": "usrp_b2x0_geolocate",
            "target_id": self.target_id,
            "sensor_node_id": str(self.sensor_node_id),
            "frequency_hz": int(frequency_hz),
            "frequency_mhz": float(frequency_hz) / 1e6,
            "power_dbm": float(metric_db),
            "timestamp": float(det_time),
            "detector": "usrp_b2x0_geolocate",
            "opid": self.opid,
            "flowgraph": "fixed_threshold_b2x0",
            "device": "USRP B2x0",
            "configured_frequency_mhz": self.frequency_mhz,
            "description": self.description,
        }

        await self.tak_cot_callback({
            "msg_type": "event",
            "uid": f"usrp-b2x0-geolocate-{self.target_id}-{int(det_time)}",
            "lat": True,
            "lon": True,
            "alt": True,
            "time": True,
            "data": detection,
            "opid": self.opid,
            "tak_icon": "r-x-fissure-detection",
        })

    async def run(self) -> None:
        self._apply_parameters_from_runner()

        if not self.target_id:
            raise RuntimeError("usrp_b2x0_geolocate requires target_id from hub geolocation start")

        if self.status_callback:
            await self.status_callback(f"Geolocating target {self.target_id} with USRP B2x0")

        configured_freq_hz = self.frequency_mhz * 1000000.0
        script_path = os.path.join(
            os.path.dirname(__file__),
            "fixed_detection_flow_graphs",
            "fixed_threshold_b2x0.py",
        )

        cmd = [
            sys.executable,
            script_path,
            "--rx-freq-default", str(configured_freq_hz),
        ]

        self.logger.info(f"Starting USRP B2x0 fixed-threshold geolocate flowgraph: {' '.join(cmd)}")

        gps_task = asyncio.create_task(self._gps_loop())

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            while not self._stop:
                lat = self._current_position.get("lat")
                lon = self._current_position.get("lon")
                if lat is None or lon is None:
                    await asyncio.sleep(0.25)
                    continue

                try:
                    line_bytes = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=0.25,
                    )
                except asyncio.TimeoutError:
                    continue

                if not line_bytes:
                    self.logger.info("USRP B2x0 fixed-threshold flowgraph exited (EOF on stdout).")
                    break

                line = line_bytes.strip()
                if not line:
                    continue

                text = line.decode(errors="ignore")

                if not text.startswith("TSI:"):
                    continue

                parts = text.split("/")
                if len(parts) < 5:
                    self.logger.warning(f"Unexpected TSI format: {text}")
                    continue

                _, label, freq_str, metric_str, tstamp_str = parts[:5]

                try:
                    frequency_hz = float(freq_str)
                    metric = float(metric_str)
                    det_time = float(tstamp_str)
                except ValueError:
                    self.logger.warning(f"Could not parse TSI line: {text}")
                    continue

                now = time.time()
                if (now - self._last_emit_time) < self.min_detection_interval_s:
                    continue
                self._last_emit_time = now

                self.logger.info(
                    f"USRP B2x0 measurement for {self.target_id}: "
                    f"label={label}, freq_mhz={frequency_hz/1e6:.6f}, metric={metric:.2f}, "
                    f"lat={lat}, lon={lon}"
                )

                await self._emit_detection(
                    frequency_hz=frequency_hz,
                    metric_db=metric,
                    det_time=det_time if det_time > 0 else now,
                )

                if self.status_callback:
                    await self.status_callback(
                        f"Tracking {self.target_id} @ {frequency_hz/1e6:.3f} MHz"
                    )

        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.logger.exception(f"USRP B2x0 geolocate operation error: {e}")
        finally:
            self._gps_stop.set()
            try:
                await asyncio.wait_for(gps_task, timeout=3.0)
            except Exception:
                pass

            if process.returncode is None:
                self.logger.info("Terminating USRP B2x0 fixed-threshold flowgraph process...")
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.logger.warning("Flowgraph did not terminate, killing...")
                    process.kill()
                    await process.wait()

            if process.stderr:
                try:
                    stderr_data = await asyncio.wait_for(process.stderr.read(), timeout=1.0)
                except asyncio.TimeoutError:
                    stderr_data = b""

                if stderr_data:
                    self.logger.debug(
                        "USRP B2x0 fixed-threshold flowgraph stderr:\n"
                        + stderr_data.decode(errors="ignore")
                    )

            self.logger.info("USRP B2x0 geolocate operation stopped cleanly.")


if __name__ == "__main__":
    from fissure.utils.plugins.test_operation import run_test
    run_test(OperationMain, {}, {})