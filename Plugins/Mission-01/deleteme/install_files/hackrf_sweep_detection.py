#!/usr/bin/env python3
"""
HackRF Sweep - FISSURE Plugin
Produces periodic alerts with strongest signals observed in a band.

Updated:
- Replaced numeric band (0-6) with restricted string band_range_mhz (e.g. "300-600")
- Added injected params: band_range_mhz, alert_interval_s, detection_threshold_db, description
- Uses per-instance (self.*) values instead of module globals for alert interval / threshold
"""

import asyncio
import sys
import time
import json
import logging
import os
import statistics
from typing import Union, Callable, Dict, Any, Optional

try:
    from fissure.utils.plugins.operations import Operation
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
    from fissure.utils.plugins.operations import Operation


# ============================================================
# CONFIGURATION (fixed, known-good bands only)
# ============================================================

ALLOWED_BAND_RANGES_MHZ = {
    "1-300": (1e6, 300e6),
    "300-600": (300e6, 600e6),
    "600-900": (600e6, 900e6),
    "900-1500": (900e6, 1500e6),
    "1500-2000": (1500e6, 2000e6),
    "2000-2600": (2000e6, 2600e6),
    "2600-3000": (2600e6, 3000e6),
}

BIN_WIDTH = 200e3
BASELINE_SWEEPS = 30
WARMUP_SWEEPS = 5
MAX_ALERT_SIGNALS = 5


def parse_sweep_line(line: str):
    parts = line.split(',')
    if len(parts) < 6:
        return None
    try:
        f_start = float(parts[2])
        f_end = float(parts[3])
        n = int(parts[5])
        bins = [float(x) for x in parts[6:6 + n]]
        return f_start, f_end, bins
    except Exception:
        return None


def compute_hotspot_weights(baseline):
    num_bins = len(baseline[0])
    weights = [1.0] * num_bins

    medians = []
    stds = []
    maxvals = []

    for i in range(num_bins):
        col = [s[i] for s in baseline]
        med = statistics.median(col)
        std = statistics.pstdev(col)
        mx = max(col)
        medians.append(med)
        stds.append(std)
        maxvals.append(mx)

    overall_med = statistics.median(medians)
    overall_std = statistics.pstdev(medians) if len(medians) > 1 else 0

    for i in range(num_bins):
        if medians[i] > overall_med + 2 * overall_std:
            weights[i] = 0.25
        if stds[i] > 8.0:
            weights[i] = min(weights[i], 0.4)
        if maxvals[i] > overall_med + 20:
            weights[i] = 0.15

    return weights


# ============================================================
# OPERATION
# ============================================================

