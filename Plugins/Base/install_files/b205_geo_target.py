#! /usr/bin/env python3
"""b205_geo_target.py

FISSURE Operation modeled after dummy_target.py structure.

- __init__ signature matches dummy_target style (callbacks + artifact_manager)
- run() is the only entrypoint
- GPS loop behavior matches wifi_geo.py (asyncio.open_connection to GPSD, WATCH JSON, buffered newline parsing)
- UHD/B205 RX streaming is started (start_cont) and recv() is called continuously so the device RX LED should light.
- Uses fissure_geo library for RSSI/power multilateration -> estimated lat/lon.
- Emits updates via target_callback in dummy_target-style schema (kwargs).

Parameters (in self.parameters dict):
  Frequencies (any one):
    - frequency_mhz: float
    - freq_hz: float
    - freqs_mhz: list[float]
    - freqs_hz: list[float]

  UHD:
    - uhd_args: str (default "type=b200")
    - sample_rate: float (default 1e6)
    - gain_db: float (default 25.0)
    - n_samp: int (default 16384)
    - rf_interval_s: float (default 0.20)
    - dwell_s: float (default 0.60)

  GPSD:
    - gpsd_host: str (default "127.0.0.1")
    - gpsd_port: int (default 2947)
    - gps_refresh_interval: float (default 3.0)  (for optional TAK 'drone position')

  Geo model:
    - pathloss_n: float (default 2.4)
    - p0_db: float (default -20.0) (used if auto_calibrate is False)
    - auto_calibrate: bool (default True)
    - d_ref_m: float (default 30.0)
    - cal_min_samples: int (default 20)
    - max_samples: int (default 80)
    - smooth_alpha: float (default 0.35)

  Emit:
    - emit_every_s: float (default 2.0)
    - meas_every_s: float (default 0.20)  # how often to compute RSSI + add_measurement
    - ce_every_s: float (default 6.0)     # how often to recompute CE (expensive)
    - ce_max_samples: int (default 30)    # how many samples CE uses
    - ce_m: float (default 75.0)

  Frequency detection (optional):
    - detect_frequency: bool (default True)  # estimate strongest emitter frequency in passband
    - fft_size: int (default 4096)           # FFT size (power of 2 recommended)
    - peak_snr_db: float (default 10.0)      # required peak above median noise floor
    - max_offset_hz: float (default 0.49*sample_rate)  # clamp offset to avoid odd reports
    - display_label_prefix: str (default "Emitter")
    - source_soi_id: str (default "")

Notes:
  - B205 typically doesn't output calibrated RSSI dBm; this uses relative power (dBFS) computed from IQ.
  - For relative power, auto_calibrate=True helps anchor a reasonable distance scale.
"""

import asyncio
import json
import logging
import math
import os
import sys
import tempfile
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np

try:
    from fissure.utils.plugins.operations import Operation
    from fissure.utils import FISSURE_ROOT
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from fissure.utils.plugins.operations import Operation
    from fissure.utils import FISSURE_ROOT

# from fissure_geo import PathLossModel, MultilaterationEstimator
# from fissure_geo import estimate_ce_from_samples

sys.path.insert(0, os.path.dirname(__file__))

