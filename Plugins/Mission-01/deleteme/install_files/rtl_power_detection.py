#!/usr/bin/env python3
"""
RTL-SDR Segmented Spectrum Detector (rtl_power) - FISSURE Plugin
"""

import asyncio
import sys
import time
import logging
import os
import statistics
from typing import Union, Callable, Dict, Any, Tuple

try:
    from fissure.utils.plugins.operations import Operation
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from fissure.utils.plugins.operations import Operation


# ============================================================
# PRESET SEGMENTS (locked options)
# ============================================================

ALLOWED_SEGMENT_RANGES_MHZ = {
    "24-300": (24e6, 300e6),
    "300-600": (300e6, 600e6),
    "600-900": (600e6, 900e6),
    "900-1200": (900e6, 1200e6),
    "1200-1500": (1200e6, 1500e6),
    "1500-1764": (1500e6, 1764e6),
}

STEP = 100e3
DWELL = 0.05

BASELINE_SWEEPS = 4
BASELINE_ALPHA = 0.1

MAX_ALERT_SIGNALS = 5

MAX_HOLD_WINDOW = 5.0


def tstamp():
    return time.strftime("%H:%M:%S.") + f"{int((time.time()%1)*1000):03d}"


def parse_rtl_power_csv(line: str):
    parts = line.strip().split(',')
    if len(parts) < 7:
        return None
    try:
        start = float(parts[2])
        step = float(parts[4])
        n = int(parts[5])
        bins = [float(x) for x in parts[6:6+n]]
        return start, step, bins
    except Exception:
        return None


def compute_hotspot_weights(baseline_sweeps):
    num_bins = len(baseline_sweeps[0])
    weights = [1.0] * num_bins

    medians = []
    stds = []
    maxvals = []

    for i in range(num_bins):
        col = [s[i] for s in baseline_sweeps]
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


def cluster_maxhold(max_vals, seg_start, step, threshold):
    clusters = []
    i = 0
    n = len(max_vals)

    while i < n:
        if max_vals[i] >= threshold:
            best_i = i
            best_val = max_vals[i]
            i += 1
            while i < n and max_vals[i] >= threshold:
                if max_vals[i] > best_val:
                    best_val = max_vals[i]
                    best_i = i
                i += 1
            freq = seg_start + best_i * step
            clusters.append((freq, best_val))
        else:
            i += 1

    return clusters


