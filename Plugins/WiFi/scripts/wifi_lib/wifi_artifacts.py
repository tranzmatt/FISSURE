#!/usr/bin/env python3
"""
FISSURE – Dual-Band Passive Wi-Fi Geolocation (Artifact Logging, No Rings/Lines)
--------------------------------------------------------------------------------
✓ airodump-ng passive capture (2.4 + 5 GHz via --band abg)
✓ Continuous CSV parsing (~0.5 s)
✓ LSQ multilateration with outlier rejection
✓ Requires movement + RSSI variation for valid solve
✓ Strongest-point fallback (NEVER snaps AP to drone)
✓ AP markers use existing stale timing (not permanent)
✓ Logs artifacts to:
  - artifacts/data_source.csv
  - artifacts/processing_metrics.csv
  - artifacts/outputs_sent.csv
"""

import os, csv, glob, atexit, time, math, json, subprocess, threading, logging
import socket, ssl
import numpy as np
import xml.etree.ElementTree as ET
import pytak

# ---------------- CONFIG ----------------
WIFI_INTERFACE = "wlx00c0cab6704d"
MON_SUFFIX     = "mon"

AIRO_PREFIX    = "/tmp/airodump"
AIRO_CSV_GLOB  = AIRO_PREFIX + "-*.csv"

GPSD_HOST, GPSD_PORT  = "127.0.0.1", 2947
GPS_REFRESH_INTERVAL   = 3.0
WIFI_REFRESH_INTERVAL  = 0.5

SMOOTH_ALPHA           = 0.25
MIN_SAMPLES_FOR_SOLVE  = 4
MIN_SPREAD_METERS      = 20.0
MIN_RSSI_STD_DB        = 4.0

# TAK
TAKSERVER_HOST, TAKSERVER_PORT = "192.168.0.118", 8089
CERT_FILE = "/home/ais/Installed_by_FISSURE/takserver-docker-5.3-RELEASE-24/tak/certs/files/takserver.pem"
KEY_FILE  = "/home/ais/Installed_by_FISSURE/takserver-docker-5.3-RELEASE-24/tak/certs/files/takserver.key"
CA_FILE   = CERT_FILE

DRONE_CALLSIGN = "DF-DRONE"
DRONE_UID      = "DF-DRONE"

# RF model
P_TX_REF      = -45.0
N_MIN, N_MAX  = 2.0, 4.0
MAX_RANGE_M   = 200.0
MIN_UNC_M     = 10.0
MAX_UNC_M     = MAX_RANGE_M

# Artifact logging
ARTIFACT_DIR        = "artifacts"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

DATA_SOURCE_FILE    = os.path.join(ARTIFACT_DIR, "data_source.csv")
PROCESSING_FILE     = os.path.join(ARTIFACT_DIR, "processing_metrics.csv")
OUTPUT_FILE         = os.path.join(ARTIFACT_DIR, "outputs_sent.csv")

# Create CSV headers if missing
if not os.path.exists(DATA_SOURCE_FILE):
    with open(DATA_SOURCE_FILE, "w", newline="") as f:
        csv.writer(f).writerow(
            ["timestamp", "ssid", "bssid", "rssi", "gps_lat", "gps_lon"]
        )

if not os.path.exists(PROCESSING_FILE):
    with open(PROCESSING_FILE, "w", newline="") as f:
        csv.writer(f).writerow(
            ["timestamp", "ssid", "num_samples", "spread_m", "rssi_std_db",
             "uncertainty_m", "n_est"]
        )

if not os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, "w", newline="") as f:
        csv.writer(f).writerow(
            ["timestamp", "cot_type", "ssid_or_uid", "lat", "lon", "uncertainty_m"]
        )

# ---------------- LOGGING ----------------
logging.basicConfig(
    filename="fissure_df_dualband_artifacts.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("fissure")
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)

# ---------------- GLOBAL STATE ----------------
current_position = {"lat": None, "lon": None, "alt": 0.0}
tak_sock = None
airodump_proc = None

# ---------------- ARTIFACT HELPERS ----------------
def log_data_source(ssid, bssid, rssi, lat, lon):
    """Log every raw Wi-Fi + GPS sample."""
    if lat is None or lon is None:
        return
    with open(DATA_SOURCE_FILE, "a", newline="") as f:
        csv.writer(f).writerow([time.time(), ssid, bssid, rssi, lat, lon])

