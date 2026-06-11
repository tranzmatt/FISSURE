#!/usr/bin/env python3
"""
Promote to SOI Operation

This operation:
1. Runs the normal_decay GNU Radio flowgraph.
2. Captures up to N burst IQ files (variable length).
3. Stops when either N files exist on disk or timeout occurs.
4. Ensures the selected files have fully settled (no longer growing) before
   downstream metadata (size/checksum/etc.) is computed.
"""

import os
import sys
import time
import asyncio
import logging
from typing import Dict, List, Optional

from fissure.utils.plugins.operations import Operation
from fissure.utils import FISSURE_ROOT

# -----------------------------
# Utility helpers
# -----------------------------

def list_files(path: str) -> Dict[str, os.stat_result]:
    """
    Returns {filename: os.stat_result} for regular files under `path`.
    """
    out: Dict[str, os.stat_result] = {}
    try:
        for f in os.listdir(path):
            full = os.path.join(path, f)
            if os.path.isfile(full):
                out[f] = os.stat(full)
    except FileNotFoundError:
        return {}
    return out


def is_file_stable(prev: os.stat_result, cur: os.stat_result, settle_seconds: float) -> bool:
    """
    A file is considered stable if:
      - size hasn't changed between observations
      - and it hasn't been modified in at least `settle_seconds`
    """
    return (
        prev.st_size == cur.st_size
        and prev.st_mtime == cur.st_mtime
        and (time.time() - cur.st_mtime) >= settle_seconds
    )


async def wait_for_files_to_settle(
    paths: List[str],
    settle_seconds: float = 0.4,
    max_wait: float = 3.0,
    poll: float = 0.05,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, os.stat_result]:
    """
    Wait until all given file paths are stable (size+mtime unchanged, old enough),
    or until `max_wait` seconds elapse.

    Returns a dict {path: os.stat_result} using the latest observed stats.
    """
    start = time.time()

    # Initial snapshot (if any missing, we keep waiting until they exist or timeout)
    prev: Dict[str, os.stat_result] = {}

    while True:
        curr: Dict[str, os.stat_result] = {}
        all_exist = True

        for p in paths:
            try:
                curr[p] = os.stat(p)
            except FileNotFoundError:
                all_exist = False

        if all_exist:
            # If we have a previous snapshot, enforce stability
            if prev:
                all_stable = True
                for p in paths:
                    if not is_file_stable(prev[p], curr[p], settle_seconds):
                        all_stable = False
                        break

                if all_stable:
                    return curr

            prev = curr

        if (time.time() - start) > max_wait:
            if logger:
                logger.warning(
                    f"Timed out waiting for files to settle after {max_wait:.2f}s; proceeding best-effort."
                )
            # Best-effort: return whatever stats we have for existing files
            return curr

        await asyncio.sleep(poll)


# -----------------------------
# Operation Implementation
# -----------------------------

