#!/usr/bin/env python3
"""
FISSURE – Dual-Band Passive Wi-Fi Geolocation (2.4 GHz + 5 GHz)
----------------------------------------------------------------
✓ Captures both 2.4 GHz and 5 GHz bands via airodump-ng --band abg
✓ Auto-calibrates LNA gain (RSSI median → target)
✓ Weighted LSQ multilateration with adaptive path-loss exponent
✓ TAK TLS streaming + GPSD CoT loop
✓ Restores managed mode on exit
"""

import os, re, csv, glob, atexit, time, math, json, subprocess, threading, logging, socket, ssl
import numpy as np
import xml.etree.ElementTree as ET
import pytak

gps_stop_event = threading.Event()

# ---------- CONFIG ----------
#WIFI_INTERFACE = "wlx00c0ca956681"
WIFI_INTERFACE = "wlx00c0cab6704d"

MON_SUFFIX     = "mon"
AIRO_PREFIX    = "/tmp/airodump"
AIRO_CSV_GLOB  = AIRO_PREFIX + "-*.csv"

GPSD_HOST, GPSD_PORT = "127.0.0.1", 2947
GPS_REFRESH_INTERVAL  = 3.0
WIFI_REFRESH_INTERVAL = 0.5
SMOOTH_ALPHA = 0.3
CALIBRATION_PERIOD = 3.0

TAKSERVER_HOST, TAKSERVER_PORT = "172.19.0.3", 8089
CERT_FILE = "/home/loved/Installed_by_FISSURE/takserver-docker-5.3-RELEASE-24/tak/certs/files/takserver.pem"
KEY_FILE  = "/home/loved/Installed_by_FISSURE/takserver-docker-5.3-RELEASE-24/tak/certs/files/takserver.key"
CA_FILE   = CERT_FILE
DRONE_CALLSIGN, DRONE_UID = "DF-DRONE", "DF-DRONE"

LOG_DIR = "logs"; os.makedirs(LOG_DIR, exist_ok=True)
GAIN_STORE = os.path.join(LOG_DIR, "lna_gain_store.json")

# ---------- RF / PROPAGATION ----------
P_TX_REF = -45.0
N_MIN, N_MAX = 2.2, 3.8
LNA_GAIN_MIN, LNA_GAIN_MAX = 5.0, 30.0
RSSI_REF_TARGET = -60.0
CALIBRATION_SMOOTH = 0.4
LNA_GAIN_DB = 20.0

# ---------- LOGGING ----------
logging.basicConfig(
    filename="fissure_df_dualband.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fissure_df_dualband")
console = logging.StreamHandler(); console.setLevel(logging.INFO); logger.addHandler(console)

# ---------- GLOBAL ----------
current_position = {"lat": None, "lon": None, "alt": 0.0}
tak_sock = None
airodump_proc = None
airodump_iface_in_use = None

# ---------- PERSISTED GAIN ----------
def load_gain():
    global LNA_GAIN_DB
    try:
        if os.path.exists(GAIN_STORE):
            data = json.load(open(GAIN_STORE))
            if WIFI_INTERFACE in data:
                LNA_GAIN_DB = float(data[WIFI_INTERFACE])
                logger.info(f"📦 Loaded LNA gain {LNA_GAIN_DB:.1f} dB")
    except Exception as e:
        logger.warning(f"Gain load failed: {e}")

def save_gain():
    try:
        data = {}
        if os.path.exists(GAIN_STORE):
            data = json.load(open(GAIN_STORE))
        data[WIFI_INTERFACE] = round(LNA_GAIN_DB, 2)
        json.dump(data, open(GAIN_STORE, "w"), indent=2)
    except Exception as e:
        logger.warning(f"Gain save failed: {e}")

# ---------- TAK ----------
def connect_tak():
    global tak_sock
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=CA_FILE)
            ctx.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
            ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_REQUIRED
            conn = ctx.wrap_socket(s, server_hostname=TAKSERVER_HOST)
            conn.connect((TAKSERVER_HOST, TAKSERVER_PORT))
            tak_sock = conn
            logger.info("✅ Connected to TAKServer (TLS)")
            return
        except Exception as e:
            logger.warning(f"TAK connect failed: {e}; retrying in 5 s")
            time.sleep(5)

