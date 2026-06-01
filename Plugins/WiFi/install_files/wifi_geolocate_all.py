#!/usr/bin/env python3
"""
FISSURE – Wi-Fi Geolocate All Known Targets
-------------------------------------------
Purpose
-------
Observe all visible Wi-Fi APs, but emit detections only for target IDs that are
already known and explicitly passed in via parameters.

This operation does NOT create/update targets directly.
It emits detections for known Wi-Fi targets only.

Expected "parameters" keys:
- target_ids: list[str]                 REQUIRED for useful behavior
- search_similar_targets: bool          accepted but not used to create targets
- wifi_interface: str
- mon_suffix: str
- airo_prefix: str
- gpsd_host: str
- gpsd_port: int
- gps_refresh_interval: float
- wifi_refresh_interval: float
- min_detection_interval_s: float
- log_dir: str
"""

import os
import sys
import csv
import glob
import time
import json
import asyncio
import subprocess
import signal
import logging
from typing import Dict, Optional, List, Any, Callable, Union, Tuple

try:
    from fissure.utils.plugins.operations import Operation
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from fissure.utils.plugins.operations import Operation


MON_SUFFIX_DEFAULT = "mon"


class OperationMain(Operation):
    def __init__(
        self,
        sensor_node_id: Union[int, str] = 0,
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback: Union[Callable, None] = None,
        tak_cot_callback: Union[Callable, None] = None,
        status_callback: Union[Callable, None] = None,
        target_callback: Union[Callable, None] = None,
        artifact_manager=None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            sensor_node_id=sensor_node_id,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
            status_callback=status_callback,
            target_callback=target_callback,
            artifact_manager=artifact_manager,
        )

        self.parameters: Dict[str, Any] = parameters or {}

        self.target_ids: List[str] = []
        self.search_similar_targets: bool = False

        self.wifi_interface: str = "wlx00c0caa744fc"
        self.mon_suffix: str = MON_SUFFIX_DEFAULT

        self.airo_prefix: str = "/tmp/airodump"
        self.airo_csv_glob: str = self.airo_prefix + "-*.csv"

        self.gpsd_host: str = "127.0.0.1"
        self.gpsd_port: int = 2947
        self.gps_refresh_interval: float = 3.0
        self.wifi_refresh_interval: float = 0.5
        self.min_detection_interval_s: float = 1.0

        self.log_dir: str = "logs"
        os.makedirs(self.log_dir, exist_ok=True)

        self._gps_stop = asyncio.Event()
        self._current_position = {"lat": None, "lon": None, "alt": 0.0}

        self._airodump_proc: Optional[asyncio.subprocess.Process] = None
        self._airodump_iface_in_use: Optional[str] = None

        # map normalized bssid -> target_id
        self._known_wifi_targets: Dict[str, str] = {}

        # throttle duplicate emissions
        self._last_emit_time_by_bssid: Dict[str, float] = {}

    def _apply_parameters_from_runner(self) -> None:
        p = getattr(self, "parameters", None)
        self.logger.info(f"_apply_parameters_from_runner self.parameters={p!r} type={type(p)}")

        if not isinstance(p, dict):
            return

        raw_target_ids = p.get("target_ids", [])
        if isinstance(raw_target_ids, list):
            self.target_ids = [str(x).strip() for x in raw_target_ids if str(x).strip()]
        elif isinstance(raw_target_ids, str) and raw_target_ids.strip():
            # tolerate a single string for convenience
            self.target_ids = [raw_target_ids.strip()]
        else:
            self.target_ids = []

        self.search_similar_targets = bool(p.get("search_similar_targets", self.search_similar_targets))

        self.wifi_interface = p.get("wifi_interface", self.wifi_interface)
        self.mon_suffix = p.get("mon_suffix", self.mon_suffix)

        self.airo_prefix = p.get("airo_prefix", self.airo_prefix)
        self.airo_csv_glob = self.airo_prefix + "-*.csv"

        self.gpsd_host = p.get("gpsd_host", self.gpsd_host)
        self.gpsd_port = int(p.get("gpsd_port", self.gpsd_port))
        self.gps_refresh_interval = float(p.get("gps_refresh_interval", self.gps_refresh_interval))
        self.wifi_refresh_interval = float(p.get("wifi_refresh_interval", self.wifi_refresh_interval))
        self.min_detection_interval_s = float(p.get("min_detection_interval_s", self.min_detection_interval_s))

        self.log_dir = p.get("log_dir", self.log_dir)
        os.makedirs(self.log_dir, exist_ok=True)

        self.resource_args = {"wifi_interface": self.wifi_interface}

    @staticmethod
    def get_resources(dev: str = "") -> Dict[str, Any]:
        return {
            "usrp": {
                "type": "Alfa",
                "model": "",
                "serial": dev,
                "description": "Alfa Card",
                "required": True,
            }
        }

    # -----------------------
    # Target helpers
    # -----------------------
    @staticmethod
    def _normalize_bssid(bssid: str) -> str:
        return (bssid or "").replace(":", "").replace("-", "").strip().lower()

    def _derive_bssid_from_target_id(self, target_id: str) -> Tuple[str, str]:
        """
        Convert target_id like wifiap-24F5A28FC8DF into:
            normalized: 24f5a28fc8df
            colonized:  24:F5:A2:8F:C8:DF
        """
        if not target_id:
            return "", ""

        raw = target_id.strip()
        if raw.lower().startswith("wifiap-"):
            raw = raw[7:]

        raw = raw.replace(":", "").replace("-", "").strip()
        if len(raw) != 12:
            return "", ""

        norm = raw.lower()
        colon = ":".join(raw[i:i + 2] for i in range(0, 12, 2)).upper()
        return norm, colon

    def _build_known_wifi_target_map(self) -> None:
        self._known_wifi_targets = {}

        for target_id in self.target_ids:
            bssid_norm, bssid_colon = self._derive_bssid_from_target_id(target_id)
            if not bssid_norm:
                self.logger.warning(
                    f"Skipping target_id={target_id}; could not derive Wi-Fi BSSID"
                )
                continue

            self._known_wifi_targets[bssid_norm] = target_id
            self.logger.info(
                f"Known Wi-Fi target: target_id={target_id}, bssid={bssid_colon}"
            )

    # -----------------------
    # Airodump helpers
    # -----------------------
    def _iface(self, cmd: List[str]) -> None:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _restore_managed(self) -> None:
        try:
            self._iface(["sudo", "ip", "link", "set", self.wifi_interface, "down"])
            self._iface(["sudo", "iw", "dev", self.wifi_interface, "set", "type", "managed"])
            self._iface(["sudo", "ip", "link", "set", self.wifi_interface, "up"])
            self.logger.info(f"Restored {self.wifi_interface} to managed mode")
        except Exception as e:
            self.logger.warning(f"Restore failed: {e}")

    def _kill_existing_airodump(self) -> None:
        patterns = [
            f"airodump-ng.*--write {self.airo_prefix}",
            f"airodump-ng.* {self.wifi_interface}{self.mon_suffix}",
            f"airodump-ng.* {self.wifi_interface}",
        ]
        for pat in patterns:
            try:
                subprocess.run(
                    ["sudo", "pkill", "-f", pat],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            except Exception:
                pass

    async def _start_airodump(self) -> Tuple[Optional[asyncio.subprocess.Process], Optional[str]]:
        mon = self.wifi_interface + self.mon_suffix

        self._kill_existing_airodump()

        self._iface(["sudo", "ip", "link", "set", mon, "down"])
        self._iface(["sudo", "iw", "dev", mon, "del"])

        use: Optional[str] = None
        add = subprocess.run(
            ["sudo", "iw", "dev", self.wifi_interface, "interface", "add", mon, "type", "monitor"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        if add.returncode == 0:
            self._iface(["sudo", "ip", "link", "set", mon, "up"])
            use = mon
            self.logger.info(f"Created monitor interface: {mon}")
        else:
            err = (add.stderr or "").strip()
            self.logger.warning(f"Monitor sub-iface create failed: {err}")
            self.logger.info(f"Fallback: switching {self.wifi_interface} to monitor mode")
            self._iface(["sudo", "ip", "link", "set", self.wifi_interface, "down"])
            subprocess.run(
                ["sudo", "iw", "dev", self.wifi_interface, "set", "type", "monitor"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            self._iface(["sudo", "ip", "link", "set", self.wifi_interface, "up"])
            use = self.wifi_interface

        cmd = [
            "sudo", "-n",
            "airodump-ng",
            "--berlin", "1",
            "--write-interval", "1",
            "--band", "abg",
            "--output-format", "csv",
            "--write", self.airo_prefix,
            use,
        ]

        self.logger.info(f"Launching airodump-ng on {use} (dual-band)")
        self.logger.info(f"Command: {' '.join(cmd)}")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
            close_fds=True,
        )

        await asyncio.sleep(2.0)
        if proc.returncode is not None:
            err_b = b""
            try:
                err_b = await asyncio.wait_for(proc.stderr.read(), timeout=0.5)
            except Exception:
                pass
            self.logger.error(
                f"airodump-ng failed to start (rc={proc.returncode}). "
                f"stderr={err_b.decode(errors='ignore')}"
            )
            return None, None

        return proc, use

    def _latest_csv_path(self) -> Optional[str]:
        files = glob.glob(self.airo_csv_glob)
        return max(files, key=os.path.getmtime) if files else None

    def _read_airodump_rows_once(self) -> List[Dict[str, Any]]:
        """
        Reads the latest CSV once and returns AP rows as dicts.

        Current parsing:
        - BSSID     -> r[0]
        - channel   -> r[3]
        - privacy   -> r[5]
        - power     -> r[8]
        - ESSID     -> r[13]
        """
        csv_path = self._latest_csv_path()
        if not csv_path:
            return []

        try:
            with open(csv_path, errors="ignore", newline="") as f:
                rows = [r for r in csv.reader(f) if len(r) > 1]
        except Exception:
            return []

        idx = None
        for i, r in enumerate(rows):
            if r and r[0].strip().upper() == "BSSID":
                idx = i
                break
        if idx is None:
            return []

        out: List[Dict[str, Any]] = []
        for r in rows[idx + 1:]:
            if not r or all(c.strip() == "" for c in r):
                break

            try:
                bssid = r[0].strip()
                channel_text = r[3].strip() if len(r) > 3 else ""
                privacy = r[5].strip() if len(r) > 5 else ""
                power_text = r[8].strip() if len(r) > 8 else ""
                ssid = r[13].strip(" ,\t\r\n") if len(r) > 13 else ""

                if (not ssid) or (ssid.lower() in ("<hidden>", "broadcast", "unknown")):
                    ssid = ""

                channel = None
                if channel_text:
                    try:
                        channel = int(float(channel_text))
                    except Exception:
                        channel = None

                rssi = None
                if power_text:
                    try:
                        rssi = float(power_text)
                    except Exception:
                        rssi = None

                band = ""
                freq_mhz = None
                if channel is not None:
                    if 1 <= channel <= 14:
                        band = "2.4GHz"
                        if channel == 14:
                            freq_mhz = 2484.0
                        else:
                            freq_mhz = 2412.0 + 5.0 * (channel - 1)
                    elif 30 <= channel <= 177:
                        band = "5GHz"
                        freq_mhz = 5000.0 + 5.0 * channel

                out.append({
                    "ssid": ssid,
                    "bssid": bssid,
                    "bssid_norm": self._normalize_bssid(bssid),
                    "channel": channel,
                    "band": band,
                    "frequency_mhz": freq_mhz,
                    "rssi_dbm": rssi,
                    "encryption": privacy,
                })
            except Exception:
                continue

        return out

    # -----------------------
    # GPS loop
    # -----------------------
    async def _gps_loop(self) -> None:
        self.logger.info("Starting GPS loop (GPSD)")
        buf = ""

        while (not self._stop) and (not self._gps_stop.is_set()):
            try:
                reader, writer = await asyncio.open_connection(self.gpsd_host, self.gpsd_port)
                writer.write(b'?WATCH={"enable":true,"json":true}\n')
                await writer.drain()

                while (not self._stop) and (not self._gps_stop.is_set()):
                    data = await reader.read(4096)
                    if not data:
                        await asyncio.sleep(0.5)
                        continue

                    buf += data.decode(errors="ignore")

                    while "\n" in buf:
                        if self._stop or self._gps_stop.is_set():
                            break

                        line, buf = buf.split("\n", 1)
                        if not line.strip():
                            continue

                        try:
                            msg = json.loads(line)
                        except Exception:
                            continue

                        if msg.get("class") == "TPV" and msg.get("mode", 0) >= 2:
                            lat = msg.get("lat")
                            lon = msg.get("lon")
                            alt = msg.get("altMSL") or msg.get("altHAE") or 0.0

                            if lat and lon:
                                self._current_position.update({
                                    "lat": float(lat),
                                    "lon": float(lon),
                                    "alt": float(alt),
                                })

                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

            except Exception as e:
                self.logger.warning(f"GPS error: {e}")
                await asyncio.sleep(2.0)

    # -----------------------
    # Detection emit
    # -----------------------
    async def _emit_detection(
        self,
        *,
        target_id: str,
        ssid: str,
        bssid: str,
        channel: Optional[int],
        band: str,
        frequency_mhz: Optional[float],
        rssi_dbm: Optional[float],
        encryption: str,
    ) -> None:
        if not self.tak_cot_callback:
            return

        ts_epoch = time.time()

        detection = {
            "event_type": "detection",
            "detection_kind": "wifi_geolocate_all",
            "target_id": target_id,
            "sensor_node_id": str(self.sensor_node_id),
            "frequency_hz": int(frequency_mhz * 1e6) if frequency_mhz is not None else None,
            "frequency_mhz": frequency_mhz,
            "power_dbm": float(rssi_dbm) if rssi_dbm is not None else None,
            "timestamp": ts_epoch,
            "detector": "wifi_geolocate_all",
            "opid": self.opid,
            "ssid": ssid,
            "bssid": bssid,
            "channel": channel,
            "band": band,
            "encryption": encryption,
        }

        detection = {k: v for k, v in detection.items() if v is not None}

        uid_suffix = self._normalize_bssid(bssid) or str(int(ts_epoch))
        await self.tak_cot_callback({
            "msg_type": "event",
            "uid": f"wifi-geolocate-all-{uid_suffix}-{int(ts_epoch)}",
            "lat": True,
            "lon": True,
            "alt": True,
            "time": True,
            "data": detection,
            "opid": self.opid,
            "tak_icon": "r-x-fissure-detection",
        })

    # -----------------------
    # Main run
    # -----------------------
    async def run(self) -> None:
        self._apply_parameters_from_runner()
        self._build_known_wifi_target_map()

        if not self._known_wifi_targets:
            raise RuntimeError("wifi_geolocate_all requires at least one valid Wi-Fi target_id in target_ids")

        self.logger.info(
            f"Starting Wi-Fi geolocate all operation: "
            f"known_targets={len(self._known_wifi_targets)}, "
            f"search_similar_targets={self.search_similar_targets}"
        )

        if self.status_callback:
            await self.status_callback(
                f"Geolocating {len(self._known_wifi_targets)} known Wi-Fi targets"
            )

        gps_task = asyncio.create_task(self._gps_loop())

        self._airodump_proc, self._airodump_iface_in_use = await self._start_airodump()
        if not self._airodump_proc:
            self._gps_stop.set()
            try:
                await gps_task
            except Exception:
                pass
            return

        try:
            while not self._stop:
                lat = self._current_position.get("lat")
                lon = self._current_position.get("lon")
                if lat is None or lon is None:
                    await asyncio.sleep(self.wifi_refresh_interval)
                    continue

                rows = await self._to_thread_compat(self._read_airodump_rows_once)
                if not rows:
                    await asyncio.sleep(self.wifi_refresh_interval)
                    continue

                matched_count = 0

                for row in rows:
                    bssid_norm = row.get("bssid_norm", "")
                    target_id = self._known_wifi_targets.get(bssid_norm)
                    if not target_id:
                        continue

                    matched_count += 1

                    now = time.time()
                    last_emit = self._last_emit_time_by_bssid.get(bssid_norm, 0.0)
                    if (now - last_emit) < self.min_detection_interval_s:
                        continue

                    self._last_emit_time_by_bssid[bssid_norm] = now

                    ssid = row.get("ssid", "")
                    bssid = row.get("bssid", "")
                    channel = row.get("channel")
                    band = row.get("band", "")
                    frequency_mhz = row.get("frequency_mhz")
                    rssi_dbm = row.get("rssi_dbm")
                    encryption = row.get("encryption", "")

                    self.logger.info(
                        f"Matched known Wi-Fi target {target_id}: "
                        f"ssid={ssid or '<hidden>'}, bssid={bssid}, channel={channel}, "
                        f"freq_mhz={frequency_mhz}, rssi_dbm={rssi_dbm}"
                    )

                    await self._emit_detection(
                        target_id=target_id,
                        ssid=ssid,
                        bssid=bssid,
                        channel=channel,
                        band=band,
                        frequency_mhz=frequency_mhz,
                        rssi_dbm=rssi_dbm,
                        encryption=encryption,
                    )

                if self.status_callback:
                    if matched_count > 0:
                        await self.status_callback(
                            f"Tracking {matched_count} known Wi-Fi target matches"
                        )
                    else:
                        await self.status_callback(
                            f"Searching for {len(self._known_wifi_targets)} known Wi-Fi targets"
                        )

                await asyncio.sleep(self.wifi_refresh_interval)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.logger.exception(f"Wi-Fi geolocate all operation error: {e}")
        finally:
            self._gps_stop.set()
            try:
                await asyncio.wait_for(gps_task, timeout=3.0)
            except Exception:
                pass

            try:
                if self._airodump_proc and self._airodump_proc.returncode is None:
                    try:
                        os.killpg(self._airodump_proc.pid, signal.SIGTERM)
                    except Exception:
                        self._airodump_proc.terminate()
                    try:
                        await asyncio.wait_for(self._airodump_proc.wait(), timeout=3.0)
                    except asyncio.TimeoutError:
                        try:
                            os.killpg(self._airodump_proc.pid, signal.SIGKILL)
                        except Exception:
                            self._airodump_proc.kill()
            except Exception:
                pass

            try:
                await self._to_thread_compat(self._restore_managed)
            except Exception:
                pass

            self.logger.info("Wi-Fi geolocate all operation stopped cleanly.")

    async def _to_thread_compat(self, func, *args, **kwargs):
        if hasattr(asyncio, "to_thread"):
            return await asyncio.to_thread(func, *args, **kwargs)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


if __name__ == "__main__":
    from fissure.utils.plugins.test_operation import run_test
    run_test(OperationMain, {}, {})