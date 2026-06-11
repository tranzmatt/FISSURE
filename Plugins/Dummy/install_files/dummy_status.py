#! /usr/bin/env python3
"""Dummy Status Operation

Cycles node status through several states, then completes.

Modernized:
- UI schema params passed into __init__ (OperationMain(**params))
- Early normalization + clamping
- Python 3.8-safe typing
"""

import asyncio
import logging
import os
import sys
from typing import Any, Callable, Union

try:
    from fissure.utils.plugins.operations import Operation
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
    from fissure.utils.plugins.operations import Operation


def _to_float(v: Any, default: float) -> float:
    try:
        if v is None:
            return float(default)
        return float(v)
    except Exception:
        return float(default)


def _to_str(v: Any, default: str) -> str:
    if v is None:
        return default
    s = str(v).strip()
    return s if s else default


def _clamp(x: float, lo: float, hi: float) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


class OperationMain(Operation):
    """Dummy Status Operation"""

    def __init__(
        self,
        # --- parameters (from UI schema) ---
        profile: str = "phases",
        step_s: float = 2.0,
        description: str = "Dummy Status",
        # --- framework plumbing ---
        node_uid: str = "",
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback: Union[Callable, None] = None,
        status_callback: Union[Callable, None] = None,
        tak_cot_callback: Union[Callable, None] = None,
    ) -> None:
        super().__init__(
            node_uid=node_uid,
            logger=logger,
            alert_callback=alert_callback,
            status_callback=status_callback,
            tak_cot_callback=tak_cot_callback,
        )

        self.profile = _to_str(profile, "phases").lower()

        # Keep these bounded so the loop can't go pathological from bad inputs
        self.step_s = _clamp(_to_float(step_s, 2.0), 0.1, 60.0)
        self.tick_s = min(0.1, self.step_s)
        self.description = _to_str(description, "Dummy Status")

        # Ensure tick isn't longer than step (otherwise you might never update inside the window)
        if self.tick_s > self.step_s:
            self.tick_s = self.step_s

        self.logger.info(
            "dummy_status init params: "
            f"profile={self.profile}, step_s={self.step_s}, tick_s={self.tick_s}, "
            f"description={self.description}"
        )

        self.resource_args = {}

    def _build_statuses(self) -> list:
        # Keep simple; return list[str] but avoid typing that breaks older environments.
        if self.profile == "processing":
            return ["Processing", "Finalizing", "Complete"]
        if self.profile == "busy":
            return ["Running", "Busy", "Still Busy", "Done"]
        if self.profile == "idle":
            return ["Idle", "Idle", "Idle"]
        # default: phases
        return ["Running: Phase 1", "Running: Phase 2", "Processing", "Finalizing"]

    async def run(self) -> None:
        statuses = self._build_statuses()

        for s in statuses:
            if self._stop:
                break

            if self.status_callback:
                await self.status_callback(s)

            end_time = asyncio.get_event_loop().time() + self.step_s
            while not self._stop and asyncio.get_event_loop().time() < end_time:
                await asyncio.sleep(self.tick_s)


if __name__ == "__main__":
    from fissure.utils.plugins.test_operation import run_test

    run_test(OperationMain, {}, {})