def make_cot(uid, callsign, lat, lon, hae, remark, cot_type="a-f-G", stale=10):
    if not hasattr(make_cot, "session_start"):
        make_cot.session_start = pytak.cot_time()
    ev = ET.Element("event", {
        "version":"2.0","type":cot_type,"uid":uid,
        "how":"h-g-i-g-o","time":pytak.cot_time(),
        "start":make_cot.session_start,"stale":pytak.cot_time(stale)})
    det = ET.SubElement(ev,"detail")
    ET.SubElement(det,"remarks").text = remark
    ET.SubElement(det,"contact").set("callsign",callsign)
    ET.SubElement(ev,"point",attrib={
        "lat":f"{lat:.8f}","lon":f"{lon:.8f}","hae":f"{hae:.1f}",
        "ce":"5.0","le":"5.0"})
    return ET.tostring(ev,encoding="utf-8",method="xml")

def send_cot(xml_bytes):
    global tak_sock
    if not tak_sock: connect_tak()
    try:
        tak_sock.sendall(xml_bytes)
    except Exception as e:
        logger.warning(f"TAK send failed: {e} — reconnecting")
        connect_tak()
        try: tak_sock.sendall(xml_bytes)
        except Exception: pass

# ---------- GEOMETRY ----------
def latlon_to_xy(lat,lon,lat0,lon0):
    R=6371000.0
    lat_r,lon_r,lat0_r,lon0_r=map(math.radians,[lat,lon,lat0,lon0])
    x=(lon_r-lon0_r)*math.cos((lat_r+lat0_r)/2)*R
    y=(lat_r-lat0_r)*R
    return x,y
def xy_to_latlon(x,y,lat0,lon0):
    R=6371000.0
    lat0_r,lon0_r=math.radians(lat0),math.radians(lon0)
    lat_r=y/R+lat0_r
    lon_r=x/(R*math.cos((lat_r+lat0_r)/2))+lon0_r
    return math.degrees(lat_r),math.degrees(lon_r)

def adaptive_n(samples,p_tx=P_TX_REF):
    if len(samples)<3: return 3.0
    lat0,lon0=samples[0][0],samples[0][1]
    dists,rssis=[],[]
    for lat,lon,rssi in samples:
        x,y=latlon_to_xy(lat,lon,lat0,lon0)
        dists.append(math.hypot(x,y)+1e-6)
        rssis.append(rssi-LNA_GAIN_DB)
    try:
        coeff=np.polyfit(np.log10(dists),(p_tx-np.array(rssis))/10.0,1)
        n=float(coeff[0])
    except Exception: n=3.0
    return float(np.clip(n,N_MIN,N_MAX))

def estimate_distance(rssi,p_tx=P_TX_REF,n=3.0):
    adj=rssi-LNA_GAIN_DB
    d=10**((p_tx-adj)/(10*n))
    return float(np.clip(d,1.0,150.0))

def multilaterate(samples,p_tx=P_TX_REF):
    if len(samples)<3: return samples[-1][0],samples[-1][1]
    n=adaptive_n(samples,p_tx)
    lat0=np.mean([s[0] for s in samples]); lon0=np.mean([s[1] for s in samples])
    xs,ys,rs,rssis=[],[],[],[]
    for lat,lon,rssi in samples:
        x,y=latlon_to_xy(lat,lon,lat0,lon0)
        xs.append(x); ys.append(y); rs.append(estimate_distance(rssi,p_tx,n)); rssis.append(rssi)
    xs,ys,rs,rssis=map(np.array,(xs,ys,rs,rssis))
    med=np.median(rssis); mask=np.abs(rssis-med)<8
    if not np.any(mask): mask=np.argsort(rssis)[-3:]
    xs,ys,rs=xs[mask],ys[mask],rs[mask]
    w=1/np.clip(rs,1,1e9)**2
    x=np.average(xs,weights=w); y=np.average(ys,weights=w)
    for _ in range(15):
        d=np.hypot(x-xs,y-ys)+1e-9
        J=np.column_stack(((x-xs)/d,(y-ys)/d))
        r=d-rs; W=np.diag(w)
        try: delta,*_=np.linalg.lstsq(J.T@W@J,-J.T@W@r,rcond=None)
        except np.linalg.LinAlgError: break
        x+=delta[0]; y+=delta[1]
        if np.linalg.norm(delta)<0.5: break
    est_lat,est_lon=xy_to_latlon(x,y,lat0,lon0)
    d_est=math.hypot(x,y)
    if d_est>200:
        scale=200.0/d_est
        est_lat,est_lon=xy_to_latlon(x*scale,y*scale,lat0,lon0)
    return est_lat,est_lon

