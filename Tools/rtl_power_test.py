#!/usr/bin/env python3
"""
RTL-SDR Segmented Spectrum Detector with Baseline + Max-Hold

Cleaner console output version.
"""

import asyncio
import subprocess
import sys
import time
import statistics


# ============================================================
# SEGMENT CONFIGURATION
# ============================================================

SEGMENTS = [
    (24e6,   300e6),
    (300e6,  600e6),
    (600e6,  900e6),
    (900e6,  1200e6),
    (1200e6, 1500e6),
    (1500e6, 1764e6),
]

STEP = 100e3          # 100 kHz bins
DWELL = 0.05          # rtl_power integration time (sec)

BASELINE_SWEEPS = 4   # sweeps to build baseline
BASELINE_ALPHA = 0.1  # EMA factor
DETECTION_THRESHOLD = 8.0
MAX_ALERT_SIGNALS = 5

MAX_HOLD_WINDOW = 5.0
ALERT_INTERVAL = 5.0


# ============================================================
# UTILITIES
# ============================================================

def timestamp():
    return time.strftime("%H:%M:%S.") + f"{int((time.time()%1)*1000):03d}"

def parse_rtl_power_csv(line: str):
    parts = line.strip().split(',')
    if len(parts) < 7:
        return None
    try:
        start = float(parts[2])
        end   = float(parts[3])
        step  = float(parts[4])
        n     = int(parts[5])
        bins  = [float(x) for x in parts[6:6+n]]
        return start, end, step, bins
    except Exception:
        return None


# ============================================================
# HOTSPOT WEIGHTING
# ============================================================

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
    overall_std = statistics.pstdev(medians) if len(medians) > 1 else 0.0

    for i in range(num_bins):
        if medians[i] > overall_med + 2 * overall_std:
            weights[i] = 0.25
        if stds[i] > 8.0:
            weights[i] = min(weights[i], 0.4)
        if maxvals[i] > overall_med + 20:
            weights[i] = 0.15

    return weights


# ============================================================
# CLUSTERING
# ============================================================

def find_clusters_maxhold(max_hold_vals, seg_start, step, threshold):
    clusters = []
    i = 0
    n = len(max_hold_vals)

    while i < n:
        if max_hold_vals[i] >= threshold:
            start_idx = i
            best_idx = i
            best_val = max_hold_vals[i]
            i += 1
            while i < n and max_hold_vals[i] >= threshold:
                if max_hold_vals[i] > best_val:
                    best_val = max_hold_vals[i]
                    best_idx = i
                i += 1
            freq_hz = seg_start + best_idx * step
            clusters.append((freq_hz, best_val))
        else:
            i += 1

    return clusters


# ============================================================
# MAIN SEGMENT RUNNER
# ============================================================

