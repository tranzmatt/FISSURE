#! /usr/bin/env python3
"""Fixed Detection"""

import asyncio
import contextlib
import logging
import os
import sys
import time
from typing import Any, Callable, Dict, Union


PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FISSURE_ROOT = os.path.abspath(os.path.join(PLUGIN_ROOT, "..", ".."))
FLOW_GRAPH_DIR = os.path.join(
    PLUGIN_ROOT,
    "flow_graphs",
    "fixed_detection_flow_graphs",
)

for path in (FISSURE_ROOT, PLUGIN_ROOT, FLOW_GRAPH_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from fissure.utils.plugins.operations import Operation


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

        self.freq_mhz = float(freq_mhz)
        self.min_detection_interval_s = float(min_detection_interval_s)
        self.description = description or "Fixed detection"

        self.resource_args = {
            "freq_mhz": self.freq_mhz,
        }

        self.logger.info(
            f"fixed_detection init params: freq_mhz={self.freq_mhz}, "
            f"min_detection_interval_s={self.min_detection_interval_s}, "
            f"description={self.description}"
        )

    @staticmethod
    def get_resources(
        freq_mhz: float = 915.0,
    ) -> Dict[str, Any]:
        return {}

    async def run(self) -> None:
        """Run the Fixed Detection operation."""

        alert_interval_s = self.min_detection_interval_s
        last_alert_time = 0.0
        cb_timeout_s = 2.0

        configured_freq_hz = self.freq_mhz * 1_000_000.0

        script_path = os.path.join(
            FLOW_GRAPH_DIR,
            "fixed_threshold_b2x0.py",
        )

        if not os.path.isfile(script_path):
            self.logger.error(f"Fixed detection flow graph not found: {script_path}")
            return

        cmd = [
            sys.executable,
            "-u",
            script_path,
            "--rx-freq-default",
            str(configured_freq_hz),
        ]

        self.logger.info(f"Starting fixed detection flow graph: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=FLOW_GRAPH_DIR,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def _log_stderr() -> None:
            if process.stderr is None:
                return

            while True:
                line = await process.stderr.readline()
                if not line:
                    break

                text = line.decode(errors="ignore").strip()
                if text:
                    self.logger.warning(f"fixed_detection stderr: {text}")

        stderr_task = asyncio.create_task(_log_stderr())

        try:
            if process.stdout is None:
                self.logger.error("Fixed detection flow graph stdout pipe was not created.")
                return

            while not self._stop:
                try:
                    line_bytes = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=0.25,
                    )
                except asyncio.TimeoutError:
                    continue

                if not line_bytes:
                    self.logger.info("Fixed detection flow graph exited: EOF on stdout.")
                    break

                text = line_bytes.decode(errors="ignore").strip()
                if not text:
                    continue

                self.logger.debug(f"fixed_detection stdout: {text}")

                if "TSI:" not in text:
                    continue

                text = text[text.index("TSI:") :]

                parts = text.split("/")
                if len(parts) < 5:
                    self.logger.warning(f"Unexpected TSI format: {text}")
                    continue

                _, label, freq_str, rssi_str, tstamp_str = parts[:5]

                try:
                    freq_hz = float(freq_str)
                    rssi_dbm = float(rssi_str)
                    flowgraph_timestamp = float(tstamp_str)
                except ValueError:
                    self.logger.warning(f"Could not parse TSI line: {text}")
                    continue

                now = time.time()
                if now - last_alert_time < alert_interval_s:
                    continue

                last_alert_time = now
                ts = time.time()

                detection = {
                    "kind": "detection",
                    "event_type": "detection",
                    "node_uid": self.node_uid,
                    "source_id": self.node_uid,
                    "description": self.description,
                    "label": label,
                    "frequency_hz": int(freq_hz),
                    "frequency_mhz": float(freq_hz) / 1e6,
                    "power_dbm": float(rssi_dbm),
                    "timestamp": int(ts),
                    "flowgraph_timestamp": float(flowgraph_timestamp),
                    "detector": "fixed_detection",
                    "opid": self.opid,
                    "flowgraph": "fixed_threshold_b2x0",
                    "device": "USRP B2x0",
                    "configured_frequency_mhz": self.freq_mhz,
                }

                self.logger.info(f"fixed_detection parsed detection: {detection}")

                if self.alert_callback:
                    try:
                        await asyncio.wait_for(
                            self.alert_callback(
                                self.node_uid,
                                self.opid,
                                f"{self.description} @ {freq_hz / 1e6:.3f} MHz, RSSI {rssi_dbm} dBm",
                                self.logger,
                            ),
                            timeout=cb_timeout_s,
                        )
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        self.logger.exception("alert_callback failed")
                else:
                    self.logger.warning("fixed_detection has no alert_callback")

                if self.tak_cot_callback:
                    try:
                        await asyncio.wait_for(
                            self.tak_cot_callback(
                                {
                                    "msg_type": "event",
                                    "uid": f"fixed-detection-{self.node_uid}-{int(ts)}",
                                    "lat": True,
                                    "lon": True,
                                    "alt": True,
                                    "time": True,
                                    "data": detection,
                                    "opid": self.opid,
                                    "tak_icon": "r-x-fissure-detection",
                                }
                            ),
                            timeout=cb_timeout_s,
                        )
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        self.logger.exception("tak_cot_callback failed")
                else:
                    self.logger.warning("fixed_detection has no tak_cot_callback")

        finally:
            if stderr_task and not stderr_task.done():
                stderr_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await stderr_task

            if process.returncode is None:
                self.logger.info("Terminating fixed detection flow graph process...")
                process.terminate()

                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.logger.warning("Fixed detection flow graph did not terminate, killing...")
                    process.kill()
                    await process.wait()

            self.logger.info("Fixed Detection exiting.")


if __name__ == "__main__":
    from fissure.utils.plugins.test_operation import run_test

    run_test(OperationMain, {}, {})