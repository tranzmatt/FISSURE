#! /usr/bin/env python3
"""Scan Detection using fixed_threshold_b2x0 in-process, with message-port capture.
"""

import asyncio
import sys
import time
import logging
import os
from typing import Any, Callable, Dict, Union

from fissure.utils.plugins.operations import Operation

from gnuradio import gr
import pmt

sys.path.insert(0, os.path.dirname(__file__))
from fixed_detection_flow_graphs.fixed_threshold_b2x0 import fixed_threshold_b2x0


class DetectionSink(gr.basic_block):
    """
    Simple GR block that receives messages and forwards the payload
    to a Python callback (string).
    """
    def __init__(self, callback: Callable[[str], None], logger: logging.Logger = None):
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

    def __init__(
        self,
        dwell_s: float = 10.0,
        alert_interval_s: float = 10.0,
        description: str = "Scan detection across preset bands",
        dev: str = '',
        sensor_node_id: Union[int, str] = 0,
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback: Union[Callable, None] = None,
        tak_cot_callback: Union[Callable, None] = None,
        status_callback: Union[Callable, None] = None,
    ) -> None:

        super().__init__(
            sensor_node_id=sensor_node_id,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
            status_callback=status_callback,
        )

        self.dev = dev
        self.resource_args = {'dev': self.dev}

        self.dwell_s = float(dwell_s)
        self.alert_interval_s = float(alert_interval_s)
        self.description = description or "Scan detection across preset bands"

        # Preset scan list
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
            f"scan_detection init params: dwell_s={self.dwell_s}, "
            f"alert_interval_s={self.alert_interval_s}, description={self.description}"
        )

    @staticmethod
    def get_resources(dev: str = '') -> Dict[str, Any]:
        return {
            'usrp': {
                'type': 'sdr',
                'model': 'USRP B2x0',
                'serial': dev,
                'description': 'USRP B2x0',
                'required': True,
            }
        }

    async def run(self) -> None:
        self.logger.info("[SCAN] Creating flowgraph in-process…")

        tb = fixed_threshold_b2x0()

        loop = asyncio.get_running_loop()
        detections: asyncio.Queue[str] = asyncio.Queue()

        def enqueue_detection(text: str):
            loop.call_soon_threadsafe(detections.put_nowait, text)

        sink = DetectionSink(enqueue_detection, logger=self.logger)
        tb.msg_connect((tb.epy_block_0, 'detected_signals'), (sink, 'in'))

        tb.start()

        first_freq_hz = self.SCAN_FREQS[0]
        first_freq_mhz = first_freq_hz / 1e6
        tb.set_rx_freq(first_freq_hz)

        self.logger.info(f"[SCAN] Initial tuning to {first_freq_mhz:.3f} MHz")

        if self.status_callback:
            await self.status_callback(f"Running: Scan tuned {first_freq_mhz:.3f} MHz")

        last_alert_by_freq: Dict[float, float] = {}
        scan_index = 0
        last_retune = time.time()

        self.logger.info("[SCAN] Flowgraph started.")

        try:
            while not self._stop:

                freq_hz = self.SCAN_FREQS[scan_index]
                scan_index = (scan_index + 1) % len(self.SCAN_FREQS)
                freq_mhz = freq_hz / 1e6

                # RETUNE
                try:
                    tb.set_rx_freq(freq_hz)
                    self.logger.info(f"[SCAN] Retuned via tb.set_rx_freq({freq_mhz:.3f} MHz)")
                    last_retune = time.time()

                    if self.status_callback:
                        await self.status_callback(f"Running: Scan tuned {freq_mhz:.3f} MHz")

                except Exception as e:
                    self.logger.error(f"[SCAN] Retune failed: {e}")
                    await asyncio.sleep(self.dwell_s)
                    continue

                dwell_end = last_retune + self.dwell_s
                detections_seen = 0

                # DWELL LOOP
                while time.time() < dwell_end and not self._stop:
                    try:
                        text = detections.get_nowait()
                    except asyncio.QueueEmpty:
                        await asyncio.sleep(0.05)
                        continue

                    if not text.startswith("TSI:/Signal Found"):
                        continue

                    now = time.time()

                    if now - last_retune < self.IGNORE_WINDOW:
                        continue

                    parts = text.split("/")
                    if len(parts) < 5:
                        continue

                    _, _, f_str, rssi_str, _tstamp_str = parts[:5]

                    try:
                        det_freq_hz = float(f_str)
                        det_rssi_dbm = float(rssi_str)
                    except ValueError:
                        continue

                    detections_seen += 1

                    # --- PER-FREQUENCY THROTTLE ---
                    last = last_alert_by_freq.get(freq_hz, 0.0)
                    if now - last < self.alert_interval_s:
                        continue
                    last_alert_by_freq[freq_hz] = now
                    # --------------------------------

                    freq_mhz_int = int(round(freq_hz / 1e6))
                    uid = f"SCAN-{freq_mhz_int}MHz"

                    self.logger.info(
                        f"[TAK+ALERT] UID={uid} det={det_freq_hz/1e6:.3f} MHz RSSI={det_rssi_dbm} dBm"
                    )

                    try:
                        if self.tak_cot_callback:
                            ts = time.time()

                            detection = {
                                "event_type": "detection",
                                "frequency_hz": int(det_freq_hz),
                                "power_dbm": float(det_rssi_dbm),
                                "timestamp": ts,
                                "detector": "scan_detection",
                                "opid": self.opid,
                                "scan_frequency_hz": freq_hz,
                                "scan_frequency_mhz": round(freq_hz / 1e6, 3),
                                "retune_age_s": round(ts - last_retune, 3),
                            }

                            await self.tak_cot_callback({
                                "msg_type": "event",
                                "uid": f"scan-detection-{int(ts)}",
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
                                self.sensor_node_id,
                                self.opid,
                                f"Scan detection @ {det_freq_hz/1e6:.3f} MHz, RSSI {det_rssi_dbm} dBm",
                                self.logger,
                            )

                    except Exception as e:
                        self.logger.error(f"[SCAN] Error sending TAK/alert: {e}")

                self.logger.info(
                    f"[SCAN] Completed dwell @ {freq_mhz:.3f} MHz, detections_seen={detections_seen}"
                )

        finally:
            tb.stop()
            tb.wait()
            self.logger.info("[SCAN] Stopped.")