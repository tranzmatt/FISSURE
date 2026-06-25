#!/usr/bin/env python3
"""
TSI Feature Extractor Operation (headless)

Given a folder of IQ artifacts, or an explicit file list, compute a set of
selected time-domain and frequency-domain features per file.

Stop semantics
--------------
- If stop is requested, exit promptly and DO NOT write tsi_features.json.
  This prevents downstream stages from running on partial output.
"""

import asyncio
import hashlib
import inspect
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

try:
    from scipy import stats
    from scipy.fft import fft, next_fast_len
except Exception:  # pragma: no cover
    stats = None
    fft = None
    next_fast_len = None


# -------------------------------------------------------------------
# Plugin/repo import bootstrap
# -------------------------------------------------------------------

PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FISSURE_REPO_ROOT = os.path.abspath(os.path.join(PLUGIN_ROOT, "..", ".."))

for path in (FISSURE_REPO_ROOT, PLUGIN_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from fissure.utils.plugins.operations import Operation
    from fissure.utils import FISSURE_ROOT
except ImportError:
    if FISSURE_REPO_ROOT not in sys.path:
        sys.path.insert(0, FISSURE_REPO_ROOT)
    if PLUGIN_ROOT not in sys.path:
        sys.path.insert(0, PLUGIN_ROOT)

    from fissure.utils.plugins.operations import Operation
    from fissure.utils import FISSURE_ROOT


# -------------------------------------------------------------------
# Defaults
# -------------------------------------------------------------------

DEFAULTS: Dict[str, Any] = {
    "checkboxes": [
        "Mean",
        "Max",
        "Peak",
        "Peak to Peak",
        "RMS",
        "Variance",
        "Standard Deviation",
        "Power",
        "Crest Factor",
        "Pulse Indicator",
        "Margin",
        "Kurtosis",
        "Skewness",
        "Zero Crossings",
        "Samples",
        "Mean of Band Power Spectrum",
        "Max of Band Power Spectrum",
        "Sum of Total Band Power",
        "Peak of Band Power",
        "Variance of Band Power",
        "Standard Deviation of Band Power",
        "Skewness of Band Power",
        "Kurtosis of Band Power",
        "Relative Spectral Peak per Band",
    ],
    "data_type": "Complex Float 32",
    "extensions": [".iq", ".bin", ".raw", ".dat"],
    "selection_sidecar": "selected_files.json",
}


FFT_FEATURES = {
    "Mean of Band Power Spectrum",
    "Max of Band Power Spectrum",
    "Sum of Total Band Power",
    "Peak of Band Power",
    "Variance of Band Power",
    "Standard Deviation of Band Power",
    "Skewness of Band Power",
    "Kurtosis of Band Power",
    "Relative Spectral Peak per Band",
}


# -------------------------------------------------------------------
# Generic helpers
# -------------------------------------------------------------------

def _json_safe(value: Any) -> Any:
    """
    Convert numpy/scipy scalar values into JSON-safe Python values.
    Non-finite floats are represented as None so downstream JSON parsers do not
    have to accept NaN/Infinity extensions.
    """
    if isinstance(value, np.generic):
        value = value.item()

    if isinstance(value, complex):
        value = float(np.real(value))

    if isinstance(value, float) and not np.isfinite(value):
        return None

    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_json_safe(v) for v in value]

    return value