def log_processing(ssid, num_samples, spread_m, rssi_std, unc_m, n_est):
    """Log processing metrics for each AP LSQ attempt."""
    with open(PROCESSING_FILE, "a", newline="") as f:
        csv.writer(f).writerow([
            time.time(),
            ssid,
            num_samples,
            spread_m,
            rssi_std,
            unc_m if unc_m is not None else "",
            n_est if n_est is not None else "",
        ])

def log_output(cot_type, ssid_or_uid, lat, lon, unc_m):
    """Log every CoT pushed to TAK."""
    with open(OUTPUT_FILE, "a", newline="") as f:
        csv.writer(f).writerow([
            time.time(),
            cot_type,
            ssid_or_uid,
            lat if lat is not None else "",
            lon if lon is not None else "",
            unc_m if unc_m is not None else "",
        ])

# ---------------- TAK HELPERS ----------------
def connect_tak():
    global tak_sock
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=CA_FILE)
            ctx.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_REQUIRED
            conn = ctx.wrap_socket(s, server_hostname=TAKSERVER_HOST)
            conn.connect((TAKSERVER_HOST, TAKSERVER_PORT))
            tak_sock = conn
            logger.info("✅ Connected to TAKServer (TLS)")
            return
        except Exception as e:
            logger.warning(f"TAK connect failed: {e}; retrying…")
            time.sleep(4)

def send_tak(xml_bytes):
    """Low-level send with auto-reconnect."""
    global tak_sock
    if tak_sock is None:
        connect_tak()
    try:
        tak_sock.sendall(xml_bytes)
    except Exception:
        connect_tak()
        tak_sock.sendall(xml_bytes)

# ---------- CoT builders ----------
def make_drone_cot(lat, lon, alt, remark="Drone Position"):
    """Drone marker (keep existing stale timing: ~6s)."""
    if not hasattr(make_drone_cot, "session_start"):
        make_drone_cot.session_start = pytak.cot_time()

    root = ET.Element("event", {
        "version": "2.0",
        "type": "a-f-A",
        "uid": DRONE_UID,
        "how": "h-g-i-g-o",
        "time": pytak.cot_time(),
        "start": make_drone_cot.session_start,
        "stale": pytak.cot_time(6),     # keep original drone stale timing
    })
    detail = ET.SubElement(root, "detail")
    ET.SubElement(detail, "remarks").text = remark
    ET.SubElement(detail, "contact").set("callsign", DRONE_CALLSIGN)
    ET.SubElement(root, "point", {
        "lat": f"{lat:.8f}",
        "lon": f"{lon:.8f}",
        "hae": f"{alt:.1f}",
        "ce": "10.0",
        "le": "10.0",
    })
    return ET.tostring(root, encoding="utf-8")

def make_ap_cot(uid, callsign, lat, lon, remark, stale_seconds=20):
    """AP marker (keep existing AP stale timing, e.g., 20s)."""
    if not hasattr(make_ap_cot, "session_start"):
        make_ap_cot.session_start = pytak.cot_time()

    root = ET.Element("event", {
        "version": "2.0",
        "type": "a-f-G",
        "uid": uid,
        "how": "h-g-i-g-o",
        "time": pytak.cot_time(),
        "start": make_ap_cot.session_start,
        "stale": pytak.cot_time(stale_seconds),
    })
    detail = ET.SubElement(root, "detail")
    ET.SubElement(detail, "remarks").text = remark
    ET.SubElement(detail, "contact").set("callsign", callsign)
    ET.SubElement(root, "point", {
        "lat": f"{lat:.8f}",
        "lon": f"{lon:.8f}",
        "hae": "0.0",
        "ce": "10.0",
        "le": "10.0",
    })
    return ET.tostring(root, encoding="utf-8")

# ---------------- GEOMETRY ----------------
def latlon_to_xy(lat, lon, lat0, lon0):
    R = 6371000.0
    lat_r, lon_r, lat0_r, lon0_r = map(math.radians, (lat, lon, lat0, lon0))
    x = (lon_r - lon0_r) * math.cos((lat_r + lat0_r) / 2.0) * R
    y = (lat_r - lat0_r) * R
    return x, y

def xy_to_latlon(x, y, lat0, lon0):
    R = 6371000.0
    lat0_r, lon0_r = map(math.radians, (lat0, lon0))
    lat_r = y / R + lat0_r
    lon_r = x / (R * math.cos((lat_r + lat0_r) / 2.0)) + lon0_r
    return math.degrees(lat_r), math.degrees(lon_r)

