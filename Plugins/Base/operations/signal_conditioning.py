#!/usr/bin/env python3
"""
Signal Conditioning Operation

This operation:
1. Runs the normal_decay GNU Radio flow graph helper.
2. Captures up to N burst IQ files (variable length).
3. Stops when either N files exist on disk or stop is requested.
4. Ensures the selected files have fully settled (no longer growing) before
   downstream metadata (size/checksum/etc.) is computed.
5. Publishes artifact metadata that later SOI workflow stages can attach to
   the promoted SOI record.
"""

import os
import sys
import time
import json
import shutil
import hashlib
import asyncio
import logging
import inspect
from typing import Any, Callable, Dict, List, Optional

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


# -----------------------------
# Utility helpers
# -----------------------------

def list_files(path: str) -> Dict[str, os.stat_result]:
    """
    Return {filename: os.stat_result} for regular files under `path`.
    """
    out: Dict[str, os.stat_result] = {}
    try:
        for filename in os.listdir(path):
            full_path = os.path.join(path, filename)
            if os.path.isfile(full_path):
                out[filename] = os.stat(full_path)
    except FileNotFoundError:
        return {}
    return out


def is_file_stable(prev: os.stat_result, cur: os.stat_result, settle_seconds: float) -> bool:
    """
    A file is considered stable if:
      - size has not changed between observations
      - mtime has not changed between observations
      - it has not been modified in at least `settle_seconds`
    """
    return (
        prev.st_size == cur.st_size
        and prev.st_mtime == cur.st_mtime
        and (time.time() - cur.st_mtime) >= settle_seconds
    )


def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    """
    Compute a SHA-256 checksum for a file.
    """
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


async def maybe_await(value: Any) -> Any:
    """
    Await coroutine-like values while allowing normal synchronous returns.
    """
    if inspect.isawaitable(value):
        return await value
    return value


async def invoke_callback(callback: Optional[Callable], *args: Any, timeout: float = 2.0, **kwargs: Any) -> Any:
    """
    Invoke a callback with a bounded await when possible.
    """
    if not callback:
        return None

    result = callback(*args, **kwargs)
    if inspect.isawaitable(result):
        return await asyncio.wait_for(result, timeout=timeout)
    return result


async def drain_stream(stream: Optional[asyncio.StreamReader], logger: logging.Logger, label: str) -> None:
    """
    Drain a subprocess stream so the child cannot block on a full pipe.
    """
    if stream is None:
        return

    try:
        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode(errors="ignore").rstrip()
            if text:
                logger.warning("%s: %s", label, text)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Failed while draining %s", label)


async def cancel_task(task: Optional[asyncio.Task], logger: logging.Logger, name: str) -> None:
    """
    Cancel and await a task cleanly.
    """
    if task is None or task.done():
        return

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("%s failed during cancellation", name)


async def terminate_process(proc: Optional[asyncio.subprocess.Process], logger: logging.Logger) -> None:
    """
    Terminate a subprocess, then kill it if it does not exit promptly.
    """
    if proc is None or proc.returncode is not None:
        return

    proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        logger.warning("Flow graph helper did not terminate quickly; killing it.")
        proc.kill()
        await proc.wait()


async def wait_for_files_to_settle(
    paths: List[str],
    settle_seconds: float,
    max_wait: Optional[float],
    poll: float,
    logger: Optional[logging.Logger] = None,
    stop_check: Optional[Callable[[], bool]] = None,
) -> Dict[str, os.stat_result]:
    """
    Wait until all provided file paths are stable or return best-effort stats
    when stop/max_wait ends the settle window.
    """
    start = time.time()
    last_stats: Dict[str, os.stat_result] = {}
    stable_since: Dict[str, Optional[float]] = {path: None for path in paths}
    done = set()

    while len(done) < len(paths):
        now = time.time()

        if stop_check and stop_check():
            if logger:
                logger.info("Stop requested during settle; exiting settle early.")
            break

        if max_wait is not None and (now - start) > max_wait:
            if logger:
                logger.warning("Settle max_wait exceeded; returning best-effort stats.")
            break

        for path in paths:
            if path in done:
                continue

            try:
                stat = os.stat(path)
            except FileNotFoundError:
                stable_since[path] = None
                continue

            prev = last_stats.get(path)
            if prev is not None and is_file_stable(prev, stat, settle_seconds):
                if stable_since[path] is None:
                    stable_since[path] = now
                if (now - stable_since[path]) >= settle_seconds:
                    done.add(path)
            else:
                stable_since[path] = None

            last_stats[path] = stat

        await asyncio.sleep(poll)

    return last_stats