def _sha256_file(path: str, block_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(block_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _infer_artifact_id(folder: Optional[str], explicit_artifact_id: Optional[str] = None) -> str:
    if explicit_artifact_id:
        return str(explicit_artifact_id)

    if not folder:
        return ""

    folder_abs = os.path.abspath(folder)
    parts = folder_abs.split(os.sep)

    # Expected artifact file folder:
    #   <FISSURE_ROOT>/artifacts/<artifact_id>/files
    try:
        idx = parts.index("artifacts")
        if len(parts) > idx + 1:
            return parts[idx + 1]
    except ValueError:
        pass

    if os.path.basename(folder_abs) == "files":
        return os.path.basename(os.path.dirname(folder_abs))

    return ""


async def _call_with_timeout(callback, payload: Dict[str, Any], logger: logging.Logger, name: str) -> None:
    if callback is None:
        return

    try:
        result = callback(payload)
        if inspect.isawaitable(result):
            await asyncio.wait_for(result, timeout=2.0)
    except Exception:
        logger.exception("%s failed", name)


async def _set_status(callback, value: str, logger: logging.Logger) -> None:
    if callback is None:
        return

    try:
        result = callback(value)
        if inspect.isawaitable(result):
            await asyncio.wait_for(result, timeout=2.0)
    except Exception:
        logger.exception("status_callback failed")


# -------------------------------------------------------------------
# IQ reading helpers
# -------------------------------------------------------------------

def _dtype_info(data_type: str) -> Tuple[np.dtype, bool]:
    """
    Returns (base_dtype, is_complex_interleaved).

    For complex interleaved formats, file is [I0, Q0, I1, Q1, ...] in base_dtype.
    """
    dt = (data_type or "").strip()

    if dt == "Complex Float 32":
        return (np.float32, True)
    if dt == "Complex Float 64":
        return (np.float64, True)
    if dt in ("Complex Int 16", "Short/Int 16"):
        return (np.int16, True)
    if dt in ("Complex Int 8", "Byte/Int 8"):
        return (np.int8, True)
    if dt == "Complex Int 64":
        return (np.int64, True)

    if dt == "Float/Float 32":
        return (np.float32, False)
    if dt == "Int/Int 32":
        return (np.int32, False)

    raise ValueError(f"Unsupported data_type: {data_type!r}")


def read_iq_file(path: str, data_type: str) -> np.ndarray:
    """
    Read an IQ artifact file into a numpy array.

    - If complex interleaved: returns complex array (complex64/complex128)
    - If real-only: returns real array
    """
    base_dtype, is_complex = _dtype_info(data_type)

    raw = np.fromfile(path, dtype=base_dtype)
    if raw.size == 0:
        return raw

    if is_complex:
        if raw.size < 2:
            return np.array([], dtype=np.complex64)

        if (raw.size % 2) != 0:
            raw = raw[:-1]

        if base_dtype == np.float64:
            return (raw[0::2] + 1j * raw[1::2]).astype(np.complex128, copy=False)

        i = raw[0::2].astype(np.float32, copy=False)
        q = raw[1::2].astype(np.float32, copy=False)
        return i + 1j * q

    return raw


# -------------------------------------------------------------------
# Feature extraction
# -------------------------------------------------------------------

def compute_features(
    x: np.ndarray,
    data_type: str,
    checkboxes: List[str],
) -> Dict[str, Union[int, float, None]]:
    """
    Compute selected features over x (complex or real).
    Returns {feature_name: value}.
    """
    out: Dict[str, Union[int, float, None]] = {}

    if x.size == 0:
        return out

    is_complex = np.iscomplexobj(x)

    need_fft = any(f in FFT_FEATURES for f in checkboxes)
    S = None
    if need_fft:
        if fft is None or next_fast_len is None:
            raise RuntimeError("scipy is required for FFT-based features (scipy.fft).")
        nfft = next_fast_len(len(x))
        ft = fft(x, nfft)
        S = (np.abs(ft) ** 2) / max(len(x), 1)

    def _as_float(v: Any) -> Optional[float]:
        if np.isscalar(v):
            if isinstance(v, (np.complex64, np.complex128, complex)):
                v = np.real(v)
            v = float(v)
            return v if np.isfinite(v) else None
        v = float(v)
        return v if np.isfinite(v) else None

    # Time Domain
    if "Mean" in checkboxes:
        out["Mean"] = _as_float(np.mean(x))

    if "Max" in checkboxes:
        out["Max"] = _as_float(np.max(np.abs(x)) if is_complex else np.max(x))

    if "Peak" in checkboxes:
        out["Peak"] = _as_float(np.max(np.abs(x)))

    if "Peak to Peak" in checkboxes:
        out["Peak to Peak"] = _as_float(np.ptp(np.abs(x)) if is_complex else np.ptp(x))

    if "RMS" in checkboxes:
        out["RMS"] = _as_float(np.sqrt(np.mean((np.abs(x) ** 2) if is_complex else (x ** 2))))

    if "Variance" in checkboxes:
        out["Variance"] = _as_float(np.var(x))

    if "Standard Deviation" in checkboxes:
        out["Standard Deviation"] = _as_float(np.std(x))

    if "Power" in checkboxes:
        out["Power"] = _as_float(np.mean((np.abs(x) ** 2) if is_complex else (x ** 2)))

    if "Crest Factor" in checkboxes:
        denom = np.sqrt(np.mean((np.abs(x) ** 2) if is_complex else (x ** 2)))
        out["Crest Factor"] = _as_float((np.max(np.abs(x)) / denom) if denom != 0 else 0.0)

    if "Pulse Indicator" in checkboxes:
        denom = np.mean(np.abs(x)) if is_complex else np.mean(x)
        out["Pulse Indicator"] = _as_float((np.max(np.abs(x)) / denom) if denom != 0 else 0.0)

    if "Margin" in checkboxes:
        denom = (np.abs(np.mean(np.sqrt(np.abs(x)))) ** 2) if is_complex else (abs(np.mean(np.sqrt(np.abs(x)))) ** 2)
        out["Margin"] = _as_float((np.max(np.abs(x)) / denom) if denom != 0 else 0.0)

    if "Kurtosis" in checkboxes:
        if stats is None:
            raise RuntimeError("scipy is required for kurtosis/skew features (scipy.stats).")
        v = np.abs(x) if is_complex else x
        out["Kurtosis"] = _as_float(stats.kurtosis(v))

    if "Skewness" in checkboxes:
        if stats is None:
            raise RuntimeError("scipy is required for kurtosis/skew features (scipy.stats).")
        v = np.abs(x) if is_complex else x
        out["Skewness"] = _as_float(stats.skew(v))

    if "Zero Crossings" in checkboxes:
        if is_complex:
            i = np.real(x)
            q = np.imag(x)
            zc_i = int(np.where(np.diff(np.sign(i)))[0].shape[0])
            zc_q = int(np.where(np.diff(np.sign(q)))[0].shape[0])
            out["Zero Crossings"] = zc_i + zc_q
        else:
            out["Zero Crossings"] = int(np.where(np.diff(np.sign(x)))[0].shape[0])

    if "Samples" in checkboxes:
        out["Samples"] = int(len(x))

    # Frequency Domain
    if S is not None:
        if "Mean of Band Power Spectrum" in checkboxes:
            out["Mean of Band Power Spectrum"] = _as_float(np.mean(S))
        if "Max of Band Power Spectrum" in checkboxes:
            out["Max of Band Power Spectrum"] = _as_float(np.max(S))
        if "Sum of Total Band Power" in checkboxes:
            out["Sum of Total Band Power"] = _as_float(np.sum(S))
        if "Peak of Band Power" in checkboxes:
            out["Peak of Band Power"] = _as_float(np.max(np.abs(S)))
        if "Variance of Band Power" in checkboxes:
            out["Variance of Band Power"] = _as_float(np.var(S))
        if "Standard Deviation of Band Power" in checkboxes:
            out["Standard Deviation of Band Power"] = _as_float(np.std(S))
        if "Skewness of Band Power" in checkboxes:
            if stats is None:
                raise RuntimeError("scipy is required for skew features (scipy.stats).")
            out["Skewness of Band Power"] = _as_float(stats.skew(S))
        if "Kurtosis of Band Power" in checkboxes:
            if stats is None:
                raise RuntimeError("scipy is required for kurtosis features (scipy.stats).")
            out["Kurtosis of Band Power"] = _as_float(stats.kurtosis(S))
        if "Relative Spectral Peak per Band" in checkboxes:
            denom = np.mean(S)
            out["Relative Spectral Peak per Band"] = _as_float((np.max(S) / denom) if denom != 0 else 0.0)

    return out


def resolve_files_from_folder(folder: str, extensions: List[str]) -> List[str]:
    out: List[str] = []
    try:
        for name in os.listdir(folder):
            p = os.path.join(folder, name)
            if os.path.isfile(p) and any(name.lower().endswith(ext) for ext in extensions):
                out.append(p)
    except FileNotFoundError:
        return []
    return sorted(out)


def _resolve_sidecar_files(sidecar_path: str) -> List[str]:
    with open(sidecar_path, "r", encoding="utf-8") as f:
        blob = json.load(f)

    selected = blob.get("selected", [])
    if not isinstance(selected, list):
        return []

    base_dir = os.path.dirname(sidecar_path)
    out: List[str] = []
    for item in selected:
        if not isinstance(item, str):
            continue
        p = item if os.path.isabs(item) else os.path.join(base_dir, item)
        if os.path.isfile(p):
            out.append(os.path.abspath(p))
    return out


# -------------------------------------------------------------------
# Operation Implementation
# -------------------------------------------------------------------

class OperationMain(Operation):
    def __init__(
        self,
        node_uid: str = "",
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback=None,
        tak_cot_callback=None,
        status_callback=None,
        source_id: Optional[str] = None,
        artifact_id: Optional[str] = None,

        folder: Optional[str] = None,
        files: Optional[List[str]] = None,
        data_type: str = DEFAULTS["data_type"],
        checkboxes: Optional[List[str]] = None,
        extensions: Optional[List[str]] = None,
        selection_sidecar: str = DEFAULTS["selection_sidecar"],
    ):
        super().__init__(
            node_uid=node_uid,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
            status_callback=status_callback,
        )

        self.source_id = source_id or node_uid or "sensor_node"
        self.artifact_id = artifact_id or ""
        self.folder = folder
        self.files = files
        self.data_type = data_type
        self.checkboxes = checkboxes if checkboxes is not None else list(DEFAULTS["checkboxes"])
        self.extensions = extensions if extensions is not None else list(DEFAULTS["extensions"])
        self.selection_sidecar = selection_sidecar

        self.output_path: str = ""
        self.report_path: str = ""
        self.feature_results: List[Dict[str, Any]] = []
        self.report_payload: Dict[str, Any] = {}

    async def run(self) -> None:
        status_callback = getattr(self, "status_callback", None)
        params: Dict[str, Any] = getattr(self, "parameters", {}) or {}

        node_uid = str(params.get("node_uid", self.node_uid) or self.node_uid or "")
        source_id = str(params.get("source_id", self.source_id) or node_uid or "sensor_node")

        folder = params.get("folder", self.folder)
        files = params.get("files", self.files)
        data_type = params.get("data_type", self.data_type)
        checkboxes = params.get("checkboxes", self.checkboxes)
        extensions = params.get("extensions", self.extensions)
        sidecar_name = params.get("selection_sidecar", self.selection_sidecar)
        artifact_id = str(params.get("artifact_id", self.artifact_id) or "")

        if checkboxes is None:
            checkboxes = list(DEFAULTS["checkboxes"])
        if extensions is None:
            extensions = list(DEFAULTS["extensions"])

        folder = os.path.abspath(folder) if isinstance(folder, str) and folder else None
        resolved_files: List[str] = []
        wrote_features = False

        try:
            await _set_status(status_callback, "Running: Feature Extraction", self.logger)

            if files and isinstance(files, list):
                for f in files:
                    if not isinstance(f, str):
                        continue
                    p = os.path.abspath(f)
                    if os.path.isfile(p):
                        resolved_files.append(p)

                if not folder and resolved_files:
                    folder = os.path.dirname(resolved_files[0])

            elif folder and isinstance(folder, str):
                sidecar_path = os.path.join(folder, sidecar_name)
                if os.path.isfile(sidecar_path):
                    try:
                        resolved_files = _resolve_sidecar_files(sidecar_path)
                    except Exception as e:
                        self.logger.warning("Failed reading sidecar %s: %r", sidecar_path, e)

                if not resolved_files:
                    resolved_files = resolve_files_from_folder(folder, extensions)

            else:
                default_folder = os.path.join(FISSURE_ROOT, "artifacts", self.opid, "files")
                folder = os.path.abspath(default_folder)
                resolved_files = resolve_files_from_folder(folder, extensions)

            if not artifact_id:
                artifact_id = _infer_artifact_id(folder)
            self.artifact_id = artifact_id

            if not resolved_files:
                self.logger.warning("No input files resolved (folder=%r).", folder)
                return

            self.logger.info("TSI FE: data_type=%r, files=%d", data_type, len(resolved_files))
            await _set_status(
                status_callback,
                f"Running: Feature Extraction ({len(resolved_files)} files)",
                self.logger,
            )

            results: List[Dict[str, Any]] = []

            for index, path in enumerate(resolved_files, start=1):
                if self._stop:
                    self.logger.info("Stop requested; terminating feature extraction early.")
                    return

                try:
                    st = os.stat(path)
                    x = read_iq_file(path, data_type=data_type)
                    feats = compute_features(x, data_type=data_type, checkboxes=checkboxes)

                    results.append(
                        {
                            "file": os.path.basename(path),
                            "path": path,
                            "data_type": data_type,
                            "size_bytes": int(st.st_size),
                            "mtime": float(st.st_mtime),
                            "sha256": _sha256_file(path),
                            "features": _json_safe(feats),
                        }
                    )
                except Exception as e:
                    self.logger.error("Feature extraction failed for %s: %r", path, e)
                    results.append(
                        {
                            "file": os.path.basename(path),
                            "path": path,
                            "data_type": data_type,
                            "error": repr(e),
                        }
                    )

                if index < len(resolved_files):
                    await asyncio.sleep(0)

            if self._stop:
                self.logger.info("Stop requested; skipping tsi_features.json write.")
                return

            self.feature_results = results

            if folder:
                os.makedirs(folder, exist_ok=True)
                out_path = os.path.join(folder, "tsi_features.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(_json_safe(results), f, indent=2, allow_nan=False)
                self.output_path = out_path
                wrote_features = True
                self.logger.info("Wrote feature output: %s", out_path)

                report_payload = {
                    "kind": "artifact",
                    "event_type": "feature_extraction",
                    "node_uid": node_uid,
                    "source_id": source_id,
                    "operation_id": getattr(self, "opid", ""),
                    "artifact_id": artifact_id,
                    "folder": folder,
                    "feature_file": out_path,
                    "data_type": data_type,
                    "input_count": len(resolved_files),
                    "result_count": len(results),
                    "errors": [r for r in results if "error" in r],
                }
                self.report_payload = report_payload

                report_path = os.path.join(folder, "feature_extraction_report.json")
                with open(report_path, "w", encoding="utf-8") as f:
                    json.dump(_json_safe(report_payload), f, indent=2, allow_nan=False)
                self.report_path = report_path
                self.logger.info("Wrote feature extraction report: %s", report_path)

                await _call_with_timeout(
                    getattr(self, "alert_callback", None),
                    report_payload,
                    self.logger,
                    "alert_callback",
                )
                await _call_with_timeout(
                    getattr(self, "tak_cot_callback", None),
                    report_payload,
                    self.logger,
                    "tak_cot_callback",
                )

            return

        finally:
            if self._stop and not wrote_features:
                self.logger.info("Feature extraction stopped before output was written.")
            await _set_status(status_callback, "Idle", self.logger)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def _main():
        op = OperationMain(node_uid="test-node", logger=logging.getLogger("tsi_fe_test"))
        op.parameters = {
            "folder": "/tmp/some_artifact_folder",
            "data_type": "Complex Float 32",
        }
        await op.run()

    asyncio.run(_main())