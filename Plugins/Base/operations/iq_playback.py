#! /usr/bin/env python3
"""IQ Playback Operation

IQ playback operation for the Base plugin.

Assumptions:
  - Playback file already exists on the executing Sensor Node for node_path mode.
  - transfer mode is reserved for the Dashboard slot to stage a file before
    launching this operation. This operation does not transfer files.
  - B2x0/B20xmini playback flow graph files are under:
      Plugins/Base/flow_graphs/iq_playback_flow_graphs/<maint-version>/b2x0/
  - Supported first-pass graphs:
      iq_playback_b2x0
      iq_playback_single_b2x0
"""

import asyncio
import importlib.util
import logging
import os
import sys
import uuid
from typing import Callable, Union


PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FISSURE_ROOT = os.path.abspath(os.path.join(PLUGIN_ROOT, "..", ".."))

for path in (FISSURE_ROOT, PLUGIN_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from fissure.utils.plugins.operations import Operation
from fissure.utils import get_library_version


class OperationMain(Operation):
    """IQ Playback Operation"""

    def __init__(
        self,
        operation_id: str = "",
        requester: str = "",
        flow_graph_name: str = "iq_playback_b2x0",
        playback_file_mode: str = "node_path",
        filepath: str = "",

        hardware_display_name: str = "",
        hardware_type: str = "",
        hardware_uuid: str = "",
        hardware_radio_name: str = "",
        hardware_serial: str = "",
        hardware_serial_argument: str = "False",
        hardware_interface: str = "",
        hardware_ip: str = "",
        hardware_daughterboard: str = "",

        tx_frequency: Union[str, float] = 915.0,
        tx_channel: str = "A:A",
        tx_antenna: str = "TX/RX",
        tx_gain: Union[str, float] = 70.0,
        sample_rate_msps: Union[str, float] = 1.0,
        data_type: str = "Complex Float 32",
        description: str = "IQ playback",

        node_uid: str = "",
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback: Union[Callable, None] = None,
        tak_cot_callback: Union[Callable, None] = None,
        status_callback: Union[Callable, None] = None,
        target_callback: Union[Callable, None] = None,
        soi_callback: Union[Callable, None] = None,
        artifact_manager=None,
    ) -> None:
        super().__init__(
            node_uid=node_uid,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
            status_callback=status_callback,
            target_callback=target_callback,
            soi_callback=soi_callback,
            artifact_manager=artifact_manager,
        )

        self.operation_id = str(operation_id or self.opid or uuid.uuid4())
        self.requester = str(requester or "").strip()

        self.flow_graph_name = str(flow_graph_name or "iq_playback_b2x0").strip()
        self.playback_file_mode = str(playback_file_mode or "node_path").strip().lower()
        self.filepath = str(filepath or "").strip()

        self.hardware_display_name = str(hardware_display_name or "").strip()
        self.hardware_type = str(hardware_type or "").strip()
        self.hardware_uuid = str(hardware_uuid or "").strip()
        self.hardware_radio_name = str(hardware_radio_name or "").strip()
        self.hardware_serial = str(hardware_serial or "").strip()
        self.hardware_serial_argument = str(hardware_serial_argument or "False").strip()
        self.hardware_interface = str(hardware_interface or "").strip()
        self.hardware_ip = str(hardware_ip or "").strip()
        self.hardware_daughterboard = str(hardware_daughterboard or "").strip()

        self.tx_frequency = self._float(tx_frequency, 915)
        self.tx_channel = str(tx_channel or "A:A").strip()
        self.tx_antenna = str(tx_antenna or "TX/RX").strip()
        self.tx_gain = self._float(tx_gain, 70.0)
        self.sample_rate_msps = self._float(sample_rate_msps, 1.0)
        self.data_type = str(data_type or "Complex Float 32").strip()
        self.description = str(description or "IQ playback").strip()

        self.logger.info(
            "iq_playback init params: "
            f"operation_id={self.operation_id}, "
            f"requester={self.requester}, "
            f"flow_graph_name={self.flow_graph_name}, "
            f"playback_file_mode={self.playback_file_mode}, "
            f"filepath={self.filepath}, "
            f"hardware_type={self.hardware_type}, "
            f"hardware_serial_argument={self.hardware_serial_argument}, "
            f"tx_frequency={self.tx_frequency}, "
            f"tx_channel={self.tx_channel}, "
            f"tx_antenna={self.tx_antenna}, "
            f"sample_rate_msps={self.sample_rate_msps}, "
            f"tx_gain={self.tx_gain}, "
            f"data_type={self.data_type}"
        )

    async def run(self) -> None:
        """Run IQ playback."""

        try:
            self._validate()

            if self.status_callback:
                await self.status_callback("Running: IQ Playback")

            await self._play_file()

        except asyncio.CancelledError:
            self.logger.info("iq_playback cancelled")
            raise

        except Exception:
            self.logger.exception("iq_playback failed")
            raise

        finally:
            if self.status_callback:
                try:
                    await self.status_callback("Idle")
                except Exception:
                    self.logger.exception("iq_playback status_callback failed while setting Idle")

    def _validate(self) -> None:
        if self.flow_graph_name not in {
            "iq_playback_b2x0",
            "iq_playback_single_b2x0",
        }:
            raise RuntimeError(
                f"Unsupported IQ playback flow graph for first pass: {self.flow_graph_name}"
            )

        if self.hardware_type not in {"USRP B20xmini", "USRP B2x0"}:
            raise RuntimeError(
                f"Unsupported IQ playback hardware for first pass: {self.hardware_type}"
            )

        if self.playback_file_mode not in {"node_path", "transfer"}:
            raise RuntimeError(
                f"Unsupported playback_file_mode: {self.playback_file_mode}"
            )

        if not self.filepath:
            raise RuntimeError("IQ playback requires filepath")

        if self.playback_file_mode == "transfer":
            self.logger.warning(
                "iq_playback received playback_file_mode=transfer. "
                "The file must already have been staged by the caller before this operation starts."
            )

        if not os.path.isfile(self.filepath):
            raise FileNotFoundError(
                f"IQ playback file not found on executing node: {self.filepath}"
            )

        data_type_key = str(self.data_type or "").strip().lower()
        supported_complex_types = {
            "complex",
            "complex float 32",
            "complex float32",
            "cf32",
            "fc32",
            "gr_complex",
        }

        if data_type_key not in supported_complex_types:
            raise RuntimeError(
                f"Unsupported IQ playback data_type for first pass: {self.data_type}"
            )

        self.data_type = "Complex Float 32"

    async def _play_file(self) -> None:
        module_path = self._resolve_flow_graph_path()
        module = self._load_module(module_path)

        top_block_cls = getattr(module, self.flow_graph_name)

        self.logger.info(f"Starting IQ playback flow graph: {module_path}")

        tb = top_block_cls(
            filepath=self.filepath,
            serial=self.hardware_serial_argument,
            tx_channel=self.tx_channel,
            tx_frequency=self.tx_frequency,
            sample_rate=self.sample_rate_msps,
            tx_gain=self.tx_gain,
            tx_antenna=self.tx_antenna,
            ip_address=self.hardware_ip,
        )

        loop = asyncio.get_running_loop()
        wait_future = None

        try:
            tb.start()
            wait_future = loop.run_in_executor(None, tb.wait)

            while not getattr(self, "_stop", False):
                if wait_future.done():
                    await wait_future
                    break

                await asyncio.sleep(0.1)

        finally:
            self.logger.info("Stopping IQ playback flow graph...")

            try:
                tb.stop()
            except Exception:
                self.logger.exception("iq_playback tb.stop failed")

            if wait_future is not None:
                try:
                    await asyncio.wait_for(wait_future, timeout=5.0)
                except asyncio.TimeoutError:
                    self.logger.warning("iq_playback flow graph wait timed out after stop")
                except Exception:
                    self.logger.exception("iq_playback wait_future failed after stop")

            try:
                tb.wait()
            except Exception:
                pass

            self.logger.info("IQ playback flow graph stopped.")

    def _resolve_flow_graph_path(self) -> str:
        version = get_library_version() or "maint-3.10"
        hardware_dir = "b2x0"

        path = os.path.join(
            PLUGIN_ROOT,
            "flow_graphs",
            "iq_playback_flow_graphs",
            version,
            hardware_dir,
            f"{self.flow_graph_name}.py",
        )

        if not os.path.isfile(path):
            raise FileNotFoundError(f"IQ playback flow graph not found: {path}")

        return path

    def _load_module(self, path: str):
        module_name = f"fissure_plugin_iq_playback_{uuid.uuid4().hex}"
        module_dir = os.path.dirname(path)

        if module_dir not in sys.path:
            sys.path.insert(0, module_dir)

        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load flow graph module: {path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        return module

    @staticmethod
    def _float(value, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)


if __name__ == "__main__":
    from fissure.utils.plugins.test_operation import run_test

    run_test(OperationMain, {}, {})