def adaptive_n(samples):
    """Estimate path-loss exponent n from samples."""
    if len(samples) < 3:
        return 3.0
    lat0, lon0 = samples[0][0], samples[0][1]
    dists = []
    rssis = []
    for lat, lon, rssi in samples:
        x, y = latlon_to_xy(lat, lon, lat0, lon0)
        dists.append(math.hypot(x, y) + 1e-6)
        rssis.append(rssi)
    dists = np.array(dists)
    rssis = np.array(rssis)
    try:
        m = np.polyfit(np.log10(dists), (P_TX_REF - rssis) / 10.0, 1)[0]
        return float(np.clip(m, N_MIN, N_MAX))
    except Exception:
        return 3.0

def estimate_distance(rssi, n):
    """RSSI -> distance (m), capped."""
    d = 10 ** ((P_TX_REF - rssi) / (10.0 * n))
    return float(np.clip(d, 1.0, MAX_RANGE_M))

def multilaterate(samples):
    """
    Returns:
      (est_lat, est_lon, unc_m, spread_m, rssi_std, n_est)
    or:
      (None, None, None, spread_m, rssi_std, None)
    """
    num = len(samples)
    if num == 0:
        return None, None, None, 0.0, 0.0, None

    lats = np.array([s[0] for s in samples])
    lons = np.array([s[1] for s in samples])
    rssis = np.array([s[2] for s in samples])

    lat0 = float(np.mean(lats))
    lon0 = float(np.mean(lons))

    xs, ys = [], []
    for lt, ln in zip(lats, lons):
        x, y = latlon_to_xy(lt, ln, lat0, lon0)
        xs.append(x)
        ys.append(y)
    xs = np.array(xs)
    ys = np.array(ys)

    if len(xs) > 1:
        spread = float(np.max(np.hypot(xs - np.mean(xs), ys - np.mean(ys))))
    else:
        spread = 0.0
    rssi_std = float(np.std(rssis)) if len(rssis) > 1 else 0.0

    if num < MIN_SAMPLES_FOR_SOLVE or spread < MIN_SPREAD_METERS or rssi_std < MIN_RSSI_STD_DB:
        # Not enough geometry or variation -> return metrics but no solution
        return None, None, None, spread, rssi_std, None

    # Robust LSQ
    n_est = adaptive_n(samples)
    rs = np.array([estimate_distance(r, n_est) for r in rssis])

    # RSSI outlier rejection
    med = float(np.median(rssis))
    mask = np.abs(rssis - med) < 8.0
    if not np.any(mask):
        strongest = np.argsort(rssis)[-3:]
        mask = np.isin(np.arange(len(rssis)), strongest)

    xs = xs[mask]
    ys = ys[mask]
    rs = rs[mask]
    if len(xs) < 3:
        return None, None, None, spread, rssi_std, n_est

    w = 1.0 / np.clip(rs, 1.0, MAX_RANGE_M) ** 2
    x = float(np.average(xs, weights=w))
    y = float(np.average(ys, weights=w))

    for _ in range(15):
        d = np.hypot(x - xs, y - ys) + 1e-9
        J = np.column_stack(((x - xs) / d, (y - ys) / d))
        r = d - rs
        W = np.diag(w)
        try:
            delta, *_ = np.linalg.lstsq(J.T @ W @ J, -J.T @ W @ r, rcond=None)
        except np.linalg.LinAlgError:
            break
        x += float(delta[0])
        y += float(delta[1])
        if np.linalg.norm(delta) < 0.4:
            break

    # Uncertainty from residuals
    d_est = np.hypot(x - xs, y - ys)
    res = d_est - rs
    if len(res) > 0:
        unc_m = float(np.clip(np.sqrt(np.mean(res**2)), MIN_UNC_M, MAX_UNC_M))
    else:
        unc_m = MAX_UNC_M

    est_lat, est_lon = xy_to_latlon(x, y, lat0, lon0)
    return est_lat, est_lon, unc_m, spread, rssi_std, n_est

