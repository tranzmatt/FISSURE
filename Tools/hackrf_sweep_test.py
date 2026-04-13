#!/usr/bin/env python3
import subprocess, sys, time, statistics

# =====================================================
# BAND PRESETS
# =====================================================
BAND_PRESETS = {
    0: (1e6, 300e6),
    1: (300e6, 600e6),
    2: (600e6, 900e6),
    3: (900e6, 1500e6),
    4: (1500e6, 2000e6),
    5: (2000e6, 2600e6),
    6: (2600e6, 3000e6),
}

try:
    BAND = int(sys.argv[1])
except:
    BAND = 1

if BAND not in BAND_PRESETS:
    print(f"[ERROR] Band {BAND} undefined")
    sys.exit(1)

F_START, F_STOP = BAND_PRESETS[BAND]

# =====================================================
# CONFIG
# =====================================================
BIN_WIDTH = 200e3
BASELINE_SWEEPS = 30
DETECTION_THRESHOLD = 12.0
WARMUP_SWEEPS = 5

# alert settings
ALERT_INTERVAL = 5
MAX_ALERT_SIGNALS = 5
window_detections = []
last_alert_time = time.time()

def timestamp():
    return time.strftime("%H:%M:%S.") + f"{int((time.time()%1)*1000):03d}"

# =====================================================
# Helpers
# =====================================================
def parse_sweep_line(line):
    parts = line.split(',')
    if len(parts) < 6:
        return None
    try:
        f_start = float(parts[2])
        f_end = float(parts[3])
        n = int(parts[5])
        bins = [float(x) for x in parts[6:6+n]]
        return f_start, f_end, bins
    except:
        return None

def compute_hotspot_weights(baseline):
    num_bins = len(baseline[0])
    weights = [1.0] * num_bins
    medians = []
    stds    = []
    maxvals = []

    for i in range(num_bins):
        col = [s[i] for s in baseline]
        med = statistics.median(col)
        std = statistics.pstdev(col)
        mx  = max(col)
        medians.append(med)
        stds.append(std)
        maxvals.append(mx)

    overall_med = statistics.median(medians)
    overall_std = statistics.pstdev(medians) if len(medians) > 1 else 0

    for i in range(num_bins):
        if medians[i] > overall_med + 2*overall_std:
            weights[i] = 0.25
        if stds[i] > 8.0:
            weights[i] = min(weights[i], 0.4)
        if maxvals[i] > overall_med + 20:
            weights[i] = 0.15

    return weights

# =====================================================
# MAIN
# =====================================================
print(f"\n=== ALERT MODE ===")
print(f"Band {BAND}: {F_START/1e6:.1f}-{F_STOP/1e6:.1f} MHz\n")

cmd = [
    "stdbuf","-oL",
    "hackrf_sweep",
    "-f", f"{int(F_START/1e6)}:{int(F_STOP/1e6)}",
    "-w", str(int(BIN_WIDTH))
]

proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
blocks = {}

try:
    for raw in proc.stdout:
        line = raw.strip()
        if not line:
            continue

        parsed = parse_sweep_line(line)
        if parsed is None:
            continue

        f_start, f_end, bins = parsed

        # new block
        if f_start not in blocks:
            blocks[f_start] = {
                "baseline_sweeps": [],
                "baseline": None,
                "weights": None,
                "ready": False,
                "warmup": 0,
            }

        blk = blocks[f_start]

        # warmup
        if blk["warmup"] < WARMUP_SWEEPS:
            blk["warmup"] += 1
            continue

        # baseline building
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

        # detection
        weighted = [
            (s - b) * w
            for s, b, w in zip(bins, blk["baseline"], blk["weights"])
        ]

        max_delta = max(weighted)
        idx = weighted.index(max_delta)
        freq = f_start + idx * BIN_WIDTH

        if max_delta >= DETECTION_THRESHOLD:
            window_detections.append((freq, max_delta))

        # ALERT TIME?
        now = time.time()
        if now - last_alert_time >= ALERT_INTERVAL:

            if window_detections:
                window_detections.sort(key=lambda x: x[1], reverse=True)
                strongest = window_detections[:MAX_ALERT_SIGNALS]

                freqs = ",".join(str(int(f/1e6)) for f, d in strongest)
                deltas = ",".join(str(int(d)) for f, d in strongest)

                print(f"{timestamp()}  [ALERT] f:{freqs} d:{deltas}")

            window_detections.clear()
            last_alert_time = now

except KeyboardInterrupt:
    print("[STOP] Ctrl+C – terminating.")
    proc.terminate()
    proc.wait()
