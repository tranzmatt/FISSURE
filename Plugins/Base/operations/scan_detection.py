#! /usr/bin/env python3
"""Scan Detection using fixed_threshold_b2x0 in-process, with message-port capture."""

import asyncio
import logging
import os
import sys
import time
from typing import Any, Callable, Dict, Union


PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FISSURE_REPO_ROOT = os.path.abspath(os.path.join(PLUGIN_ROOT, "..", ".."))
FLOW_GRAPH_DIR = os.path.join(
    PLUGIN_ROOT,
    "flow_graphs",
    "fixed_detection_flow_graphs",
)

for path in (FISSURE_REPO_ROOT, PLUGIN_ROOT, FLOW_GRAPH_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from fissure.utils.plugins.operations import Operation
except ImportError:
    if FISSURE_REPO_ROOT not in sys.path:
        sys.path.insert(0, FISSURE_REPO_ROOT)

    if PLUGIN_ROOT not in sys.path:
        sys.path.insert(0, PLUGIN_ROOT)

    from fissure.utils.plugins.operations import Operation

from gnuradio import gr
import pmt

from fixed_threshold_b2x0 import fixed_threshold_b2x0


class DetectionSink(gr.basic_block):
    """Receives GNU Radio messages and forwards each payload string to a callback."""

    def __init__(
        self,
        callback: Callable[[str], None],
        logger: Union[logging.Logger, None] = None,
    ):
        gr.basic_block.__init__(
            self,
            name="scan_detection_sink",
            in_sig=None,
            out_sig=None,
        )

        self._callback = callback
        self._logger = logger or logging.getLogger(__name__)

        self.message_port_register_in(pmt.intern("in"))
        self.set_msg_handler(pmt.intern("in"), self._handle_msg)

    def _handle_msg(self, msg):
        try:
            if pmt.is_symbol(msg):
                text = pmt.symbol_to_string(msg)
            else:
                text = pmt.write_string(msg)

            if self._callback:
                self._callback(text)

        except Exception as e:
            self._logger.error(f"[SCAN] DetectionSink error: {e}")


class OperationMain(Operation):
    """Scan detection across preset frequencies using fixed_threshold_b2x0."""

    def __init__(
        self,
        dwell_s: Union[str, float] = 10.0,
        alert_interval_s: Union[str, float] = 10.0,
        description: str = "Scan detection across preset bands",
        dev: str = "",
        node_uid: str = "",
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback: Union[Callable, None] = None,
        tak_cot_callback: Union[Callable, None] = None,
        status_callback: Union[Callable, None] = None,
    ) -> None:
        super().__init__(
            node_uid=node_uid,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
            status_callback=status_callback,
        )

        self.dev = str(dev or "").strip()
        self.resource_args = {"dev": self.dev}

        self.dwell_s = max(0.1, self._float(dwell_s, 10.0))
        self.alert_interval_s = max(0.0, self._float(alert_interval_s, 10.0))
        self.description = description or "Scan detection across preset bands"

        self.SCAN_FREQS = [
            311e6,
            903e6,
            915e6,
            927e6,
            2412e6,
            2437e6,
            2462e6,
        ]

        self.IGNORE_WINDOW = 0.5

        self.logger.info(
            "scan_detection init params: "
            f"dwell_s={self.dwell_s}, "
            f"alert_interval_s={self.alert_interval_s}, "
            f"description={self.description}, "
            f"dev={self.dev}"
        )

    @staticmethod
    def get_resources(dev: str = "") -> Dict[str, Any]:
        return {
            "usrp": {
                "type": "sdr",
                "model": "USRP B2x0",
                "serial": dev,
                "description": "USRP B2x0",
                "required": True,
            }
        }

    async def run(self) -> None:
        """Run scan detection."""

        try:
            await self._run_scan_detection()

        except asyncio.CancelledError:
            self.logger.info("scan_detection cancelled")
            raise

        except Exception:
            self.logger.exception("scan_detection failed")
            raise

        finally:
            if self.status_callback:
                try:
                    await self.status_callback("Idle")
                except Exception:
                    self.logger.exception("scan_detection status_callback failed while setting Idle")

    async def _run_scan_detection(self) -> None:
        self.logger.info("[SCAN] Creating flow graph in-process.")

        tb = fixed_threshold_b2x0()

        loop = asyncio.get_running_loop()
        detections: asyncio.Queue[str] = asyncio.Queue()

        def enqueue_detection(text: str):
            loop.call_soon_threadsafe(detections.put_nowait, text)

        sink = DetectionSink(enqueue_detection, logger=self.logger)

        try:
            tb.msg_connect((tb.epy_block_0, "detected_signals"), (sink, "in"))
        except Exception:
            self.logger.exception("[SCAN] Failed to connect detection message sink")
            raise

        try:
            tb.start()

            first_freq_hz = self.SCAN_FREQS[0]
            tb.set_rx_freq(first_freq_hz)

            first_freq_mhz = first_freq_hz / 1e6
            self.logger.info(f"[SCAN] Initial tuning to {first_freq_mhz:.3f} MHz")

            if self.status_callback:
                await self.status_callback(f"Running: Scan tuned {first_freq_mhz:.3f} MHz")

            last_alert_by_freq: Dict[float, float] = {}
            scan_index = 0

            self.logger.info("[SCAN] Flow graph started.")

            while not self._stop:
                freq_hz = self.SCAN_FREQS[scan_index]
                scan_index = (scan_index + 1) % len(self.SCAN_FREQS)
                freq_mhz = freq_hz / 1e6

                try:
                    tb.set_rx_freq(freq_hz)
                    last_retune = time.time()

                    self.logger.info(f"[SCAN] Retuned via tb.set_rx_freq({freq_mhz:.3f} MHz)")

                    if self.status_callback:
                        await self.status_callback(f"Running: Scan tuned {freq_mhz:.3f} MHz")

                except Exception as e:
                    self.logger.error(f"[SCAN] Retune failed: {e}")
                    await asyncio.sleep(self.dwell_s)
                    continue

                dwell_end = last_retune + self.dwell_s
                detections_seen = 0

                while time.time() < dwell_end and not self._stop:
                    try:
                        text = await asyncio.wait_for(detections.get(), timeout=0.05)
                    except asyncio.TimeoutError:
                        continue

                    if "TSI:" not in text:
                        continue

                    text = text[text.index("TSI:") :]

                    if not text.startswith("TSI:/Signal Found"):
                        continue

                    now = time.time()

                    if now - last_retune < self.IGNORE_WINDOW:
                        continue

                    parts = text.split("/")
                    if len(parts) < 5:
                        self.logger.warning(f"[SCAN] Unexpected TSI format: {text}")
                        continue

                    _, _label, freq_str, rssi_str, tstamp_str = parts[:5]

                    try:
                        det_freq_hz = float(freq_str)
                        det_rssi_dbm = float(rssi_str)
                        flowgraph_timestamp = float(tstamp_str)
                    except ValueError:
                        self.logger.warning(f"[SCAN] Could not parse TSI line: {text}")
                        continue

                    detections_seen += 1

                    last = last_alert_by_freq.get(freq_hz, 0.0)
                    if now - last < self.alert_interval_s:
                        continue

                    last_alert_by_freq[freq_hz] = now

                    await self._emit_detection(
                        det_freq_hz=det_freq_hz,
                        det_rssi_dbm=det_rssi_dbm,
                        flowgraph_timestamp=flowgraph_timestamp,
                        scan_frequency_hz=freq_hz,
                        last_retune=last_retune,
                    )

                self.logger.info(
                    f"[SCAN] Completed dwell @ {freq_mhz:.3f} MHz, "
                    f"detections_seen={detections_seen}"
                )

        finally:
            self.logger.info("[SCAN] Stopping flow graph...")

            try:
                tb.stop()
            except Exception:
                self.logger.exception("[SCAN] tb.stop failed")

            try:
                tb.wait()
            except Exception:
                self.logger.exception("[SCAN] tb.wait failed")

            self.logger.info("[SCAN] Stopped.")

    async def _emit_detection(
        self,
        *,
        det_freq_hz: float,
        det_rssi_dbm: float,
        flowgraph_timestamp: float,
        scan_frequency_hz: float,
        last_retune: float,
    ) -> None:
        ts = time.time()
        cb_timeout_s = 2.0

        scan_freq_mhz = round(scan_frequency_hz / 1e6, 3)
        uid = f"SCAN-{int(round(scan_frequency_hz / 1e6))}MHz"

        self.logger.info(
            f"[TAK+ALERT] UID={uid} "
            f"det={det_freq_hz / 1e6:.3f} MHz RSSI={det_rssi_dbm} dBm"
        )

        detection = {
            "kind": "detection",
            "event_type": "detection",
            "node_uid": self.node_uid,
            "source_id": self.node_uid,
            "description": self.description,
            "frequency_hz": int(det_freq_hz),
            "frequency_mhz": float(det_freq_hz) / 1e6,
            "power_dbm": float(det_rssi_dbm),
            "timestamp": int(ts),
            "flowgraph_timestamp": float(flowgraph_timestamp),
            "detector": "scan_detection",
            "opid": self.opid,
            "flowgraph": "fixed_threshold_b2x0",
            "device": "USRP B2x0",
            "scan_frequency_hz": int(scan_frequency_hz),
            "scan_frequency_mhz": scan_freq_mhz,
            "retune_age_s": round(ts - last_retune, 3),
        }

        if self.tak_cot_callback:
            try:
                await asyncio.wait_for(
                    self.tak_cot_callback(
                        {
                            "msg_type": "event",
                            "uid": f"scan-detection-{self.node_uid}-{int(ts)}",
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
                self.logger.exception("[SCAN] tak_cot_callback failed")

        if self.alert_callback:
            try:
                await asyncio.wait_for(
                    self.alert_callback(
                        self.node_uid,
                        self.opid,
                        f"Scan detection @ {det_freq_hz / 1e6:.3f} MHz, RSSI {det_rssi_dbm} dBm",
                        self.logger,
                    ),
                    timeout=cb_timeout_s,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger.exception("[SCAN] alert_callback failed")

    @staticmethod
    def _float(value, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)


if __name__ == "__main__":
    from fissure.utils.plugins.test_operation import run_test

    run_test(OperationMain, {}, {})