# ---------------- GPS LOOP ----------------
def gps_loop():
    logger.info("Starting GPS loop")
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10.0)
            s.connect((GPSD_HOST, GPSD_PORT))
            logger.info(f"Connected to GPSD at {GPSD_HOST}:{GPSD_PORT}")
            s.settimeout(None)
            s.sendall(b'?WATCH={"enable":true,"json":true}\n')
            buf = ""
            last = 0
            while True:
                data = s.recv(4096).decode(errors="ignore")
                if not data:
                    logger.warning("GPSD connection closed")
                    break
                buf += data
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line)
                    except Exception as e:
                        logger.debug(f"Failed to parse GPSD JSON: {e}")
                        continue
                    logger.debug(f"GPSD message: {msg.get('class', 'unknown')}")
                    if msg.get("class") == "TPV" and msg.get("mode", 0) >= 2:
                        lat = msg.get("lat")
                        lon = msg.get("lon")
                        alt = msg.get("altMSL") or msg.get("altHAE") or 0.0
                        if lat is None or lon is None:
                            logger.warning("Invalid GPS fix received")
                            continue
                        current_position.update({"lat": lat, "lon": lon, "alt": alt})
                        now = time.time()
                        if now - last > GPS_REFRESH_INTERVAL:
                            xml = make_drone_cot(lat, lon, alt)
                            send_tak(xml)
                            log_output("a-f-A", DRONE_UID, lat, lon, None)
                            logger.info(f"Drone pos: {lat:.6f},{lon:.6f}")
                            last = now
        except Exception as e:
            logger.warning(f"GPS error: {e}")
            time.sleep(2)

# ---------------- AIRODUMP CONTROL ----------------
def restore_managed():
    try:
        subprocess.run(["sudo", "ip", "link", "set", WIFI_INTERFACE, "down"])
        subprocess.run(["sudo", "iw", "dev", WIFI_INTERFACE, "set", "type", "managed"])
        subprocess.run(["sudo", "ip", "link", "set", WIFI_INTERFACE, "up"])
        logger.info(f"Restored {WIFI_INTERFACE} to managed mode")
    except Exception as e:
        logger.warning(f"Restore managed failed: {e}")

atexit.register(restore_managed)