# -----------------------------
# Operation implementation
# -----------------------------

class OperationMain(Operation):
    """
    Signal Conditioning Operation

    Runs the promote-to-SOI signal conditioning capture stage and publishes
    artifact metadata for the files captured by normal_decay.py.
    """

    def __init__(
        self,
        node_uid: str = "",
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback=None,
        tak_cot_callback=None,
        frequency_mhz: Optional[float] = None,
        status_callback=None,
        source_id: Optional[str] = None,
        max_files: int = 5,
        sample_rate: str = "1e6",
        threshold: str = "0.004",
        decay: str = "0.0002",
        channel: str = "A:A",
        ip_address: str = "",
        serial: str = "False",
        antenna: str = "TX/RX",
        gain: str = "60",
    ):
        super().__init__(
            node_uid=node_uid,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
            status_callback=status_callback,
        )
        self.frequency_mhz = frequency_mhz
        self.source_id = source_id or node_uid or "sensor_node"
        self.max_files = int(max_files)
        self.sample_rate = str(sample_rate)
        self.threshold = str(threshold)
        self.decay = str(decay)
        self.channel = str(channel)
        self.ip_address = str(ip_address)
        self.serial = str(serial)
        self.antenna = str(antenna)
        self.gain = str(gain)

        self.artifact_id = ""
        self.artifact_payload: Dict[str, Any] = {}
        self.selected_files: List[str] = []

    async def _set_status(self, status: str) -> None:
        if not getattr(self, "status_callback", None):
            return
        try:
            await invoke_callback(self.status_callback, status, timeout=2.0)
        except Exception:
            self.logger.exception("status_callback failed")

    async def _publish_alert(self, payload: Dict[str, Any]) -> None:
        if not getattr(self, "alert_callback", None):
            return
        try:
            await invoke_callback(self.alert_callback, payload, timeout=2.0)
        except Exception:
            self.logger.exception("alert_callback failed")

    async def _publish_tak_cot(self, payload: Dict[str, Any]) -> None:
        if not getattr(self, "tak_cot_callback", None):
            return
        try:
            await invoke_callback(self.tak_cot_callback, payload, timeout=2.0)
        except Exception:
            self.logger.exception("tak_cot_callback failed")

    async def _create_artifact(self, payload: Dict[str, Any]) -> str:
        """
        Use the operation artifact helper when one exists. Keep the payload on
        the instance either way so SOI orchestration can read it after run().
        """
        self.artifact_payload = payload

        artifact = None
        for method_name in (
            "create_artifact",
            "register_artifact",
            "add_artifact",
            "emit_artifact",
            "artifact_callback",
        ):
            method = getattr(self, method_name, None)
            if not method:
                continue

            try:
                artifact = await maybe_await(method(payload))
                break
            except TypeError:
                try:
                    artifact = await maybe_await(method(**payload))
                    break
                except TypeError:
                    continue
            except Exception:
                self.logger.exception("%s failed", method_name)
                break

        artifact_id = getattr(artifact, "id", artifact) if artifact else ""
        if artifact_id:
            self.artifact_id = str(artifact_id)
            self.artifact_payload["artifact_id"] = self.artifact_id
        else:
            # The artifacts/<opid>/files layout still gives downstream stages a
            # stable identifier even when this Operation base class does not
            # expose an artifact registration method.
            self.artifact_id = str(getattr(self, "opid", "") or "")
            self.artifact_payload["artifact_id"] = self.artifact_id

        return self.artifact_id

    def _build_artifact_payload(
        self,
        selected: List[str],
        final_stats: Dict[str, os.stat_result],
        output_dir: str,
    ) -> Dict[str, Any]:
        files: List[Dict[str, Any]] = []

        for filename in selected:
            full_path = os.path.join(output_dir, filename)
            stat = final_stats.get(full_path)
            if stat is None:
                try:
                    stat = os.stat(full_path)
                except FileNotFoundError:
                    self.logger.warning("Final artifact missing unexpectedly: %s", full_path)
                    continue

            checksum = ""
            try:
                checksum = sha256_file(full_path)
            except Exception:
                self.logger.exception("Failed to checksum artifact file: %s", full_path)

            files.append(
                {
                    "name": filename,
                    "path": full_path,
                    "relative_path": os.path.relpath(full_path, FISSURE_ROOT),
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "sha256": checksum,
                }
            )

        return {
            "kind": "artifact",
            "event_type": "signal_conditioning_artifact",
            "node_uid": self.node_uid,
            "source_id": self.source_id or self.node_uid or "sensor_node",
            "operation_id": getattr(self, "opid", ""),
            "artifact_id": getattr(self, "opid", ""),
            "artifact_type": "iq_capture",
            "artifact_format": "burst_iq_files",
            "name": "Signal Conditioning IQ Capture",
            "description": "Burst IQ files captured by the signal conditioning stage.",
            "frequency_mhz": self.frequency_mhz,
            "sample_rate": self.sample_rate,
            "output_dir": output_dir,
            "files_dir": output_dir,
            "file_count": len(files),
            "files": files,
        }

    def _normal_decay_path(self) -> str:
        return os.path.abspath(
            os.path.join(PLUGIN_ROOT, "scripts", "promote_to_soi_lib", "normal_decay.py")
        )

    def _build_command(self, python_path: str, flowgraph_path: str) -> List[str]:
        return [
            python_path,
            flowgraph_path,
            "--sample-rate", self.sample_rate,
            "--threshold", self.threshold,
            "--decay", self.decay,
            "--max-bursts", str(self.max_files),
            "--rx-freq", str(self.frequency_mhz),
            "--channel", self.channel,
            "--ip-address", self.ip_address,
            "--serial", self.serial,
            "--antenna", self.antenna,
            "--gain", self.gain,
        ]

    async def run(self) -> None:
        """
        Promote-to-SOI capture stage.
        """
        proc: Optional[asyncio.subprocess.Process] = None
        stderr_task: Optional[asyncio.Task] = None
        stop_reason = "unknown"

        try:
            if self.frequency_mhz is None:
                raise ValueError("Missing required parameter: frequency_mhz")

            if self.max_files <= 0:
                raise ValueError("max_files must be greater than zero")

            settle_poll = 0.10
            settle_seconds = 1.0
            settle_max_wait = None

            output_dir = os.path.join(FISSURE_ROOT, "artifacts", self.opid, "files")
            os.makedirs(output_dir, exist_ok=True)

            await self._set_status(f"Running: Capture @ {self.frequency_mhz:.3f} MHz")

            flowgraph_path = self._normal_decay_path()
            if not os.path.isfile(flowgraph_path):
                raise FileNotFoundError(f"normal_decay.py not found: {flowgraph_path}")

            python_path = shutil.which("python3") or shutil.which("python") or sys.executable
            cmd = self._build_command(python_path, flowgraph_path)

            self.logger.info("Flow graph argv: %r", cmd)
            self.logger.info("Output directory: %s", output_dir)

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=output_dir,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            stderr_task = asyncio.create_task(drain_stream(proc.stderr, self.logger, "normal_decay stderr"))

            known_files: Dict[str, os.stat_result] = {}
            stable_files = set()
            cap_selected: Optional[List[str]] = None
            cap_last: Optional[str] = None
            cap_wait_started: Optional[float] = None

            while True:
                now = time.time()

                if self._stop:
                    stop_reason = "stop_requested"
                    self.logger.info("Stop requested; exiting capture loop.")
                    break

                if proc.returncode is not None:
                    stop_reason = f"process_exited_{proc.returncode}"
                    self.logger.info("normal_decay exited with return code %s", proc.returncode)
                    break

                current = list_files(output_dir)
                file_count = len(current)
                prev_last = known_files.get(cap_last) if cap_last else None

                for filename, stat in current.items():
                    prev = known_files.get(filename)
                    if prev is not None and is_file_stable(prev, stat, settle_seconds):
                        if filename not in stable_files:
                            stable_files.add(filename)
                            self.logger.debug("File settled during capture: %s", filename)
                    known_files[filename] = stat

                if file_count >= self.max_files:
                    if cap_selected is None:
                        ordered = sorted(current.items(), key=lambda kv: (kv[1].st_mtime, kv[0]))
                        cap_selected = [filename for filename, _ in ordered[: self.max_files]]
                        cap_last = cap_selected[-1] if cap_selected else None
                        cap_wait_started = now
                        self.logger.info(
                            "Reached %s files; latched selection=%s. Waiting for last file to settle: %s",
                            file_count,
                            cap_selected,
                            cap_last,
                        )
                        prev_last = known_files.get(cap_last) if cap_last else None

                    if cap_last is None or cap_last not in current:
                        self.logger.warning("Latched last file missing (%s); re-latching selection.", cap_last)
                        cap_selected = None
                        cap_last = None
                        cap_wait_started = None
                        await asyncio.sleep(settle_poll)
                        continue

                    last_stat = current[cap_last]
                    if prev_last is not None and is_file_stable(prev_last, last_stat, settle_seconds):
                        stop_reason = "max_files_and_last_settled"
                        self.logger.info("Last file settled: %s. Stopping capture.", cap_last)
                        break

                    if settle_max_wait is not None and cap_wait_started is not None:
                        if (now - cap_wait_started) > settle_max_wait:
                            stop_reason = "max_files_settle_timeout"
                            self.logger.warning(
                                "Timed out waiting for last file to settle (%s); stopping anyway.",
                                cap_last,
                            )
                            break

                await asyncio.sleep(settle_poll)

            await terminate_process(proc, self.logger)
            await cancel_task(stderr_task, self.logger, "stderr drain task")

            if self._stop:
                self.logger.info("Stop requested; skipping post-capture settle stage.")
                return

            current = list_files(output_dir)
            if not current:
                self.logger.warning("No artifacts captured.")
                return

            ordered = sorted(current.items(), key=lambda kv: (kv[1].st_mtime, kv[0]))
            selected = [filename for filename, _ in ordered[: self.max_files]]
            selected_paths = [os.path.join(output_dir, filename) for filename in selected]
            self.selected_files = selected_paths

            final_stats = await wait_for_files_to_settle(
                selected_paths,
                settle_seconds=settle_seconds,
                max_wait=settle_max_wait,
                poll=settle_poll,
                logger=self.logger,
                stop_check=lambda: self._stop,
            )

            for filename in selected:
                full_path = os.path.join(output_dir, filename)
                stat = final_stats.get(full_path)
                if stat is not None:
                    self.logger.info("Final artifact: %s (size=%s bytes)", full_path, stat.st_size)
                else:
                    try:
                        stat2 = os.stat(full_path)
                        self.logger.info("Final artifact: %s (size=%s bytes)", full_path, stat2.st_size)
                    except FileNotFoundError:
                        self.logger.warning("Final artifact missing unexpectedly: %s", full_path)

            artifact_payload = self._build_artifact_payload(selected, final_stats, output_dir)
            artifact_id = await self._create_artifact(artifact_payload)
            artifact_payload["artifact_id"] = artifact_id
            self.artifact_payload = artifact_payload

            metadata_path = os.path.join(output_dir, "signal_conditioning_artifact.json")
            try:
                with open(metadata_path, "w", encoding="utf-8") as handle:
                    json.dump(artifact_payload, handle, indent=2, sort_keys=True)
                self.logger.info("Wrote signal conditioning artifact metadata: %s", metadata_path)
            except Exception:
                self.logger.exception("Failed to write signal conditioning artifact metadata")

            await self._publish_alert(artifact_payload)
            await self._publish_tak_cot(artifact_payload)

            self.logger.info(
                "Signal conditioning capture complete: artifact_id=%s file_count=%s stop_reason=%s",
                artifact_id,
                artifact_payload.get("file_count", 0),
                stop_reason,
            )

        finally:
            await terminate_process(proc, self.logger)
            await cancel_task(stderr_task, self.logger, "stderr drain task")
            await self._set_status("Idle")


if __name__ == "__main__":
    async def _main():
        logging.basicConfig(level=logging.INFO)
        op = OperationMain(
            node_uid="test-node",
            logger=logging.getLogger("signal_conditioning_test"),
            frequency_mhz=915.0,
        )
        await op.run()

    asyncio.run(_main())