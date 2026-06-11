#! /usr/bin/env python3
"""Fixed Detection
"""
import asyncio
import logging
import os
import sys
from typing import Any, Callable, Dict, Union

try:
    from fissure.utils.plugins.operations import Operation
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
    from fissure.utils.plugins.operations import Operation

# add gr_flowgraphs
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from fixed_detection_flow_graphs.fixed_threshold_b2x0 import fixed_threshold_b2x0

import json
import time


class OperationMain(Operation):
    """Fixed Detection"""

    def __init__(
        self,
        freq_mhz: float = 915.0,
        min_detection_interval_s: float = 10.0,
        description: str = "Fixed detection",
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

        # --- parameters (from UI schema) ---
        self.freq_mhz = float(freq_mhz)
        self.min_detection_interval_s = float(min_detection_interval_s)
        self.description = description or "Fixed detection"

        # --- placeholders for future resource management ---
        self.resource_args = {
            # keep structure for future expansion
            "freq_mhz": self.freq_mhz,
        }

        self.logger.info(f"fixed_detection init params: freq_mhz={self.freq_mhz}, min_detection_interval_s={self.min_detection_interval_s}, description={self.description}")

    @staticmethod
    def get_resources(
        # keep signature flexible for future placeholders
        freq_mhz: float = 915.0,
    ) -> Dict[str, Any]:
        # Placeholder: return empty for now, but keep the hook
        # Later you can declare SDR model, bandwidth, etc. keyed off freq_mhz.
        return {}

    async def run(self) -> None:
        """
        Run the Fixed Detection Operation.
        """

        ALERT_INTERVAL = self.min_detection_interval_s
        last_alert_time = 0.0

        # Convert configured frequency once
        configured_freq_hz = self.freq_mhz * 1000000.0

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

        self.logger.info(f"Starting fixed detection flowgraph: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            while not self._stop:

                # --- INTERRUPTIBLE READ ---
                try:
                    line_bytes = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=0.25,
                    )
                except asyncio.TimeoutError:
                    continue

                if not line_bytes:
                    self.logger.info("Fixed detection flowgraph exited (EOF on stdout).")
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

                _, label, freq_str, rssi_str, tstamp_str = parts[:5]

                try:
                    freq_hz = float(freq_str)
                    rssi_dbm = float(rssi_str)
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
                            "description": self.description,
                            "frequency_hz": int(freq_hz),
                            "frequency_mhz": float(freq_hz) / 1e6,
                            "power_dbm": float(rssi_dbm),
                            "timestamp": ts,
                            "detector": "fixed_detection",
                            "opid": self.opid,
                            "flowgraph": "fixed_threshold_b2x0",
                            "device": "USRP B2x0",
                            "configured_frequency_mhz": self.freq_mhz,
                        }

                        await self.tak_cot_callback({
                            "msg_type": "event",
                            "uid": f"fixed-detection-{int(ts)}",
                            "lat": True,
                            "lon": True,
                            "alt": True,
                            "time": True,
                            "data": detection,
                            "opid": self.opid,
                            "tak_icon": "r-x-fissure-detection",
                        })

                    if self.alert_callback:
                        await self.alert_callback(
                            self.node_uid,
                            self.opid,
                            f"{self.description} @ {freq_hz/1e6:.3f} MHz, RSSI {rssi_dbm} dBm",
                            self.logger,
                        )

                except Exception as e:
                    self.logger.error(f"Error sending TAK/alert from fixed_detection: {e}")

        finally:
            # Graceful shutdown
            if process.returncode is None:
                self.logger.info("Terminating fixed detection flowgraph process...")
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.logger.warning("Flowgraph did not terminate, killing...")
                    process.kill()
                    await process.wait()

            # Drain stderr safely
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
                        "Fixed detection flowgraph stderr:\n"
                        + stderr_data.decode(errors="ignore")
                    )

if __name__ == "__main__":
    from fissure.utils.plugins.test_operation import run_test
    run_test(OperationMain, {}, {})