def start_airodump():
    mon = WIFI_INTERFACE + MON_SUFFIX
    subprocess.run(["sudo", "iw", "dev", mon, "del"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    add = subprocess.run(
        ["sudo", "iw", "dev", WIFI_INTERFACE, "interface", "add", mon, "type", "monitor"],
        capture_output=True, text=True
    )

    if add.returncode == 0:
        subprocess.run(["sudo", "ip", "link", "set", mon, "up"])
        iface = mon
    else:
        logger.warning(f"Monitor sub-iface add failed: {add.stderr.strip()}. Falling back to converting main iface.")
        proc = subprocess.run(["sudo", "ip", "link", "set", WIFI_INTERFACE, "down"])
        if proc.returncode != 0:
            logger.error(f"Failed to bring down {WIFI_INTERFACE}")
        proc = subprocess.run(["sudo", "iw", "dev", WIFI_INTERFACE, "set", "type", "monitor"])
        if proc.returncode != 0:
            logger.error(f"Failed to set {WIFI_INTERFACE} to monitor mode")
        proc = subprocess.run(["sudo", "ip", "link", "set", WIFI_INTERFACE, "up"])
        if proc.returncode != 0:
            logger.error(f"Failed to bring up {WIFI_INTERFACE}")
        iface = WIFI_INTERFACE

    cmd = [
        "sudo",
        "airodump-ng",
        "--berlin", "1",
        "--write-interval", "1",
        "--band", "abg",           # dual-band
        "--output-format", "csv",
        "--write", AIRO_PREFIX,
        iface
    ]
    logger.info(f"📡 Launching airodump-ng on {iface}")
    logger.info(f"    Command: {' '.join(cmd)}")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        time.sleep(2)
        if proc.poll() is not None:
            logger.error("Airodump failed to start")
            return None
        return proc
    except Exception as e:
        logger.error(f"Airodump launch error: {e}")
        return None

def latest_csv():
    files = glob.glob(AIRO_CSV_GLOB)
    return max(files, key=os.path.getmtime) if files else None

def read_airodump_rows():
    """Yield (ssid, bssid, rssi) continuously."""
    while True:
        csv_path = latest_csv()
        if not csv_path:
            time.sleep(WIFI_REFRESH_INTERVAL)
            continue
        try:
            with open(csv_path, newline="", errors="ignore") as f:
                rows = [r for r in csv.reader(f) if len(r) > 1]
        except Exception:
            time.sleep(WIFI_REFRESH_INTERVAL)
            continue

        start = None
        for i, r in enumerate(rows):
            if r and r[0].strip().upper() == "BSSID":
                start = i + 1
                break
        if start is None:
            time.sleep(WIFI_REFRESH_INTERVAL)
            continue

        for r in rows[start:]:
            if len(r) < 14:
                break
            try:
                bssid = r[0].strip()
                rssi = int(float(r[8]))
                ssid = r[13].strip() or f"HIDDEN_{bssid[-5:].replace(':','')}"
                yield ssid, bssid, rssi
            except Exception:
                continue

        time.sleep(WIFI_REFRESH_INTERVAL)

# ---------------- HELPERS ----------------
def sanitize_ssid(ssid: str, bssid: str):
    safe = "".join(c if c.isalnum() or c in ("_", "-", ".") else "_" for c in ssid).strip("_")
    if not safe:
        safe = bssid
    return safe[:50], safe

# ---------------- MAIN ----------------
def main():
    connect_tak()
    threading.Thread(target=gps_loop, daemon=True).start()
    logger.info("🌐 Starting dual-band Wi-Fi geolocation with artifact logging")

    ap_db = {}
    global airodump_proc
    airodump_proc = start_airodump()
    if not airodump_proc:
        logger.error("❌ Airodump failed; exiting.")
        return

    try:
        logger.info("🔍 Beginning Wi-Fi scan and geolocation loop")
        for ssid, bssid, rssi in read_airodump_rows():
            lat = current_position.get("lat")
            lon = current_position.get("lon")
            if lat is None or lon is None:
                logger.info("Waiting for valid GPS fix…")
                time.sleep(1)
                continue

            # Log data source artifact for EVERY sample
            log_data_source(ssid, bssid, rssi, lat, lon)

            if ssid not in ap_db:
                ap_db[ssid] = {
                    "bssid": bssid,
                    "samples": [],
                    "est_lat": lat,
                    "est_lon": lon,
                    "best_rssi": rssi,
                    "best_lat": lat,
                    "best_lon": lon,
                    "unc_m": MAX_UNC_M,
                }

            rec = ap_db[ssid]
            rec["samples"].append((lat, lon, rssi))
            rec["samples"] = rec["samples"][-100:]  # keep last N samples

            # Track strongest-point fallback
            if rssi > rec["best_rssi"]:
                rec["best_rssi"] = rssi
                rec["best_lat"] = lat
                rec["best_lon"] = lon

            # Run multilateration
            est_lat_new, est_lon_new, unc_m, spread, rssi_std, n_est = multilaterate(rec["samples"])

            # Log processing artifact every attempt
            log_processing(ssid, len(rec["samples"]), spread, rssi_std, unc_m, n_est)

            # If no new solution, fallback to last/best
            if est_lat_new is None or est_lon_new is None:
                # Prefer last known estimate
                est_lat_new = rec["est_lat"]
                est_lon_new = rec["est_lon"]
                # If estimate is still basically initial and we have a good strong-point
                if rec["best_rssi"] > -90:
                    est_lat_new = rec["best_lat"]
                    est_lon_new = rec["best_lon"]
                # Keep old uncertainty if we don't have a new one
                unc_m = rec.get("unc_m", MAX_UNC_M)
            else:
                if unc_m is None:
                    unc_m = rec.get("unc_m", MAX_UNC_M)

            # Smooth movement (does NOT snap to drone)
            rec["est_lat"] = SMOOTH_ALPHA * est_lat_new + (1.0 - SMOOTH_ALPHA) * rec["est_lat"]
            rec["est_lon"] = SMOOTH_ALPHA * est_lon_new + (1.0 - SMOOTH_ALPHA) * rec["est_lon"]
            rec["unc_m"]   = float(np.clip(unc_m, MIN_UNC_M, MAX_UNC_M))

            ap_uid, ap_name = sanitize_ssid(ssid, bssid)
            remark = (
                f"SSID={ssid} | BSSID={bssid} | RSSI={rssi} | "
                f"Samples={len(rec['samples'])} | unc≈{rec['unc_m']:.1f}m"
            )
            xml = make_ap_cot(ap_uid, ap_name, rec["est_lat"], rec["est_lon"], remark, stale_seconds=20)
            send_tak(xml)

            # Log output artifact
            log_output("a-f-G", ap_uid, rec["est_lat"], rec["est_lon"], rec["unc_m"])

            logger.info(
                f"📶 {ssid}: rssi={rssi}, est=({rec['est_lat']:.6f},{rec['est_lon']:.6f}), "
                f"unc={rec['unc_m']:.1f}m"
            )

    except KeyboardInterrupt:
        logger.info("🛑 Exiting cleanly.")
    finally:
        if airodump_proc:
            airodump_proc.terminate()
        restore_managed()

if __name__ == "__main__":
    main()