from fissure_geo import PathLossModel, MultilaterationEstimator
from fissure_geo import estimate_ce_from_samples


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

        # wifi_geo-style GPS state
        self._gps_stop = asyncio.Event()
        self._current_position: Dict[str, Any] = {"lat": None, "lon": None, "alt": 0.0}

        # Defaults; may be overwritten in run()
        self.gpsd_host = "127.0.0.1"
        self.gpsd_port = 2947
        self.gps_refresh_interval = 3.0
        self.opid = str(uuid.uuid4())

    # -----------------------
    # Compatibility helpers
    # -----------------------
    def _should_stop(self) -> bool:
        if getattr(self, "_stop", False):
            return True
        ev = getattr(self, "stop_event", None)
        if ev is not None:
            try:
                return ev.is_set()
            except Exception:
                pass
        return False

    async def _maybe_await(self, result):
        import inspect
        if inspect.isawaitable(result):
            return await result
        return result

    async def _emit_target_update(self, **kwargs) -> None:
        """Emit via target_callback (dummy_target-style kwargs)."""
        if not self.target_callback:
            return
        try:
            await self._maybe_await(self.target_callback(**kwargs))
        except TypeError:
            # If wired to accept a single dict
            await self._maybe_await(self.target_callback(kwargs))

    def _now_iso(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _parse_freqs_hz(self, params: Dict[str, Any]) -> List[float]:
        freqs: List[float] = []
        if isinstance(params.get("freqs_hz"), (list, tuple)):
            freqs.extend([float(x) for x in params["freqs_hz"]])
        if isinstance(params.get("freqs_mhz"), (list, tuple)):
            freqs.extend([float(x) * 1e6 for x in params["freqs_mhz"]])
        if "freq_hz" in params:
            freqs.append(float(params["freq_hz"]))
        if "frequency_mhz" in params:
            freqs.append(float(params["frequency_mhz"]) * 1e6)
        if not freqs:
            # Safe default to make RX LED light during testing if user forgot frequency
            freqs = [915e6]
        return sorted({float(f) for f in freqs})

    # -----------------------
    # wifi_geo-style GPS loop
    # -----------------------
    async def _gps_loop(self) -> None:
        """Matches wifi_geo.py GPSD behavior."""
        self.logger.info("Starting GPS loop (GPSD)")
        last = 0.0
        buf = ""

        while (not self._should_stop()) and (not self._gps_stop.is_set()):
            try:
                reader, writer = await asyncio.open_connection(self.gpsd_host, self.gpsd_port)
                writer.write(b'?WATCH={"enable":true,"json":true}\n')
                await writer.drain()

                while (not self._should_stop()) and (not self._gps_stop.is_set()):
                    data = await reader.read(4096)
                    if not data:
                        await asyncio.sleep(0.5)
                        continue
                    buf += data.decode(errors="ignore")

                    while "\n" in buf:
                        if self._should_stop() or self._gps_stop.is_set():
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
                            alt = msg.get("altMSL") or msg.get("altHAE") or msg.get("alt") or 0.0
                            if lat is not None and lon is not None:
                                self._current_position.update(
                                    {"lat": float(lat), "lon": float(lon), "alt": float(alt or 0.0)}
                                )

                                now = time.time()
                                if (now - last) >= float(self.gps_refresh_interval):
                                    last = now

                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

            except Exception as e:
                self.logger.warning(f"GPS error: {e}")
                await asyncio.sleep(2.0)

        self.logger.info("GPS loop exited")

    # -----------------------
    # UHD helpers
    # -----------------------
    def _power_dbfs(self, iq: np.ndarray) -> float:
        p = float(np.mean(np.abs(iq) ** 2))
        p = max(p, 1e-12)
        return 10.0 * math.log10(p)


    def _detect_peak_offset_hz(
        self,
        iq: np.ndarray,
        sample_rate: float,
        *,
        fft_size: int = 4096,
        peak_snr_db: float = 10.0,
        max_offset_hz: Optional[float] = None,
    ) -> Optional[float]:
        """Estimate strongest spectral peak offset (Hz) from center.

        Returns:
          offset_hz (can be negative) or None if no peak passes SNR threshold.

        Notes:
        - Uses median power as a noise-floor proxy.
        - Designed to be fast enough to run at low Hz (e.g., meas_every_s).
        """
        if iq.size < 64:
            return None

        sr = float(sample_rate)
        if sr <= 0:
            return None

        n = int(fft_size)
        # Clamp FFT size to available samples
        n = min(n, int(iq.size))
        if n < 256:
            n = int(iq.size)

        # If n isn't power of 2, numpy is still fine, but power-of-2 is faster.
        x = np.asarray(iq[:n], dtype=np.complex64)

        # Hann window to reduce leakage
        w = np.hanning(n).astype(np.float32)
        xw = x * w

        spec = np.fft.fftshift(np.fft.fft(xw))
        pwr = (spec.real * spec.real) + (spec.imag * spec.imag)

        # Noise floor estimate
        noise = float(np.median(pwr))
        noise = max(noise, 1e-12)

        peak_idx = int(np.argmax(pwr))
        peak = float(pwr[peak_idx])
        peak = max(peak, 1e-12)

        snr_db = 10.0 * math.log10(peak / noise)
        if snr_db < float(peak_snr_db):
            return None

        freqs = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / sr))
        offset = float(freqs[peak_idx])

        if max_offset_hz is None:
            max_offset_hz = 0.49 * sr
        max_off = float(abs(max_offset_hz))
        if max_off > 0:
            offset = float(np.clip(offset, -max_off, max_off))

        return offset

    def _uhd_open(self, uhd_args: str, rate: float, gain: float):
        try:
            import uhd  # type: ignore
        except Exception:
            try:
                import pyuhd as uhd  # type: ignore
            except Exception as e:
                raise RuntimeError(
                    "UHD python bindings not found (uhd/pyuhd). Install python UHD bindings or adapt to SoapySDR."
                ) from e

        usrp = uhd.usrp.MultiUSRP(uhd_args)
        usrp.set_rx_rate(rate, 0)
        usrp.set_rx_gain(gain, 0)
        usrp.set_rx_antenna("TX/RX", 0)

        # Streamer
        st_args = uhd.usrp.StreamArgs("fc32", "sc16")
        streamer = usrp.get_rx_stream(st_args)
        md = uhd.types.RXMetadata()

        # Start continuous streaming (this should light RX LED once recv() is called)
        cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        cmd.stream_now = True
        streamer.issue_stream_cmd(cmd)

        return uhd, usrp, streamer, md

    def _stable_target_id_for_freq(self, freq_hz: float) -> str:
        return f"emitter-{int(freq_hz)}"

    def _make_artifact(self, *, operation_id: str, target_id: str, freq_hz: float, snapshot: Dict[str, Any]) -> str:
        if not self.artifact_manager:
            return ""
        evidence_dir = tempfile.mkdtemp(prefix="b205_geo_")
        with open(os.path.join(evidence_dir, "evidence.json"), "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

        try:
            return self.artifact_manager.create_zip_artifact_from_folder(
                source_id=getattr(self, "parameters", {}).get("source_id", "") if hasattr(self, "parameters") else "",
                operation_id=operation_id,
                folder=evidence_dir,
                name=f"B205 Geo evidence @ {freq_hz/1e6:.3f} MHz",
                metadata={
                    "role": "target_evidence_b205_geo",
                    "target_id": target_id,
                    "frequency_hz": float(freq_hz),
                    "frequency_mhz": float(freq_hz / 1e6),
                    "operation_id": operation_id,
                },
                arc_prefix=f"target_{operation_id}",
            )
        except Exception as e:
            self.logger.exception(f"Failed creating artifact: {e}")
            return ""

    # -----------------------
    # run()
    # -----------------------
    async def run(self) -> None:
        params: Dict[str, Any] = getattr(self, "parameters", {}) or {}

        if not self.target_callback:
            raise RuntimeError("b205_geo_target requires target_callback to be wired")

        # GPS config
        self.gpsd_host = str(params.get("gpsd_host", self.gpsd_host))
        self.gpsd_port = int(params.get("gpsd_port", self.gpsd_port))
        self.gps_refresh_interval = float(params.get("gps_refresh_interval", self.gps_refresh_interval))

        # UHD config
        uhd_args = str(params.get("uhd_args", "type=b200"))
        rate = float(params.get("sample_rate", 1e6))
        gain = float(params.get("gain_db", 60.0))
        n_samp = int(params.get("n_samp", 131072))
        rf_interval_s = float(params.get("rf_interval_s", 0.0))

        # Performance knobs: throttle computation, not recv()
        meas_every_s = float(params.get("meas_every_s", 0.20))
        ce_every_s = float(params.get("ce_every_s", 6.0))
        ce_max_samples = int(params.get("ce_max_samples", 30))
        dwell_s = float(params.get("dwell_s", 1.5))
        detect_frequency = bool(params.get("detect_frequency", True))
        fft_size = int(params.get("fft_size", 8192))
        peak_snr_db = float(params.get("peak_snr_db", 15.0))
        max_offset_hz = params.get("max_offset_hz", 200e3)
        max_offset_hz = float(max_offset_hz) if max_offset_hz is not None else None
         

        # Geo config
        pathloss_n = float(params.get("pathloss_n", 2.4))
        p0_db = float(params.get("p0_db", -20.0))
        auto_cal = bool(params.get("auto_calibrate", True))
        d_ref_m = float(params.get("d_ref_m", 30.0))
        cal_min_samples = int(params.get("cal_min_samples", 20))
        max_samples = int(params.get("max_samples", 80))
        smooth_alpha = float(params.get("smooth_alpha", 0.35))

        # Emit config
        emit_every_s = float(params.get("emit_every_s", 1.0))
        ce_m_default = float(params.get("ce_m", 75.0))
        ce_confidence = float(params.get("ce_confidence", 0.90))
        display_label_prefix = str(params.get("display_label_prefix", "Emitter"))
        source_soi_id = str(params.get("source_soi_id", "") or "")

        freqs_hz = self._parse_freqs_hz(params)

        if self.status_callback:
            await self._maybe_await(self.status_callback(f"Running: B205 Geo ({len(freqs_hz)} freqs)"))

        if not self.artifact_manager:
            self.logger.warning("artifact_manager not provided; TAK may not render targets if artifact_id is required")

        # Start GPS task (wifi_geo-style)
        # gps_task = asyncio.create_task(self._gps_loop())

        # --- GPS Setup ---
        try:
            # Attempt GPSD connection
            gps_task = asyncio.create_task(self._gps_loop())
        except Exception:
            gps_task = None

        # If no GPS position available shortly after start, fall back to fixed coordinates
        async def _gps_fallback_check():
            await asyncio.sleep(1.0)
            if self._current_position.get("lat") is None:
                self.logger.warning("GPS unavailable. Using fixed fallback coordinates.")
                self._current_position.update({
                    "lat": 40.712776,
                    "lon": -74.005974,
                    "alt": 10.5,
                })

        asyncio.create_task(_gps_fallback_check())


        # Open UHD and start streaming
        uhd, usrp, streamer, md = self._uhd_open(uhd_args, rate, gain)
        buf = np.empty(n_samp, dtype=np.complex64)

        # Per-frequency state
        per_freq: Dict[float, Dict[str, Any]] = {}
        for f in freqs_hz:
            model = PathLossModel(n=pathloss_n, p0_db=p0_db)
            est = MultilaterationEstimator(smooth_alpha=smooth_alpha, max_samples=max_samples)
            per_freq[f] = {
                "model": model,
                "est": est,
                "target_id": self._stable_target_id_for_freq(f),
                "last_emit": 0.0,
                "last_meas": 0.0,
                "last_ce": 0.0,
                "ce_cached": float(ce_m_default),
                "detected_freq_hz": None,
                "last_freq_det": 0.0,
                "artifact_id": "",
                "operation_id": str(uuid.uuid4()),
            }

        try:
            # Main loop
            while not self._should_stop():
                # Always call recv() to keep streaming active (LED), even if GPS isn't ready yet.
                for f in freqs_hz:
                    if self._should_stop():
                        break

                    # retune
                    try:
                        usrp.set_rx_freq(uhd.types.TuneRequest(float(f)), 0)
                    except Exception as e:
                        self.logger.warning(f"Tune failed for {f} Hz: {e}")
                        await asyncio.sleep(0.1)
                        continue

                    t0 = time.time()
                    while not self._should_stop() and (time.time() - t0) < dwell_s:
                        n = int(streamer.recv(buf, md, timeout=1.0) or 0)
                        if n <= 0:
                            # log metadata errors if any
                            try:
                                if md.error_code != uhd.types.RXMetadataErrorCode.none:
                                    self.logger.warning("RXMetadata error: %s", md.strerror())
                            except Exception:
                                pass
                            await asyncio.sleep(0.01)
                            continue


                        # GPS may not be ready; keep streaming regardless. Only record measurements when GPS is valid.
                        lat = self._current_position.get("lat")
                        lon = self._current_position.get("lon")
                        alt = self._current_position.get("alt", 0.0)

                        st = per_freq[f]
                        model: PathLossModel = st["model"]
                        est: MultilaterationEstimator = st["est"]

                        now = time.time()

                        # Throttle measurement work (RSSI + add_measurement), but DO NOT throttle recv().
                        if (lat is not None) and (lon is not None) and ((now - st["last_meas"]) >= meas_every_s):
                            p_dbfs = self._power_dbfs(buf[:n])


                            # Optional: detect strongest emitter frequency within the current passband.
                            # This is throttled implicitly by meas_every_s (and additionally by last_freq_det below).
                            if detect_frequency:
                                # Only run FFT occasionally even if meas_every_s is small
                                if (now - st["last_freq_det"]) >= max(0.2, meas_every_s):
                                    try:
                                        off = self._detect_peak_offset_hz(
                                            buf[:n],
                                            rate,
                                            fft_size=fft_size,
                                            peak_snr_db=peak_snr_db,
                                            max_offset_hz=max_offset_hz,
                                        )
                                        if off is not None:
                                            st["detected_freq_hz"] = float(f + off)
                                        st["last_freq_det"] = now
                                    except Exception:
                                        st["last_freq_det"] = now

                            est.add_measurement(
                                lat=float(lat),
                                lon=float(lon),
                                rssi_db=float(p_dbfs),
                                t=now,
                                model=model,
                                auto_calibrate=auto_cal,
                                d_ref_m=d_ref_m,
                                cal_min_samples=cal_min_samples,
                            )
                            st["last_meas"] = now

                        # Emit periodic target update once ready
                        if est.ready and (lat is not None) and (lon is not None) and ((now - st["last_emit"]) >= emit_every_s):
                            out_latlon = est.estimate_latlon(model)
                            if out_latlon is not None:
                                est_lat, est_lon = out_latlon

                                # CE is expensive: compute on a slower cadence and cache it
                                if (now - st["last_ce"]) >= ce_every_s:
                                    try:
                                        samples_ref = getattr(est, "_samples", None)
                                        if samples_ref is None:
                                            samples_ref = est.samples
                                        ce_calc = estimate_ce_from_samples(samples_ref[-ce_max_samples:], model, confidence=ce_confidence)
                                        if ce_calc is not None:
                                            st["ce_cached"] = float(ce_calc)
                                    except Exception:
                                        pass
                                    st["last_ce"] = now

                                ce_m = float(st.get("ce_cached", ce_m_default)) if st.get("ce_cached") is not None else float(ce_m_default)

                                now_iso = self._now_iso()
                                target_id = st["target_id"]
                                operation_id = st["operation_id"]

                                display_label = f"{display_label_prefix} @ {f/1e6:.3f} MHz"

                                classification = {
                                    "display_label": display_label,
                                    "candidates": [
                                        {"source": "radio", "label": "B205", "frequency_hz": float(st.get("detected_freq_hz") or f)},
                                        {"source": "model", "label": "RSSI multilateration", "confidence": 0.6},
                                    ],
                                }

                                location = {
                                    "lat": float(est_lat),
                                    "lon": float(est_lon),
                                    "hae_m": float(alt or 0.0),
                                    "ce_m": float(ce_m),
                                        "detected_frequency_hz": float(st.get("detected_freq_hz") or f),
                                    "timestamp": now_iso,
                                    "source": "b205_geo_target",
                                }

                                samples_ref = getattr(est, "_samples", None)
                                if samples_ref is None:
                                    samples_ref = est.samples
                                recent = samples_ref[-min(50, len(samples_ref)) :]
                                snapshot = {
                                    "target_id": target_id,
                                    "sensor_node_id": self.sensor_node_id,
                                    "frequency_hz": float(st.get("detected_freq_hz") or f),
                                    "frequency_mhz": float((st.get("detected_freq_hz") or f) / 1e6),
                                    "created_time": now_iso,
                                    "model": {
                                        "n": model.n,
                                        "p0_db": model.p0_db,
                                        "auto_calibrate": auto_cal,
                                        "d_ref_m": d_ref_m,
                                        "ce_confidence": float(ce_confidence),
                                    },
                                    "estimate": {"lat": float(est_lat), "lon": float(est_lon), "ce_m": float(ce_m)},
                                    "samples": [{"lat": s.lat, "lon": s.lon, "rssi_db": s.rssi_db, "t": s.t} for s in recent],
                                }

                                artifact_id = st["artifact_id"]
                                if not artifact_id and self.artifact_manager:
                                    artifact_id = self._make_artifact(
                                        operation_id=operation_id,
                                        target_id=target_id,
                                        freq_hz=f,
                                        snapshot=snapshot,
                                    )
                                    st["artifact_id"] = artifact_id

                                await self._emit_target_update(
                                    sensor_node_id=self.sensor_node_id,
                                    target_id=target_id,
                                    source_soi_id=source_soi_id,
                                    frequency_mhz=float((st.get("detected_freq_hz") or f) / 1e6),
                                    state="tracking",
                                    artifact_id=artifact_id,
                                    classification=classification,
                                    location=location,
                                    history_entry={
                                        "event": "b205_geo_update",
                                        "artifact_id": artifact_id,
                                        "operation_id": operation_id,
                                        "frequency_hz": float(st.get("detected_freq_hz") or f),
                                    },
                                    summary={
                                        "stage": "tracking",
                                        "stage_order": 20,
                                        "frequency_hz": float(st.get("detected_freq_hz") or f),
                                        "samples": len(samples_ref),
                                        "p0_db": float(model.p0_db),
                                        "n": float(model.n),
                                        "ce_m": float(ce_m),
                                        "detected_frequency_hz": float(st.get("detected_freq_hz") or f),
                                    },
                                    lat=float(est_lat),
                                    lon=float(est_lon),
                                    alt=float(alt or 0.0),
                                    observation_time=True,
                                )

                                st["last_emit"] = now

                        await asyncio.sleep(0) if rf_interval_s <= 0 else await asyncio.sleep(rf_interval_s)

                await asyncio.sleep(0.01)

        finally:
            # Stop GPS loop (wifi_geo-style)
            self._gps_stop.set()
            try:
                gps_task.cancel()
                await gps_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

            # Stop UHD streaming
            try:
                cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
                cmd.stream_now = True
                streamer.issue_stream_cmd(cmd)
            except Exception:
                pass

            if self.status_callback:
                await self._maybe_await(self.status_callback("Idle"))

            self.logger.info("B205 Geo operation stopped/complete.")


if __name__ == "__main__":
    # Standalone test harness (if present in your tree)
    from fissure.utils.plugins.test_operation import run_test

    # Example parameters to ensure RX starts and LED lights:
    #   {"frequency_mhz": 915.0}
    run_test(OperationMain, {}, {})
