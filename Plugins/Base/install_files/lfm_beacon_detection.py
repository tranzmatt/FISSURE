#! /usr/bin/env python3
"""LFM Beacon Detection
"""
import asyncio
import logging
import os
import sys
import time
from typing import Any, Callable, Dict, Union

try:
    from fissure.utils.plugins.operations import Operation
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
    from fissure.utils.plugins.operations import Operation

# add gr_flowgraphs
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from fixed_detection_flow_graphs.lfm_beacon_rtlsdr import lfm_beacon_rtlsdr


class OperationMain(Operation):
    """LFM Beacon Detection"""

    def __init__(
        self,
        freq_mhz: float = 433.0,
        min_detection_interval_s: float = 1.0,
        description: str = "LFM beacon detection",
        node_uid: str = "",
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback: Union[Callable, None] = None,
        tak_cot_callback: Union[Callable, None] = None,
    ) -> None:
        super().__init__(
            node_uid=node_uid,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
        )

        self.freq_mhz = float(freq_mhz)
        self.min_detection_interval_s = float(min_detection_interval_s)
        self.description = description or "LFM beacon detection"

        self.resource_args = {
            "freq_mhz": self.freq_mhz,
        }

        self.logger.info(
            f"lfm_beacon_detection init params: "
            f"freq_mhz={self.freq_mhz}, "
            f"min_detection_interval_s={self.min_detection_interval_s}, "
            f"description={self.description}"
        )

    @staticmethod
    def get_resources(
        freq_mhz: float = 433.0,
    ) -> Dict[str, Any]:
        return {}

    async def run(self) -> None:
        """
        Run the LFM Beacon Detection Operation.
        """
        ALERT_INTERVAL = self.min_detection_interval_s
        last_alert_time = 0.0

        configured_freq_hz = self.freq_mhz * 1000000.0

        script_path = os.path.join(
            os.path.dirname(__file__),
            "lfm_beacon_detection_flow_graphs",
            "lfm_beacon_rtlsdr.py",
        )

        cmd = [
            sys.executable,
            script_path,
            "--rx-freq-default", str(configured_freq_hz),
        ]

        self.logger.info(f"Starting LFM beacon flowgraph: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            while not self._stop:
                try:
                    line_bytes = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=0.25,
                    )
                except asyncio.TimeoutError:
                    continue

                if not line_bytes:
                    self.logger.info("LFM beacon flowgraph exited (EOF on stdout).")
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
                    freq_hz = float(freq_str)
                    metric = float(metric_str)
                    det_time = float(tstamp_str)
                except ValueError:
                    self.logger.warning(f"Could not parse TSI line: {text}")
                    continue

                now = time.time()
                if now - last_alert_time < ALERT_INTERVAL:
                    continue

                last_alert_time = now

                try:
                    if self.tak_cot_callback:
                        ts = time.time()

                        detection = {
                            "event_type": "detection",
                            "node_uid": self.node_uid,
                            "description": self.description,
                            "frequency_hz": int(freq_hz),
                            "frequency_mhz": float(freq_hz) / 1e6,
                            "power_dbm": float(metric),  # metric for now
                            "timestamp": ts,
                            "detector": "lfm_beacon_detection",
                            "opid": self.opid,
                            "flowgraph": "lfm_beacon_rtlsdr",
                            "device": "RTL-SDR",
                            "configured_frequency_mhz": self.freq_mhz,
                        }

                        await self.tak_cot_callback({
                            "msg_type": "event",
                            "uid": f"lfm-beacon-detection-{int(ts)}",
                            "lat": True,
                            "lon": True,
                            "alt": True,
                            "time": True,
                            "data": detection,
                            "opid": self.opid,
                        })

                    if self.alert_callback:
                        await self.alert_callback(
                            self.node_uid,
                            self.opid,
                            f"{self.description} @ {freq_hz/1e6:.3f} MHz, metric {metric:.2f}",
                            self.logger,
                        )

                except Exception as e:
                    self.logger.error(f"Error sending TAK/alert from lfm_beacon_detection: {e}")

        finally:
            if process.returncode is None:
                self.logger.info("Terminating LFM beacon flowgraph process...")
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.logger.warning("Flowgraph did not terminate, killing...")
                    process.kill()
                    await process.wait()

            if process.stderr:
                try:
                    stderr_data = await asyncio.wait_for(
                        process.stderr.read(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    stderr_data = b""

                if stderr_data:
                    self.logger.debug(
                        "LFM beacon flowgraph stderr:\n"
                        + stderr_data.decode(errors="ignore")
                    )


if __name__ == "__main__":
    from fissure.utils.plugins.test_operation import run_test
    run_test(OperationMain, {}, {})