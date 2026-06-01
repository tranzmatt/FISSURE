#! /usr/bin/env python3
"""Dummy Detection
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
    """Dummy Detection"""

    def __init__(
        self,
        period_s: float = 60.0,
        freq_mhz: float = 915.0,
        power_dbm: float = -40.0,
        description: str = "Periodic dummy detection",
        sensor_node_id: Union[int, str] = 0,
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback: Union[Callable, None] = None,
        tak_cot_callback: Union[Callable, None] = None,
    ) -> None:
        super().__init__(
            sensor_node_id=sensor_node_id,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
        )

        self.period_s = float(period_s)
        self.freq_mhz = float(freq_mhz)
        self.freq_hz = int(self.freq_mhz * 1_000_000.0)
        self.power_dbm = float(power_dbm)
        self.description = description or "Periodic dummy detection"

        self.logger.info(
            f"dummy_detection init params: period_s={self.period_s}, "
            f"freq_mhz={self.freq_mhz}, freq_hz={self.freq_hz}, "
            f"power_dbm={self.power_dbm}, description={self.description}"
        )

    async def run(self) -> None:
        """Periodic dummy detection event"""
        tick_s = 0.25
        cb_timeout_s = 2.0

        while not self._stop:
            ts = time.time()

            detection = {
                "event_type": "detection",
                "frequency_hz": int(self.freq_hz),
                "power_dbm": float(self.power_dbm),
                "timestamp": int(ts),
                "detector": "dummy_detection",
                "opid": self.opid,
            }

            if self.alert_callback:
                try:
                    await asyncio.wait_for(
                        self.alert_callback(
                            self.sensor_node_id,
                            self.opid,
                            f"Dummy detection @ {self.freq_mhz:g} MHz",
                            self.logger,
                        ),
                        timeout=cb_timeout_s,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    self.logger.exception("alert_callback failed")

            if self.tak_cot_callback:
                try:
                    await asyncio.wait_for(
                        self.tak_cot_callback(
                            {
                                "msg_type": "event",
                                "uid": f"dummy-detection-{int(ts)}",
                                "lat": True,
                                "lon": True,
                                "alt": True,
                                "time": True,
                                "data": detection,
                                "opid": self.opid,
                                "tak_icon": "r-x-fissure-detection",
                            }
                        ),
                        timeout=cb_timeout_s,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    self.logger.exception("tak_cot_callback failed")

            # interruptible sleep
            end_time = time.time() + self.period_s
            while not self._stop and time.time() < end_time:
                await asyncio.sleep(tick_s)

        self.logger.info("Dummy Detection exiting (stop requested).")



if __name__ == "__main__":
    """Run as standalone script for testing.
    """
    from fissure.utils.plugins.test_operation import run_test
    run_test(OperationMain, {}, {})