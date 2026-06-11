#!/usr/bin/env python3
"""
Decision Tree Feature Classification (headless)

Reads per-file extracted features (tsi_features.json) and runs all eligible
Decision Tree models found in a models folder. Produces per-file predictions
and a batch consensus across files.

- No GUI, no dashboard messaging (unless status_callback is wired by your runner).
- Writes classification_report.json next to artifacts for later consumption.

Stop semantics
--------------
- If stop is requested, exit promptly and DO NOT write classification_report.json.
"""

import os
import json
import ast
import logging
import pickle
from typing import Any, Dict, List, Optional

import numpy as np

from fissure.utils.plugins.operations import Operation


def _default_models_folder() -> str:
    return os.path.join(os.path.dirname(__file__), "decision_tree_models")


def _read_model_details(txt_path: str) -> Dict[str, Any]:
    """
    Parses a model .txt file:
      Technique: Decision Tree
      Features: [...]
      Truth Categories: [...]
    """
    details: Dict[str, Any] = {"path": txt_path}
    with open(txt_path, "r", encoding="utf-8") as f:
        blob = f.read()

    details["raw"] = blob

    for line in blob.splitlines():
        if line.startswith("Technique: "):
            details["technique"] = line.split("Technique: ", 1)[1].strip()
        elif line.startswith("Features: "):
            try:
                details["features"] = ast.literal_eval(line.split("Features: ", 1)[1].strip())
            except Exception:
                details["features"] = []
        elif line.startswith("Truth Categories: "):
            try:
                details["truth_categories"] = line.split("Truth Categories: ", 1)[1].strip()
            except Exception:
                pass

    if "features" not in details:
        details["features"] = []

    return details


def _load_feature_rows(features_json_path: str) -> List[Dict[str, Any]]:
    with open(features_json_path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    if not isinstance(rows, list):
        raise ValueError("features file must be a JSON list")

    return rows


def _eligible_models(model_details: List[Dict[str, Any]], available_features: List[str]) -> List[Dict[str, Any]]:
    avail = set(available_features)
    out: List[Dict[str, Any]] = []
    for md in model_details:
        req = md.get("features", [])
        if isinstance(req, list) and req and set(req).issubset(avail):
            out.append(md)
    return out


def _safe_float(v: Any) -> float:
    try:
        if v is None:
            return float("nan")
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, (np.integer, np.floating)):
            return float(v)
        return float(v)
    except Exception:
        return float("nan")