class OperationMain(Operation):

    def __init__(
        self,
        band_range_mhz: str = "300-600",
        alert_interval_s: float = 5.0,
        detection_threshold_db: float = 12.0,
        description: str = "HackRF sweep detection",
        sensor_node_id: Union[int, str] = 0,
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback: Optional[Callable] = None,
        tak_cot_callback: Optional[Callable] = None,
    ):
        super().__init__(
            sensor_node_id=sensor_node_id,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback
        )

        key = (band_range_mhz or "").strip()
        if key not in ALLOWED_BAND_RANGES_MHZ:
            allowed = ", ".join(ALLOWED_BAND_RANGES_MHZ.keys())
            raise ValueError(f"Invalid band_range_mhz='{key}'. Allowed: {allowed}")

        self.band_range_mhz = key
        self.F_START, self.F_STOP = ALLOWED_BAND_RANGES_MHZ[key]

        self.alert_interval_s = float(alert_interval_s)
        self.detection_threshold_db = float(detection_threshold_db)
        self.description = description or "HackRF sweep detection"

        self.blocks: Dict[float, Dict[str, Any]] = {}
        self.window_detections = []
        self.last_alert_time = time.time()

        self.logger.info(
            f"[HACKRF] init params: band_range_mhz={self.band_range_mhz}, "
            f"start={self.F_START/1e6:.1f} MHz, stop={self.F_STOP/1e6:.1f} MHz, "
            f"alert_interval_s={self.alert_interval_s}, "
            f"detection_threshold_db={self.detection_threshold_db}, "
            f"description={self.description}"
        )

    @staticmethod
    def get_resources() -> Dict[str, Any]:
        return {}

    async def run(self) -> None:

        self.logger.info(
            f"[HACKRF] Starting sweep band={self.band_range_mhz} "
            f"{self.F_START/1e6:.1f}-{self.F_STOP/1e6:.1f} MHz"
        )

        cmd = [
            "stdbuf", "-oL",
            "hackrf_sweep",
            "-f", f"{int(self.F_START/1e6)}:{int(self.F_STOP/1e6)}",
            "-w", str(int(BIN_WIDTH)),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def drain_stderr():
            while True:
                try:
                    line = await proc.stderr.readline()
                except Exception:
                    return
                if not line:
                    return
                self.logger.debug("[HACKRF stderr] " + line.decode(errors="ignore").strip())

        stderr_task = asyncio.create_task(drain_stderr())

        try:
            while not self._stop:

                # Interruptible read
                try:
                    raw = await asyncio.wait_for(proc.stdout.readline(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue

                if not raw:
                    break

                parsed = parse_sweep_line(raw.decode(errors="ignore").strip())
                if parsed is None:
                    continue

                f_start, f_end, bins = parsed

                if f_start not in self.blocks:
                    self.blocks[f_start] = {
                        "baseline_sweeps": [],
                        "baseline": None,
                        "weights": None,
                        "ready": False,
                        "warmup": 0,
                    }

                blk = self.blocks[f_start]

                if blk["warmup"] < WARMUP_SWEEPS:
                    blk["warmup"] += 1
                    continue

                if not blk["ready"]:
                    blk["baseline_sweeps"].append(bins)
                    if blk["baseline"] is None:
                        blk["baseline"] = bins.copy()
                    else:
                        blk["baseline"] = [
                            max(b, s) for b, s in zip(blk["baseline"], bins)
                        ]
                    if len(blk["baseline_sweeps"]) >= BASELINE_SWEEPS:
                        blk["weights"] = compute_hotspot_weights(blk["baseline_sweeps"])
                        blk["ready"] = True
                    continue

                weighted = [
                    (s - b) * w
                    for s, b, w in zip(bins, blk["baseline"], blk["weights"])
                ]

                max_delta = max(weighted)
                idx = weighted.index(max_delta)
                freq = f_start + idx * BIN_WIDTH

                if max_delta >= self.detection_threshold_db:
                    self.window_detections.append((freq, max_delta))

                now = time.time()
                if now - self.last_alert_time >= self.alert_interval_s:

                    if self.window_detections:
                        self.window_detections.sort(key=lambda x: x[1], reverse=True)
                        strongest = self.window_detections[:MAX_ALERT_SIGNALS]
                        freqs = [int(f / 1e6) for f, d in strongest]
                        deltas = [int(d) for f, d in strongest]
                        await self._issue_alert(freqs, deltas)

                    self.window_detections.clear()
                    self.last_alert_time = now

        finally:

            stderr_task.cancel()

            if proc.returncode is None:
                self.logger.info("[HACKRF] Terminating sweep...")
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.logger.warning("[HACKRF] Killing sweep...")
                    proc.kill()
                    await proc.wait()

            self.logger.info("[HACKRF] Sweep stopped.")

    async def _issue_alert(self, freqs, deltas):

        freqs_str = ",".join(str(x) for x in freqs)
        deltas_str = ",".join(str(x) for x in deltas)

        alert_text = f"HackRF sweep f:{freqs_str} d:{deltas_str}"

        if self.alert_callback:
            await self.alert_callback(
                self.sensor_node_id,
                self.opid,
                alert_text,
                self.logger
            )

        if self.tak_cot_callback and freqs:
            ts = time.time()
            detection = {
                "event_type": "detection",
                # NOTE: this is a coarse MHz integer; fine resolution is in the sweep binning
                "frequency_hz": int(freqs[0] * 1e6),
                # NOTE: this is a delta/score, not calibrated power
                "power_dbm": float(deltas[0]),
                "timestamp": ts,
                "detector": "hackrf_sweep_detection",
                "opid": self.opid,
                "frequencies_mhz": freqs,
                "deltas_db": deltas,
                "band_range_mhz": self.band_range_mhz,
            }

            await self.tak_cot_callback({
                "msg_type": "event",
                "uid": f"hackrf-detection-{int(ts)}",
                "lat": True,
                "lon": True,
                "alt": True,
                "time": True,
                "data": detection,
                "opid": self.opid,
                "tak_icon": "r-x-fissure-detection"
            })


if __name__ == "__main__":
    from fissure.utils.plugins.test_operation import run_test
    run_test(OperationMain, {}, {})