#! /usr/bin/env python3
"""
CoT Types Painter (catalog mode)

Modernized:
- Adds a minimal WinTAK-facing control surface:
    - scope: all / a-* / b-*
    - limit_mode: all / first_n (+ first_n)
    - expand_dots: yes/no
- Keeps the heavy layout/expansion tuning internal (still overridable via params for power users)
- Python 3.8-safe typing
"""

import os
import re
import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import Any, Callable, Dict, Union, List, Tuple, Optional

try:
    from fissure.utils.plugins.operations import Operation
except ImportError:
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from fissure.utils.plugins.operations import Operation


def _to_str(v: Any, default: str) -> str:
    if v is None:
        return default
    s = str(v).strip()
    return s if s else default


def _to_int(v: Any, default: int) -> int:
    try:
        if v is None:
            return int(default)
        return int(float(v))
    except Exception:
        return int(default)


def _to_bool_yn(v: Any, default: bool = True) -> bool:
    if v is None:
        return default
    s = str(v).strip().lower()
    if s in ("1", "true", "t", "yes", "y", "on"):
        return True
    if s in ("0", "false", "f", "no", "n", "off"):
        return False
    return default


def _clamp_int(x: int, lo: int, hi: int) -> int:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def read_cot_types_xml(path: str) -> List[str]:
    tree = ET.parse(path)
    root = tree.getroot()
    types: List[str] = []
    for e in root.findall(".//cot"):
        v = e.attrib.get("cot")
        if v:
            types.append(v.strip())

    seen = set()
    out: List[str] = []
    for t in types:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def sanitize_uid_component(s: str) -> str:
    safe = []
    for ch in s:
        if ch.isalnum() or ch in ("-", "_", "."):
            safe.append(ch)
        else:
            safe.append("_")
    out = "".join(safe)
    return out[:180] if len(out) > 180 else out


def _wrap_lon(lon: float) -> float:
    x = (lon + 180.0) % 360.0
    return x - 180.0


def _clamp_lat(lat: float) -> float:
    return max(-89.5, min(89.5, lat))


def _split_cot(cot_type: str) -> List[str]:
    return cot_type.split("-") if cot_type else []


def _infer_affiliation(cot_type: str) -> str:
    parts = _split_cot(cot_type)
    return parts[1] if len(parts) > 1 else "x"


def _short_callsign(s: str, max_len: int = 24) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _uid_for_variant(uid_prefix: str, base_cot: str, variant_cot: str, v_idx: int) -> str:
    b = sanitize_uid_component(base_cot)
    v = sanitize_uid_component(variant_cot)
    return f"{uid_prefix}-{b}-v{v_idx:03d}-{v}"


def _callsign_for_variant(variant_cot: str) -> str:
    aff = _infer_affiliation(variant_cot)
    return f"{_short_callsign(variant_cot, 20)}:{aff}"


def _expand_dots_in_segment(seg: str, repl: List[str], cap_guard: int) -> List[str]:
    if "." not in seg:
        return [seg]

    out = [""]
    for ch in seg:
        if ch != ".":
            out = [p + ch for p in out]
            continue

        nxt: List[str] = []
        for p in out:
            for r in repl:
                nxt.append(p + r)
                if len(nxt) >= cap_guard:
                    return nxt
        out = nxt

    return out


def expand_cot_type_dots(
    cot_type: str,
    segment_dot_sets: Dict[int, List[str]],
    fallback_dot_set: List[str],
    max_variants_per_base: int,
) -> List[str]:
    parts = _split_cot(cot_type)
    if not parts:
        return [cot_type]

    seg_expansions: List[List[str]] = []
    for seg_idx, seg in enumerate(parts):
        repl = segment_dot_sets.get(seg_idx, fallback_dot_set)
        seg_exp = _expand_dots_in_segment(seg, repl, cap_guard=max_variants_per_base)
        seg_expansions.append(seg_exp)

    out: List[str] = [""]
    for seg_idx, seg_opts in enumerate(seg_expansions):
        nxt: List[str] = []
        for prefix in out:
            for opt in seg_opts:
                candidate = opt if seg_idx == 0 else prefix + "-" + opt
                nxt.append(candidate)
                if len(nxt) >= max_variants_per_base:
                    return nxt
        out = nxt

    return out