def _find_model_file(models_folder: str, model_stem: str) -> Optional[str]:
    """
    Support both legacy naming and sane pickle naming.
    Prefer .pkl/.pickle, but allow .h5 if that's how your repo is laid out.
    """
    candidates = [
        os.path.join(models_folder, model_stem + ".pkl"),
        os.path.join(models_folder, model_stem + ".pickle"),
        os.path.join(models_folder, model_stem + ".h5"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


class OperationMain(Operation):
    def __init__(
        self,
        node_uid: str = "",
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback=None,
        tak_cot_callback=None,
        status_callback=None,

        # operation parameters
        folder: Optional[str] = None,
        models_folder: Optional[str] = None,
        features_file: str = "tsi_features.json",
        min_models: int = 2,
        use_batch_consensus: bool = True,
    ):
        super().__init__(
            node_uid=node_uid,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
            status_callback=status_callback,
        )

        self.folder = folder
        self.models_folder = models_folder or _default_models_folder()
        self.features_file = features_file
        self.min_models = int(min_models)
        self.use_batch_consensus = bool(use_batch_consensus)

    async def run(self) -> None:
        params: Dict[str, Any] = getattr(self, "parameters", {}) or {}

        folder = params.get("folder", self.folder)
        models_folder = params.get("models_folder", self.models_folder)
        features_file = params.get("features_file", self.features_file)
        min_models = int(params.get("min_models", self.min_models))
        use_batch_consensus = bool(params.get("use_batch_consensus", self.use_batch_consensus))

        # Optional status reporting (NO Idle here; runner should own Idle)
        if getattr(self, "status_callback", None):
            try:
                await self.status_callback("Running: Classifying Features")
            except Exception:
                self.logger.exception("status_callback failed (set running)")

        if self._stop:
            return

        if not folder or not isinstance(folder, str):
            self.logger.warning("No folder provided to classifier op; nothing to do.")
            return

        features_path = os.path.join(folder, features_file)
        if not os.path.isfile(features_path):
            self.logger.warning(f"Missing features file: {features_path}")
            return

        if not models_folder or not os.path.isdir(models_folder):
            self.logger.warning(f"Missing/invalid models_folder: {models_folder!r}")
            return

        # Load feature rows (one per IQ file)
        rows = _load_feature_rows(features_path)
        if self._stop:
            return

        # Collect available feature names (union across rows)
        avail_features = set()
        for r in rows:
            feats = r.get("features", {})
            if isinstance(feats, dict):
                avail_features |= set(feats.keys())
        avail_features_list = sorted(avail_features)

        # Discover model .txt files
        model_details: List[Dict[str, Any]] = []
        for name in os.listdir(models_folder):
            if self._stop:
                return
            if name.lower().endswith(".txt"):
                p = os.path.join(models_folder, name)
                try:
                    md = _read_model_details(p)
                    if md.get("technique") == "Decision Tree":
                        model_details.append(md)
                except Exception as e:
                    self.logger.warning(f"Failed reading model details {p}: {e!r}")

        if not model_details:
            self.logger.warning(f"No decision-tree model .txt files found in {models_folder}")
            return

        eligible_any = _eligible_models(model_details, avail_features_list)
        if len(eligible_any) < min_models:
            self.logger.warning(
                f"Insufficient eligible models ({len(eligible_any)} < {min_models}). "
                f"Available features: {len(avail_features_list)}"
            )
            # continue anyway

        # Per-file inference
        per_file: List[Dict[str, Any]] = []

        for r in rows:
            if self._stop:
                return

            file_name = r.get("file")
            feats = r.get("features", {})

            if not isinstance(feats, dict) or not feats:
                per_file.append({"file": file_name, "error": "missing_features"})
                continue

            file_avail = sorted(feats.keys())
            file_eligible = _eligible_models(model_details, file_avail)

            votes: Dict[str, str] = {}
            skipped: List[Dict[str, Any]] = []

            for md in file_eligible:
                if self._stop:
                    return

                model_stem = os.path.splitext(os.path.basename(md["path"]))[0]
                model_path = _find_model_file(models_folder, model_stem)

                if not model_path:
                    skipped.append(
                        {
                            "model": model_stem,
                            "reason": "missing_model_file",
                            "expected_one_of": [
                                f"{model_stem}.pkl",
                                f"{model_stem}.pickle",
                                f"{model_stem}.h5",
                            ],
                        }
                    )
                    continue

                req_feats = md.get("features", [])
                if not isinstance(req_feats, list) or not req_feats:
                    skipped.append({"model": model_stem, "reason": "missing_required_features"})
                    continue

                X = np.array([[_safe_float(feats.get(f)) for f in req_feats]], dtype=np.float64)

                try:
                    with open(model_path, "rb") as f:
                        clf = pickle.load(f)
                    y_pred = clf.predict(X)
                    votes[model_stem] = str(y_pred[0])
                except Exception as e:
                    skipped.append({"model": model_stem, "reason": "predict_failed", "error": repr(e)})

            # Vote tally
            vote_counts: Dict[str, int] = {}
            for lbl in votes.values():
                vote_counts[lbl] = vote_counts.get(lbl, 0) + 1

            if vote_counts:
                best_label = max(vote_counts.items(), key=lambda kv: kv[1])[0]
                models_used = len(votes)
                best_votes = vote_counts[best_label]
                confidence = (best_votes / models_used) if models_used > 0 else None
            else:
                best_label = None
                confidence = None
                models_used = 0

            per_file.append(
                {
                    "file": file_name,
                    "models_used": models_used,
                    "votes": votes,
                    "vote_counts": vote_counts,
                    "consensus": {"label": best_label, "confidence": confidence},
                    "skipped": skipped,
                }
            )

        # Batch consensus across files
        batch = {"label": None, "confidence": None, "files_used": 0, "vote_counts": {}}

        if use_batch_consensus and not self._stop:
            batch_counts: Dict[str, int] = {}
            used_files = 0
            for pf in per_file:
                if self._stop:
                    return
                lbl = pf.get("consensus", {}).get("label")
                if lbl:
                    batch_counts[lbl] = batch_counts.get(lbl, 0) + 1
                    used_files += 1

            if batch_counts:
                batch_label = max(batch_counts.items(), key=lambda kv: kv[1])[0]
                batch_votes = batch_counts[batch_label]
                batch_conf = (batch_votes / used_files) if used_files > 0 else None
                batch = {
                    "label": batch_label,
                    "confidence": batch_conf,
                    "files_used": used_files,
                    "vote_counts": batch_counts,
                }

        if self._stop:
            return

        report = {
            "operation": "classify_features_dt_v1",
            "folder": folder,
            "models_folder": models_folder,
            "features_file": features_file,
            "available_features": avail_features_list,
            "models_discovered": len(model_details),
            "models_eligible_any": len(eligible_any),
            "min_models": min_models,
            "per_file": per_file,
            "batch": batch,
        }

        out_path = os.path.join(folder, "classification_report.json")
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            self.logger.info(f"Wrote classification report: {out_path}")
        except Exception as e:
            self.logger.warning(f"Failed writing classification_report.json: {e!r}")

        self.logger.info(f"DT batch: label={batch.get('label')}, confidence={batch.get('confidence')}")
        return


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def _main():
        op = OperationMain(
            node_uid="test-node",
            logger=logging.getLogger("dt_classify_test"),
            folder="/tmp/some_artifact_folder",
            models_folder="/tmp/decision_tree_models",
        )
        await op.run()

    asyncio.run(_main())
