#! /usr/bin/env python3
"""Dummy Alert
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import ctypes
import logging
import os
import sys
from typing import Any, Callable, Dict, Union

try:
    from fissure.utils.plugins.operations import Operation
except ImportError:
    # add fissure to path and import modules
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
    from fissure.utils.plugins.operations import Operation

import time
import json


class OperationMain(Operation):
    """Dummy Alert"""

    def __init__(
        self,
        period_s: float = 60.0,
        uid: str = "dummy_alert",
        description: str = "Periodic dummy alert",
        plot_pin: Union[bool, str] = True,
        node_uid: str = "",
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback: Union[Callable, None] = None,
        tak_cot_callback: Union[Callable, None] = None,
    ) -> None:
        super().__init__(
            node_uid=node_uid,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
        )

        # parameters (from UI schema)
        self.period_s = float(period_s)
        self.uid = uid or "dummy_alert"
        self.description = description or "Periodic dummy alert"
        self.plot_pin = self._to_bool(plot_pin)

        self.logger.info(
            f"dummy_alert init params: period_s={self.period_s}, uid={self.uid}, "
            f"description={self.description}, plot_pin={self.plot_pin}"
        )

    @staticmethod
    def _to_bool(value: Union[bool, str, int, None]) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return True
        if isinstance(value, (int, float)):
            return bool(value)

        value_str = str(value).strip().lower()
        return value_str in ("true", "1", "yes", "y", "on")

    async def run(self) -> None:
        while not self._stop:
            now_text = str(time.time())
            alert_text = f"Dummy Alert: {now_text}"

            await self.alert_callback(self.node_uid, self.opid, alert_text, self.logger)

            if self.plot_pin:
                msg_type = "pin"
                tak_icon = "a-h-G-E-S"
            else:
                msg_type = "event"
                tak_icon = "b-t-f-r"

            tak_msg = {
                "msg_type": msg_type,
                "uid": self.uid,
                "remarks": json.dumps({"timestamp": now_text}),
                "lat": True,
                "lon": True,
                "alt": True,
                "time": True,
                "tak_icon": tak_icon,
                "opid": self.opid,
                "alert_kind": "dummy_alert",
                "alert_summary": "Dummy alert",
            }
            await self.tak_cot_callback(tak_msg)

            end_time = time.time() + self.period_s
            while not self._stop and time.time() < end_time:
                await asyncio.sleep(0.25)

        self.logger.info("Dummy Alert exiting (stop requested).")


if __name__ == "__main__":
    """Run as standalone script for testing.
    """
    from fissure.utils.plugins.test_operation import run_test
    run_test(OperationMain, {}, {})