# ---------- GPS ----------
def gps_loop():
    logger.info("Starting GPS loop")
    #while not gps_stop_event.is_set():
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.connect((GPSD_HOST,GPSD_PORT))
        s.sendall(b'?WATCH={"enable":true,"json":true}\n')
        buf=""; last=0
        while not gps_stop_event.is_set():
            try:
                data=s.recv(4096).decode(errors="ignore")
                if not data: time.sleep(0.5); continue
                buf+=data
                while "\n" in buf:
                    if gps_stop_event.is_set():
                        break
                    line,buf=buf.split("\n",1)
                    if not line.strip(): continue
                    try: msg=json.loads(line)
                    except: continue
                    if msg.get("class")=="TPV" and msg.get("mode",0)>=2:
                        lat,lon=msg.get("lat"),msg.get("lon")
                        alt=msg.get("altMSL") or msg.get("altHAE") or 0.0
                        if lat and lon:
                            current_position.update({"lat":lat,"lon":lon,"alt":alt})
                            if time.time()-last>=GPS_REFRESH_INTERVAL:
                                xml=make_cot(DRONE_UID,DRONE_CALLSIGN,lat,lon,alt,"Drone Position","a-f-A",6)
                                send_cot(xml); logger.info(f"Drone pos: {lat:.6f}, {lon:.6f}")
                                last=time.time()
            except socket.timeout:
                continue
    except Exception as e:
        logger.warning(f"GPS error: {e}"); time.sleep(2)

# ---------- AIRODUMP ----------
def _iface(cmd): subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def restore_managed():
    try:
        _iface(["sudo","ip","link","set",WIFI_INTERFACE,"down"])
        _iface(["sudo","iw","dev",WIFI_INTERFACE,"set","type","managed"])
        _iface(["sudo","ip","link","set",WIFI_INTERFACE,"up"])
        logger.info(f"✅ Restored {WIFI_INTERFACE} to managed mode")
    except Exception as e: logger.warning(f"⚠️ Restore failed: {e}")
atexit.register(restore_managed)

def start_airodump():
    mon=WIFI_INTERFACE+MON_SUFFIX
    _iface(["sudo","ip","link","set",mon,"down"])
    _iface(["sudo","iw","dev",mon,"del"])
    add=subprocess.run(["sudo","iw","dev",WIFI_INTERFACE,"interface","add",mon,"type","monitor"],
                       capture_output=True,text=True)
    if add.returncode!=0:
        err=add.stderr.strip(); logger.warning(f"⚠️ Sub-iface add failed: {err}")
        if "Invalid argument" in err or "policy validation" in err:
            logger.info(f"🔄 Fallback: switching {WIFI_INTERFACE} to monitor mode")
            _iface(["sudo","ip","link","set",WIFI_INTERFACE,"down"])
            subprocess.run(["sudo","iw","dev",WIFI_INTERFACE,"set","type","monitor"],check=False)
            _iface(["sudo","ip","link","set",WIFI_INTERFACE,"up"])
            use=WIFI_INTERFACE
        else: return None,None
    else:
        _iface(["sudo","ip","link","set",mon,"up"]); use=mon
    cmd=["sudo","airodump-ng","--berlin","1","--write-interval","1",
         "--band","abg","--output-format","csv","--write",AIRO_PREFIX,use]
    logger.info(f"📡 Launching airodump-ng on {use} (dual-band)")
    logger.info(f"    Command: {' '.join(cmd)}")
    try:
        p=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        time.sleep(2)
        if p.poll() is not None: logger.error("airodump-ng failed to start"); return None,None
        return p,use
    except Exception as e:
        logger.error(f"airodump launch failed: {e}"); return None,None

def latest_csv():
    f=glob.glob(AIRO_CSV_GLOB)
    return max(f,key=os.path.getmtime) if f else None