async def run_segment(seg_start, seg_stop):
    print(f"\n[RTL] Starting segmented detector")
    print(f"[RTL] Segment: {seg_start/1e6:.1f}–{seg_stop/1e6:.1f} MHz")
    print(f"[RTL] Baseline will be built over {BASELINE_SWEEPS} sweeps...\n")

    cmd = [
        "stdbuf", "-oL",
        "rtl_power",
        "-f", f"{int(seg_start)}:{int(seg_stop)}:{int(STEP)}",
        "-i", str(DWELL),
        "-"
    ]

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    blocks = []
    last_start = None

    baseline = None
    baseline_sweeps = []
    sweeps_seen = 0
    baseline_ready = False
    weights = None

    max_hold_vals = None
    max_hold_ts = None

    last_alert_time = time.time()

    try:
        while True:
            line = proc.stdout.readline()
            if not line:
                await asyncio.sleep(0.01)
                continue

            parsed = parse_rtl_power_csv(line)
            if not parsed:
                continue

            start, end, step, bins = parsed

            # Detect new sweep
            if last_start is not None and start < last_start:

                # Sweep complete: flatten bins
                all_bins = []
                starts = []
                for (s, b) in blocks:
                    starts.append(s)
                    all_bins.extend(b)
                num_bins = len(all_bins)

                now = time.time()

                # ----------------------------
                # Baseline building
                # ----------------------------
                if baseline is None:
                    baseline = all_bins.copy()
                    baseline_sweeps = [all_bins.copy()]
                    sweeps_seen = 1
                    print(f"[RTL] Baseline warmup {sweeps_seen}/{BASELINE_SWEEPS}")
                    max_hold_vals = [float("-inf")] * num_bins
                    max_hold_ts = [0.0] * num_bins

                elif not baseline_ready:
                    sweeps_seen += 1
                    baseline_sweeps.append(all_bins.copy())
                    baseline = [
                        max(b0, b1) for b0, b1 in zip(baseline, all_bins)
                    ]
                    print(f"[RTL] Baseline warmup {sweeps_seen}/{BASELINE_SWEEPS}")

                    if sweeps_seen >= BASELINE_SWEEPS:
                        baseline_ready = True
                        weights = compute_hotspot_weights(baseline_sweeps)
                        print("[RTL] Baseline ready.\n")

                # ----------------------------
                # Main detection mode
                # ----------------------------
                else:
                    # Baseline EMA
                    baseline = [
                        BASELINE_ALPHA * new + (1 - BASELINE_ALPHA) * b
                        for new, b in zip(all_bins, baseline)
                    ]

                    raw_delta = [
                        new - b for new, b in zip(all_bins, baseline)
                    ]

                    weighted_delta = [
                        d * w for d, w in zip(raw_delta, weights)
                    ]

                    # Prune old max-hold
                    for i in range(num_bins):
                        if now - max_hold_ts[i] > MAX_HOLD_WINDOW:
                            max_hold_vals[i] = float("-inf")
                            max_hold_ts[i] = 0.0

                    # Update max-hold
                    for i, val in enumerate(weighted_delta):
                        if val > max_hold_vals[i]:
                            max_hold_vals[i] = val
                            max_hold_ts[i] = now

                    # -------------------------------------
                    # Issue alert every ALERT_INTERVAL
                    # -------------------------------------
                    if now - last_alert_time >= ALERT_INTERVAL:
                        clusters = find_clusters_maxhold(
                            max_hold_vals,
                            seg_start=start,   # use actual sweep start
                            step=step,
                            threshold=DETECTION_THRESHOLD,
                        )
                        clusters.sort(key=lambda x: x[1], reverse=True)
                        clusters = clusters[:MAX_ALERT_SIGNALS]

                        if clusters:
                            print(f"[{timestamp()}][RTL][ALERT] Strongest signals:")
                            for f_hz, d_db in clusters:
                                print(f"    {f_hz/1e6:8.3f} MHz   Δ={d_db:5.1f} dB")
                        else:
                            print(f"[{timestamp()}][RTL][ALERT] No signals above threshold")

                        # Reset window
                        max_hold_vals = [float("-inf")] * num_bins
                        max_hold_ts = [0.0] * num_bins
                        last_alert_time = now

                blocks = []

            blocks.append((start, bins))
            last_start = start
            await asyncio.sleep(0)

    except KeyboardInterrupt:
        print("\n[RTL] Stopping segment...")
    finally:
        proc.terminate()
        proc.wait()
        print("[RTL] rtl_power stopped.\n")


# ============================================================
# ENTRY POINT
# ============================================================

async def main():
    if len(sys.argv) < 2:
        seg_id = 1
        print("[INFO] Using default segment 1 (300–600 MHz)")
    else:
        seg_id = int(sys.argv[1])

    if not (0 <= seg_id < len(SEGMENTS)):
        print("Invalid segment ID.\nAvailable segments:")
        for i, (s, e) in enumerate(SEGMENTS):
            print(f"  {i}: {s/1e6:.1f}–{e/1e6:.1f} MHz")
        sys.exit(1)

    seg_start, seg_stop = SEGMENTS[seg_id]
    await run_segment(seg_start, seg_stop)


if __name__ == "__main__":
    asyncio.run(main())
