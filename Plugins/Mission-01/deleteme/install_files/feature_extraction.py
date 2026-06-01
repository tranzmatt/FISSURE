#!/usr/bin/env python3
"""
TSI Feature Extractor Operation (headless)

Given a folder of IQ artifacts (or explicit file list), compute a set of
time-domain and frequency-domain features per file.

Stop semantics
--------------
- If stop is requested, exit promptly and DO NOT write tsi_features.json.
  This prevents downstream stages (classification) from running on partial output.
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

try:
    from scipy import stats
    from scipy.fft import fft, next_fast_len
except Exception:  # pragma: no cover
    stats = None
    fft = None
    next_fast_len = None

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
) -> Dict[str, Union[int, float]]:
    """
    Compute selected features over x (complex or real).
    Returns {feature_name: value}.
    """
    out: Dict[str, Union[int, float]] = {}

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

    def _as_float(v: Any) -> float:
        if np.isscalar(v):
            if isinstance(v, (np.complex64, np.complex128, complex)):
                return float(np.real(v))
            return float(v)
        return float(v)

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


# -------------------------------------------------------------------
# Operation Implementation
# -------------------------------------------------------------------

class OperationMain(Operation):
    def __init__(
        self,
        sensor_node_id: str = "",
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback=None,
        tak_cot_callback=None,

        folder: Optional[str] = None,
        files: Optional[List[str]] = None,
        data_type: str = DEFAULTS["data_type"],
        checkboxes: Optional[List[str]] = None,
        extensions: Optional[List[str]] = None,
        selection_sidecar: str = DEFAULTS["selection_sidecar"],
    ):
        super().__init__(
            sensor_node_id=sensor_node_id,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
        )

        self.folder = folder
        self.files = files
        self.data_type = data_type
        self.checkboxes = checkboxes if checkboxes is not None else list(DEFAULTS["checkboxes"])
        self.extensions = extensions if extensions is not None else list(DEFAULTS["extensions"])
        self.selection_sidecar = selection_sidecar

    async def run(self) -> None:
        # Prefer framework-injected parameters when present
        params: Dict[str, Any] = getattr(self, "parameters", {}) or {}

        folder = params.get("folder", self.folder)
        files = params.get("files", self.files)
        data_type = params.get("data_type", self.data_type)
        checkboxes = params.get("checkboxes", self.checkboxes)
        extensions = params.get("extensions", self.extensions)
        sidecar_name = params.get("selection_sidecar", self.selection_sidecar)

        if checkboxes is None:
            checkboxes = list(DEFAULTS["checkboxes"])
        if extensions is None:
            extensions = list(DEFAULTS["extensions"])

        resolved_files: List[str] = []

        if files and isinstance(files, list):
            resolved_files = [f for f in files if isinstance(f, str) and os.path.isfile(f)]

        elif folder and isinstance(folder, str):
            sidecar_path = os.path.join(folder, sidecar_name)
            if os.path.isfile(sidecar_path):
                try:
                    with open(sidecar_path, "r", encoding="utf-8") as f:
                        blob = json.load(f)
                    sel = blob.get("selected", [])
                    if isinstance(sel, list):
                        resolved_files = [p for p in sel if isinstance(p, str) and os.path.isfile(p)]
                except Exception as e:
                    self.logger.warning(f"Failed reading sidecar {sidecar_path}: {e!r}")

            if not resolved_files:
                resolved_files = resolve_files_from_folder(folder, extensions)

        else:
            default_folder = os.path.join(FISSURE_ROOT, "artifacts", self.opid, "files")
            resolved_files = resolve_files_from_folder(default_folder, extensions)
            folder = default_folder

        if not resolved_files:
            self.logger.warning(f"No input files resolved (folder={folder!r}).")
            return

        self.logger.info(f"TSI FE: data_type={data_type!r}, files={len(resolved_files)}")

        results: List[Dict[str, Any]] = []

        for path in resolved_files:
            if self._stop:
                self.logger.info("Stop requested; terminating feature extraction early.")
                # IMPORTANT: do not write tsi_features.json on partial/stopped runs
                return

            try:
                x = read_iq_file(path, data_type=data_type)
                feats = compute_features(x, data_type=data_type, checkboxes=checkboxes)

                results.append(
                    {
                        "file": os.path.basename(path),
                        "path": path,
                        "data_type": data_type,
                        "features": feats,
                    }
                )
            except Exception as e:
                self.logger.error(f"Feature extraction failed for {path}: {e!r}")
                results.append(
                    {
                        "file": os.path.basename(path),
                        "path": path,
                        "data_type": data_type,
                        "error": repr(e),
                    }
                )

        # Optional console output for debugging
        print(json.dumps(results, indent=2))

        # Write output next to artifacts (downstream expects this)
        if folder:
            out_path = os.path.join(folder, "tsi_features.json")
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2)
                self.logger.info(f"Wrote feature output: {out_path}")
            except Exception as e:
                self.logger.warning(f"Failed to write tsi_features.json: {e!r}")

        return


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def _main():
        op = OperationMain(sensor_node_id="test-node", logger=logging.getLogger("tsi_fe_test"))
        op.parameters = {
            "folder": "/tmp/some_artifact_folder",
            "data_type": "Complex Float 32",
        }
        await op.run()

    asyncio.run(_main())