def read_airodump_rows():
    while True:
        csv_path=latest_csv()
        if not csv_path: time.sleep(WIFI_REFRESH_INTERVAL); continue
        try:
            rows=[r for r in csv.reader(open(csv_path,errors="ignore")) if len(r)>1]
        except Exception as e:
            logger.error(f"CSV read error: {e}"); time.sleep(WIFI_REFRESH_INTERVAL); continue
        idx=next((i for i,r in enumerate(rows) if r and r[0].strip().upper()=="BSSID"),None)
        if idx is None: time.sleep(WIFI_REFRESH_INTERVAL); continue
        for r in rows[idx+1:]:
            if not r or all(c.strip()=="" for c in r): break
            try:
                bssid=r[0].strip(); rssi=int(float(r[8].strip()))
                ssid=r[13].strip(" ,\t\r\n") if len(r)>13 else ""
                if not ssid or ssid.lower() in ("<hidden>","broadcast","unknown"):
                    ssid=f"HIDDEN_{bssid[-5:].replace(':','')}"
                yield ssid,bssid,rssi,time.time()
            except: continue
        time.sleep(WIFI_REFRESH_INTERVAL)

# ---------- AUTO-CAL ----------
def auto_calibrate_gain(ap_db):
    global LNA_GAIN_DB
    rssis=[r for ap in ap_db.values() for (_,_,r) in ap["samples"]]
    if len(rssis)<10: return
    med=float(np.median(rssis))
    delta=RSSI_REF_TARGET-med
    LNA_GAIN_DB=float(np.clip(LNA_GAIN_DB+CALIBRATION_SMOOTH*delta,LNA_GAIN_MIN,LNA_GAIN_MAX))
    logger.info(f"⚙️ Auto-cal: median RSSI={med:.1f} → LNA_GAIN_DB={LNA_GAIN_DB:.1f} dB")
    save_gain()

# ---------- HELPERS ----------
def sanitize_ssid(ssid,bssid):
    safe="".join(ch if ch.isalnum() or ch in("_","-",".") else "_" for ch in ssid).strip("_") or bssid
    return safe[:50],safe

# ---------- MAIN ----------
def main():
    load_gain(); connect_tak()
    threading.Thread(target=gps_loop,daemon=True).start()
    logger.info("🌐 Starting dual-band real-time multilateration (auto-cal LNA)")
    ap_db={}; last_cal=0
    global airodump_proc,airodump_iface_in_use
    airodump_proc,airodump_iface_in_use=start_airodump()
    if not airodump_proc: return
    try:
        for ssid,bssid,rssi,_ in read_airodump_rows():
            lat,lon=current_position.get("lat"),current_position.get("lon")
            if not lat or not lon: continue
            ap=ap_db.setdefault(ssid,{"bssid":bssid,"samples":[],"est_lat":lat,"est_lon":lon})
            ap["samples"].append((lat,lon,rssi))
            ap["samples"]=ap["samples"][-80:]
            if len(ap["samples"])<3: continue
            est_lat,est_lon=multilaterate(ap["samples"])
            ap["est_lat"]=SMOOTH_ALPHA*est_lat+(1-SMOOTH_ALPHA)*ap["est_lat"]
            ap["est_lon"]=SMOOTH_ALPHA*est_lon+(1-SMOOTH_ALPHA)*ap["est_lon"]
            uid,name=sanitize_ssid(ssid,bssid)
            remark=f"SSID={ssid} | RSSI={rssi} | Gain={LNA_GAIN_DB:.1f} dB"
            xml=make_cot(uid,name,ap["est_lat"],ap["est_lon"],0.0,remark,"a-f-G",20)
            send_cot(xml)
            logger.info(f"📶 {name}: rssi={rssi}, est=({ap['est_lat']:.6f}, {ap['est_lon']:.6f})")
            now=time.time()
            if now-last_cal>CALIBRATION_PERIOD:
                auto_calibrate_gain(ap_db)
                last_cal=now
    except KeyboardInterrupt:
        logger.info("🛑 Exiting cleanly.")
    finally:
        gps_stop_event.set()
        try:
            if airodump_proc and airodump_proc.poll() is None:
                airodump_proc.terminate()
                logger.info("airodump-ng terminated")
        finally:
            restore_managed()

if __name__=="__main__":
    main()