class OperationMain(Operation):
    def __init__(
        self,
        # --- UI schema params ---
        scope: str = "b-*",
        limit_mode: str = "first_n",
        first_n: int = 5,
        expand_dots: Union[str, bool] = "no",
        base_lat: float = 40.703052,
        base_lon: float = -74.016991,
        delay_s: float = 0.05,
        description: str = "Dummy CoT Types",
        # --- framework plumbing ---
        node_uid: str = "",
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback: Union[Callable, None] = None,
        tak_cot_callback: Union[Callable, None] = None,
        status_callback: Union[Callable, None] = None,
        target_callback: Union[Callable, None] = None,
        artifact_manager=None,
    ) -> None:
        super().__init__(
            node_uid=node_uid,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
            status_callback=status_callback,
            target_callback=target_callback,
            artifact_manager=artifact_manager,
        )

        # ---- normalize UI params ----
        self.scope = _to_str(scope, "b-*").lower()
        if self.scope not in ("all", "a-*", "b-*"):
            self.scope = "b-*"

        self.limit_mode = _to_str(limit_mode, "first_n").lower()
        if self.limit_mode not in ("all", "first_n"):
            self.limit_mode = "first_n"

        self.first_n = _clamp_int(_to_int(first_n, 5), 1, 5000)
        self.expand_dots = _to_bool_yn(expand_dots, False)
        self.description = _to_str(description, "Dummy CoT Types")

        # ---- existing defaults (power-user tunables remain supported via self.parameters) ----
        here = os.path.dirname(os.path.abspath(__file__))
        self.cottypes_path = os.path.join(here, "CoTtypes.xml")
        self.match_regex = r"^"

        self.emit_all_groups = True
        self.group_size = 200
        self.groups_limit = 0
        self.emit_block_headers = True

        self.base_lat = float(base_lat)
        self.base_lon = float(base_lon)

        self.delay_s = float(delay_s)
        self.uid_prefix = "cot"

        self.affiliation_set = ["f", "u", "n", "h"]
        self.battle_dimension_set = ["P", "A", "G", "S", "U", "F", "Z"]
        self.fallback_dot_set = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
        self.max_variants_per_base = 64

        self.start_lat: Optional[float] = None
        self.start_lon: Optional[float] = None

        self.item_lat_step_deg = 0.06
        self.item_lon_step_deg = 0.08

        self.block_lat_gap_deg = 1.80
        self.block_lon_gap_deg = 2.40

        self.block_item_cols = 10
        self.block_item_rows = 10
        self.blocks_per_row = 6

        self.wrap_longitude = True
        self.clamp_latitude = True

        self.segment_dot_sets: Dict[int, List[str]] = {}

        self.logger.info(
            f"dummy_cot_types init: scope={self.scope}, limit_mode={self.limit_mode}, "
            f"first_n={self.first_n}, expand_dots={self.expand_dots}"
        )

        self.resource_args = {}

    def _apply_parameters(self) -> None:
        """
        Power-user overrides (kept for dev/testing). UI schema does NOT expose these,
        but callers can still pass them in JSON if needed.
        """
        p = getattr(self, "parameters", None)
        if not isinstance(p, dict):
            return

        self.cottypes_path = p.get("cottypes_path", self.cottypes_path)
        self.match_regex = p.get("match_regex", self.match_regex)

        # batching / blocks
        self.emit_all_groups = bool(p.get("emit_all_groups", self.emit_all_groups))
        self.group_size = int(p.get("group_size", self.group_size))
        self.groups_limit = int(p.get("groups_limit", self.groups_limit))
        self.emit_block_headers = bool(p.get("emit_block_headers", self.emit_block_headers))

        # base location
        self.base_lat = float(p.get("base_lat", self.base_lat))
        self.base_lon = float(p.get("base_lon", self.base_lon))

        # emission
        self.delay_s = float(p.get("delay_s", self.delay_s))
        self.uid_prefix = p.get("uid_prefix", self.uid_prefix)

        # expansion tuning
        self.max_variants_per_base = int(p.get("max_variants_per_base", self.max_variants_per_base))

        affs = p.get("affiliation_set", None)
        if isinstance(affs, list) and affs and all(isinstance(x, str) for x in affs):
            self.affiliation_set = affs

        bds = p.get("battle_dimension_set", None)
        if isinstance(bds, list) and bds and all(isinstance(x, str) for x in bds):
            self.battle_dimension_set = bds

        fbs = p.get("fallback_dot_set", None)
        if isinstance(fbs, list) and fbs and all(isinstance(x, str) for x in fbs):
            self.fallback_dot_set = fbs

        self.start_lat = p.get("start_lat", self.start_lat)
        self.start_lon = p.get("start_lon", self.start_lon)
        if self.start_lat is not None:
            self.start_lat = float(self.start_lat)
        if self.start_lon is not None:
            self.start_lon = float(self.start_lon)

        self.item_lat_step_deg = float(p.get("item_lat_step_deg", self.item_lat_step_deg))
        self.item_lon_step_deg = float(p.get("item_lon_step_deg", self.item_lon_step_deg))

        self.block_lat_gap_deg = float(p.get("block_lat_gap_deg", self.block_lat_gap_deg))
        self.block_lon_gap_deg = float(p.get("block_lon_gap_deg", self.block_lon_gap_deg))

        self.block_item_cols = int(p.get("block_item_cols", self.block_item_cols))
        self.block_item_rows = int(p.get("block_item_rows", self.block_item_rows))
        self.blocks_per_row = int(p.get("blocks_per_row", self.blocks_per_row))

        self.wrap_longitude = bool(p.get("wrap_longitude", self.wrap_longitude))
        self.clamp_latitude = bool(p.get("clamp_latitude", self.clamp_latitude))

        # segment_dot_sets override (expects dict like {1:["f","u"], 2:["G","A"]})
        sds = p.get("segment_dot_sets", None)
        if isinstance(sds, dict):
            cleaned: Dict[int, List[str]] = {}
            for k, v in sds.items():
                try:
                    ik = int(k)
                except Exception:
                    continue
                if isinstance(v, list) and v and all(isinstance(x, str) for x in v):
                    cleaned[ik] = v
            self.segment_dot_sets = cleaned

    def _merged_segment_dot_sets(self) -> Dict[int, List[str]]:
        merged: Dict[int, List[str]] = {1: self.affiliation_set, 2: self.battle_dimension_set}
        for k, v in (self.segment_dot_sets or {}).items():
            merged[k] = v
        return merged

    def _effective_regex(self) -> str:
        """
        Combine scope selection with match_regex safely.
        Scope affects only the prefix (a-/b-); match_regex can further refine.
        """
        scope_rx = r"^"
        if self.scope == "a-*":
            scope_rx = r"^a-"
        elif self.scope == "b-*":
            scope_rx = r"^b-"

        # If user also provided match_regex, intersect by requiring both.
        # We do it by filtering in code, so just return scope_rx and keep match_regex separately.
        return scope_rx

    async def _emit_pin(
        self,
        uid: str,
        cot_type: str,
        lat: float,
        lon: float,
        callsign: str,
        stale_s: float = 7200.0,
    ) -> None:
        msg: Dict[str, Any] = {
            "msg_type": "pin",
            "uid": uid,
            "tak_icon": cot_type,
            "callsign": callsign,
            "lat": float(lat),
            "lon": float(lon),
            "alt": 0.0,
            "time": True,
            "remarks": "",
            "stale": int(stale_s),
            "opid": self.opid,
        }
        await self.tak_cot_callback(msg)

    def _index_to_latlon(self, global_idx: int) -> Tuple[float, float, int, int, int, int]:
        start_lat = self.base_lat if self.start_lat is None else self.start_lat
        start_lon = self.base_lon if self.start_lon is None else self.start_lon

        cols = max(1, self.block_item_cols)
        rows = max(1, self.block_item_rows)
        slots_per_block = cols * rows

        block_idx = global_idx // slots_per_block
        slot_idx = global_idx % slots_per_block

        inblock_r = slot_idx // cols
        inblock_c = slot_idx % cols

        bpr = max(1, self.blocks_per_row)
        block_row = block_idx // bpr
        block_col = block_idx % bpr

        checker_lon_offset = (self.item_lon_step_deg * 0.5) if (inblock_r % 2 == 1) else 0.0

        lat = start_lat - (block_row * self.block_lat_gap_deg) - (inblock_r * self.item_lat_step_deg)
        lon = start_lon + (block_col * self.block_lon_gap_deg) + (inblock_c * self.item_lon_step_deg) + checker_lon_offset

        if self.clamp_latitude:
            lat = _clamp_lat(lat)
        if self.wrap_longitude:
            lon = _wrap_lon(lon)

        return lat, lon, block_idx, inblock_r, inblock_c, slot_idx

    async def _emit_block_header(self, block_idx: int, group_meta: Dict[str, Any]) -> None:
        cols = max(1, self.block_item_cols)
        first_global_idx = block_idx * (cols * max(1, self.block_item_rows))
        lat, lon, *_ = self._index_to_latlon(first_global_idx)
        lat = lat + (self.item_lat_step_deg * 0.35)
        lon = lon - (self.item_lon_step_deg * 0.35)
        if self.clamp_latitude:
            lat = _clamp_lat(lat)
        if self.wrap_longitude:
            lon = _wrap_lon(lon)

        uid = f"{self.uid_prefix}-BLOCK-{block_idx:04d}"
        cot_type = "a-f-G"
        callsign = f"BLOCK {block_idx:04d}"
        await self._emit_pin(uid, cot_type, lat, lon, callsign, stale_s=7200.0)

    async def _emit_catalog_for_group(self, base_types: List[str], group_meta: Dict[str, Any]) -> None:
        seg_sets = self._merged_segment_dot_sets()

        flat: List[Tuple[str, str, int]] = []
        for base in base_types:
            if self.expand_dots:
                variants = expand_cot_type_dots(
                    base,
                    segment_dot_sets=seg_sets,
                    fallback_dot_set=self.fallback_dot_set,
                    max_variants_per_base=max(1, self.max_variants_per_base),
                )
            else:
                variants = [base]
            for v_idx, v in enumerate(variants):
                flat.append((base, v, v_idx))

        cols = max(1, self.block_item_cols)
        rows = max(1, self.block_item_rows)
        slots_per_block = cols * rows
        blocks_needed = (len(flat) + slots_per_block - 1) // slots_per_block

        group_id = int(group_meta.get("group", 0))
        base_block_idx = group_id * max(1, blocks_needed)

        if self.emit_block_headers:
            for b in range(blocks_needed):
                if self._stop:
                    break
                await self._emit_block_header(base_block_idx + b, group_meta)

        painted = 0
        for j, (base, variant, v_idx) in enumerate(flat):
            if self._stop:
                break

            global_idx = (base_block_idx * slots_per_block) + j
            lat, lon, block_idx, in_r, in_c, slot_idx = self._index_to_latlon(global_idx)

            uid = _uid_for_variant(self.uid_prefix, base, variant, v_idx)
            callsign = _callsign_for_variant(variant)

            await self._emit_pin(uid, variant, lat, lon, callsign, stale_s=7200.0)
            painted += 1

            if self.delay_s > 0:
                await asyncio.sleep(self.delay_s)

            if self.status_callback and (painted % 50 == 0):
                try:
                    await self.status_callback(f"Group {group_id}: painted {painted}/{len(flat)} variants")
                except Exception:
                    pass

        if self.status_callback:
            try:
                await self.status_callback(f"Group {group_meta.get('group', 0)} complete ({painted} pins)")
            except Exception:
                pass

    async def run(self) -> None:
        self._apply_parameters()

        if not self.tak_cot_callback:
            raise RuntimeError("dummy_cot_types requires tak_cot_callback to be wired")

        if not os.path.exists(self.cottypes_path):
            raise FileNotFoundError(f"CoTtypes.xml not found: {self.cottypes_path}")

        all_types = read_cot_types_xml(self.cottypes_path)

        scope_rx = re.compile(self._effective_regex())
        user_rx = re.compile(self.match_regex) if self.match_regex else re.compile(r"^")

        types = [t for t in all_types if scope_rx.search(t) and user_rx.search(t)]

        # Apply UI limit (first_n) if requested
        if self.limit_mode == "first_n":
            types = types[: self.first_n]

        self.logger.info(
            "cot_catalog: matched=%d scope=%s limit_mode=%s first_n=%d expand_dots=%s max_variants_per_base=%d group_size=%d",
            len(types), self.scope, self.limit_mode, self.first_n, self.expand_dots, self.max_variants_per_base, self.group_size
        )

        if not self.emit_all_groups:
            meta = {"group": 0, "start_index": 0, "end_index": len(types) - 1, "regex": self.match_regex}
            await self._emit_catalog_for_group(types, meta)
            if self.status_callback:
                try:
                    await self.status_callback("Idle")
                except Exception:
                    pass
            return

        gs = max(1, self.group_size)
        total = len(types)
        num_groups = (total + gs - 1) // gs
        if self.groups_limit and self.groups_limit > 0:
            num_groups = min(num_groups, self.groups_limit)

        for g in range(num_groups):
            if self._stop:
                break
            start = g * gs
            end = min(total, start + gs)
            batch = types[start:end]
            meta = {"group": g, "start_index": start, "end_index": end - 1, "regex": self.match_regex}
            await self._emit_catalog_for_group(batch, meta)

        if self.status_callback:
            try:
                await self.status_callback("Idle")
            except Exception:
                pass


if __name__ == "__main__":
    from fissure.utils.plugins.test_operation import run_test
    run_test(OperationMain, {}, {})