class OperationMain(Operation):

    def __init__(
        self,
        segment_range_mhz: str = "300-600",
        alert_interval_s: float = 5.0,
        detection_threshold_db: float = 8.0,
        description: str = "RTL-SDR rtl_power detection",
        sensor_node_id: Union[int, str] = 0,
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback: Callable = None,
        tak_cot_callback: Callable = None,
    ):
        super().__init__(
            sensor_node_id=sensor_node_id,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback
        )

        key = (segment_range_mhz or "").strip()
        if key not in ALLOWED_SEGMENT_RANGES_MHZ:
            raise ValueError(
                f"segment_range_mhz '{key}' invalid. "
                f"Valid: {', '.join(ALLOWED_SEGMENT_RANGES_MHZ.keys())}"
            )

        self.segment_range_mhz = key
        self.seg_start, self.seg_stop = ALLOWED_SEGMENT_RANGES_MHZ[key]

        self.alert_interval_s = float(alert_interval_s)
        self.detection_threshold_db = float(detection_threshold_db)
        self.description = description or "RTL-SDR rtl_power detection"

        self.logger.info(
            f"rtl_power_detection init params: segment_range_mhz={self.segment_range_mhz}, "
            f"alert_interval_s={self.alert_interval_s}, detection_threshold_db={self.detection_threshold_db}, "
            f"description={self.description}"
        )

    @staticmethod
    def get_resources() -> Dict[str, Any]:
        return {}

    async def run(self) -> None:
        self.logger.info(
            f"[RTL-POWER] Starting sweep segment {self.segment_range_mhz}: "
            f"{self.seg_start/1e6:.1f}–{self.seg_stop/1e6:.1f} MHz"
        )
        self.logger.info(
            f"[RTL-POWER] Baseline sweeps = {BASELINE_SWEEPS}, step={STEP/1e3:.0f} kHz, dwell={DWELL}s"
        )

        cmd = [
            "stdbuf", "-oL",
            "rtl_power",
            "-f", f"{int(self.seg_start)}:{int(self.seg_stop)}:{int(STEP)}",
            "-i", str(DWELL),
            "-"
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def drain_stderr():
            while True:
                line = await proc.stderr.readline()
                if not line:
                    return
                self.logger.debug("[RTL-POWER stderr] " + line.decode(errors="ignore").strip())

        stderr_task = asyncio.create_task(drain_stderr())

        blocks = []
        last_start = None
        sweeps_seen = 0

        baseline_ready = False
        baseline = None
        baseline_sweeps = []
        weights = None

        max_hold_vals = None
        max_hold_ts = None
        last_alert_time = time.time()

        try:
            while not self._stop:

                # Interruptible read so stop works even if rtl_power is silent
                try:
                    raw = await asyncio.wait_for(proc.stdout.readline(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue

                if not raw:
                    break

                parsed = parse_rtl_power_csv(raw.decode(errors="ignore"))
                if parsed is None:
                    continue

                start, step, bins = parsed

                # Detect sweep rollover
                if last_start is not None and start < last_start:

                    all_bins = []
                    for (_, b) in blocks:
                        all_bins.extend(b)
                    num_bins = len(all_bins)
                    now = time.time()

                    # ------------------------
                    # Baseline initialization
                    # ------------------------
                    if baseline is None:
                        baseline = all_bins.copy()
                        baseline_sweeps = [all_bins.copy()]
                        max_hold_vals = [float("-inf")] * num_bins
                        max_hold_ts = [0.0] * num_bins
                        sweeps_seen = 1
                        self.logger.info(
                            f"[RTL-POWER] Baseline warmup {sweeps_seen}/{BASELINE_SWEEPS}"
                        )

                    elif not baseline_ready:
                        sweeps_seen += 1
                        baseline_sweeps.append(all_bins.copy())

                        baseline = [max(b, s) for b, s in zip(baseline, all_bins)]

                        self.logger.info(
                            f"[RTL-POWER] Baseline warmup {sweeps_seen}/{BASELINE_SWEEPS}"
                        )

                        if sweeps_seen >= BASELINE_SWEEPS:
                            weights = compute_hotspot_weights(baseline_sweeps)
                            baseline_ready = True
                            self.logger.info("[RTL-POWER] Baseline ready.\n")

                    # ------------------------
                    # Detection mode
                    # ------------------------
                    else:
                        baseline = [
                            BASELINE_ALPHA * new + (1 - BASELINE_ALPHA) * b
                            for new, b in zip(all_bins, baseline)
                        ]

                        raw_delta = [new - b for new, b in zip(all_bins, baseline)]
                        weighted_delta = [d * w for d, w in zip(raw_delta, weights)]

                        # prune old max-hold values
                        for i in range(num_bins):
                            if now - max_hold_ts[i] > MAX_HOLD_WINDOW:
                                max_hold_vals[i] = float("-inf")
                                max_hold_ts[i] = 0.0

                        # update max-hold
                        for i, v in enumerate(weighted_delta):
                            if v > max_hold_vals[i]:
                                max_hold_vals[i] = v
                                max_hold_ts[i] = now

                        # Alert interval reached?
                        if now - last_alert_time >= self.alert_interval_s:

                            clusters = cluster_maxhold(
                                max_hold_vals,
                                seg_start=self.seg_start,
                                step=step,
                                threshold=self.detection_threshold_db,
                            )
                            clusters.sort(key=lambda x: x[1], reverse=True)
                            clusters = clusters[:MAX_ALERT_SIGNALS]

                            if clusters:
                                freqs = [round(f/1e6, 3) for f, _ in clusters]
                                deltas = [round(d, 1) for _, d in clusters]
                                await self._issue_alert(freqs, deltas)
                            else:
                                self.logger.info(f"[{tstamp()}][RTL-POWER] No signals above threshold")

                            # reset window
                            max_hold_vals = [float("-inf")] * num_bins
                            max_hold_ts = [0.0] * num_bins
                            last_alert_time = now

                    blocks = []

                blocks.append((start, bins))
                last_start = start
                await asyncio.sleep(0)

        finally:
            stderr_task.cancel()

            if proc.returncode is None:
                self.logger.info("[RTL-POWER] Terminating sweep...")
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.logger.warning("[RTL-POWER] Killing sweep...")
                    proc.kill()
                    await proc.wait()

            self.logger.info("[RTL-POWER] Sweep stopped.")

    async def _issue_alert(self, freqs_mhz, deltas_db):
        freq_str = ",".join(str(x) for x in freqs_mhz)
        delta_str = ",".join(str(x) for x in deltas_db)
        alert_text = f"RTL f:{freq_str} d:{delta_str}"

        if self.alert_callback:
            await self.alert_callback(
                self.sensor_node_id,
                self.opid,
                alert_text,
                self.logger
            )

        if self.tak_cot_callback and freqs_mhz:
            ts = time.time()
            detection = {
                "event_type": "detection",
                "description": self.description,
                "frequency_hz": int(freqs_mhz[0] * 1e6),
                "power_dbm": float(deltas_db[0]),
                "timestamp": ts,
                "detector": "rtl_power_detection",
                "opid": self.opid,
                "frequencies_mhz": freqs_mhz,
                "deltas_db": deltas_db,
                "segment_range_mhz": self.segment_range_mhz,
            }

            await self.tak_cot_callback({
                "msg_type": "event",
                "uid": f"rtl-detection-{int(ts)}",
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