class OperationMain(Operation):
    """
    Promote to SOI Operation

    Runs signal conditioning and captures N IQ files.
    """

    def __init__(
        self,
        node_uid: str = "",
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback=None,
        tak_cot_callback=None,
        frequency_mhz: Optional[float] = None,
    ):
        super().__init__(
            node_uid=node_uid,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
        )
        self.frequency_mhz = frequency_mhz

    async def run(self) -> None:
        """
        Promote-to-SOI capture stage (Operation 1)

        Runs the normal_decay flowgraph to record up to `max_files` burst IQ artifacts
        into an operation-scoped artifact directory, then selects a deterministic set
        of files and ensures they have settled before computing metadata.

        Notes:
        - We cap bursts inside the flowgraph (--max-bursts) AND enforce an outer cap by
        stopping once >= max_files files exist on disk.
        - We do a post-pass selection after stopping the flowgraph to avoid races where
        files arrive faster than the watcher can “observe” them.
        - We then wait for the selected files to settle so file sizes/metadata are correct.
        """

        if self.frequency_mhz is None:
            raise ValueError("Missing required parameter: frequency_mhz")

        # -----------------------------
        # Configuration (later: passed via args)
        # -----------------------------
        max_files = 5
        settle_seconds = 0.4

        # Two-stage timeout:
        #  - allow longer time to get the first file
        #  - once we have >=1 file, allow a shorter window to collect the remainder
        timeout_no_files_sec = 180.0     # e.g., 3 minutes
        timeout_after_first_sec = 30.0   # e.g., 30 seconds after first file appears

        # Additional settling controls for metadata correctness
        settle_max_wait = 3.0
        settle_poll = 0.05

        # Output directory for IQ files
        output_dir = os.path.join(FISSURE_ROOT, "artifacts", self.opid, "files")
        os.makedirs(output_dir, exist_ok=True)

        # Path to GNU Radio flowgraph (relative to this file in install_files/)
        base_dir = os.path.dirname(__file__)
        flowgraph_path = os.path.abspath(
            os.path.join(base_dir, "..", "promote_to_soi_lib", "normal_decay.py")
        )

        python3_path = "/usr/bin/python3"  # or shutil.which("python3")

        cmd = [
            python3_path,
            flowgraph_path,
            # "--filepath", "/home/user/FISSURE/Conditioner Data/Input/one_each_1MSps.iq",
            "--sample-rate", "1e6",
            "--threshold", "0.004",
            "--decay", "0.0002",
            "--max-bursts", str(max_files),  # GRC Parameter blocks use '-' not '_'
            "--rx-freq", str(self.frequency_mhz),  #"311",
            "--channel", "A:A",
            "--ip-address", "",
            "--serial", "False",
            "--antenna", "TX/RX",
            "--gain", "60",
        ]

        self.logger.info(f"Flowgraph argv: {cmd!r}")
        self.logger.info(f"Output directory: {output_dir}")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=output_dir,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )

        start_time = time.time()
        first_file_time = None

        known_files: Dict[str, os.stat_result] = {}
        stable_files = set()  # optional debug only

        stop_reason = "unknown"

        try:
            while True:
                now = time.time()

                # Respect stop requests promptly
                if self._stop:
                    stop_reason = "stop_requested"
                    self.logger.info("Stop requested; exiting capture loop.")
                    break

                # Scan directory
                current = list_files(output_dir)  # fname -> stat
                n_files = len(current)

                # Track when the first file appears (used for staged timeout)
                if n_files > 0 and first_file_time is None:
                    first_file_time = now

                # HARD CAP: stop as soon as we have enough files on disk
                if n_files >= max_files:
                    stop_reason = "max_files_reached"
                    self.logger.info(f"Reached {n_files} files on disk; stopping capture.")
                    break

                # Two-stage timeout check
                if n_files == 0:
                    if (now - start_time) > timeout_no_files_sec:
                        stop_reason = "timeout_no_files"
                        self.logger.info("Capture timeout reached (no files).")
                        break
                else:
                    # once we have at least one file, wait a shorter period to finish
                    if first_file_time is not None and (now - first_file_time) > timeout_after_first_sec:
                        stop_reason = "timeout_after_first"
                        self.logger.info("Capture timeout reached (after first file).")
                        break

                # Optional: track stability during capture (debug only)
                for fname, stat in current.items():
                    prev = known_files.get(fname)
                    if prev is not None:
                        if is_file_stable(prev, stat, settle_seconds):
                            if fname not in stable_files:
                                stable_files.add(fname)
                                self.logger.debug(f"File settled (during capture): {fname}")
                    known_files[fname] = stat

                await asyncio.sleep(0.05)

        finally:
            # Stop the flowgraph cleanly
            if proc.returncode is None:
                self.logger.info(f"Stopping flowgraph... (reason={stop_reason})")
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.logger.warning("Flowgraph did not terminate quickly; killing...")
                    proc.kill()
                    await proc.wait()

            # Log stderr while still stabilizing
            if proc.stderr:
                err = await proc.stderr.read()
                if err:
                    self.logger.error("Flowgraph stderr:\n" + err.decode(errors="ignore"))

        # -----------------------------
        # Artifact selection + settle gate
        # -----------------------------

        # Re-scan and pick final artifacts deterministically
        current = list_files(output_dir)  # fname -> stat

        if not current:
            self.logger.warning("No artifacts captured.")
            return

        # Sort by mtime then name for determinism (alternative: parse burst index)
        ordered = sorted(current.items(), key=lambda kv: (kv[1].st_mtime, kv[0]))
        selected = [fname for fname, _ in ordered[:max_files]]
        selected_paths = [os.path.join(output_dir, f) for f in selected]

        # Ensure selected files are fully settled before metadata extraction
        final_stats = await wait_for_files_to_settle(
            selected_paths,
            settle_seconds=settle_seconds,
            max_wait=settle_max_wait,
            poll=settle_poll,
            logger=self.logger,
        )

        # -----------------------------
        # Artifact registration placeholder
        # -----------------------------
        for fname in selected:
            full_path = os.path.join(output_dir, fname)
            st = final_stats.get(full_path)
            if st is not None:
                self.logger.info(f"Final artifact: {full_path} (size={st.st_size} bytes)")
            else:
                # Best-effort fallback
                try:
                    st2 = os.stat(full_path)
                    self.logger.info(f"Final artifact: {full_path} (size={st2.st_size} bytes)")
                except FileNotFoundError:
                    self.logger.warning(f"Final artifact missing unexpectedly: {full_path}")

        return



if __name__ == "__main__":
    async def _main():
        op = OperationMain(
            node_uid="test-node",
            logger=logging.getLogger("promote_to_soi_test"),
        )
        await op.run()

    asyncio.run(_main())
