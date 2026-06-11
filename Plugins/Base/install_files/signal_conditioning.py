#!/usr/bin/env python3
"""
Signal Conditioning Operation

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
from typing import Dict, List, Optional, Callable

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
    settle_seconds: float,
    max_wait: Optional[float],
    poll: float,
    logger=None,
    stop_check: Optional[Callable[[], bool]] = None,
):
    start = time.time()
    last_stats: Dict[str, os.stat_result] = {}
    stable_since: Dict[str, Optional[float]] = {p: None for p in paths}
    done = set()

    while len(done) < len(paths):
        now = time.time()

        # Allow operation stop to break out promptly
        if stop_check and stop_check():
            if logger:
                logger.info("Stop requested during settle; exiting settle early.")
            break

        # If max_wait is None, wait indefinitely
        if max_wait is not None and (now - start) > max_wait:
            if logger:
                logger.warning("Settle max_wait exceeded; returning best-effort stats.")
            break

        for p in paths:
            if p in done:
                continue
            try:
                st = os.stat(p)
            except FileNotFoundError:
                stable_since[p] = None
                continue

            prev = last_stats.get(p)
            if prev is not None and is_file_stable(prev, st, settle_seconds):
                if stable_since[p] is None:
                    stable_since[p] = now
                # require continuous stability for settle_seconds
                if (now - stable_since[p]) >= settle_seconds:
                    done.add(p)
            else:
                stable_since[p] = None

            last_stats[p] = st

        await asyncio.sleep(poll)

    return last_stats


# -----------------------------
# Operation Implementation
# -----------------------------

class OperationMain(Operation):
    """
    Signal Conditioning Operation

    Runs signal conditioning and captures N IQ files.
    """

    def __init__(
        self,
        node_uid: str = "",
        logger: logging.Logger = logging.getLogger(__name__),
        alert_callback=None,
        tak_cot_callback=None,
        frequency_mhz: Optional[float] = None,
        status_callback=None,
    ):
        super().__init__(
            node_uid=node_uid,
            logger=logger,
            alert_callback=alert_callback,
            tak_cot_callback=tak_cot_callback,
            status_callback=status_callback,
        )
        self.frequency_mhz = frequency_mhz

    async def run(self) -> None:
        """
        Promote-to-SOI capture stage (Operation 1)

        Infinite-wait variant:
        - Waits indefinitely for artifacts to appear (no staged timeouts).
        - Stops only when:
            (a) stop requested, OR
            (b) >= max_files exist AND the last selected file is stable.
        - Then re-selects deterministically and waits for all selected files to settle
        before extracting metadata.
        """

        if self.frequency_mhz is None:
            raise ValueError("Missing required parameter: frequency_mhz")

        # -----------------------------
        # Configuration (later: passed via args)
        # -----------------------------
        max_files = 5

        # Pi-friendly settling behavior
        settle_poll = 0.10       # how often we stat/poll the filesystem
        settle_seconds = 1.0     # how long a file must remain unchanged to be "stable"
        settle_max_wait = None   # None = wait indefinitely for settle (recommended)

        # Output directory for IQ files
        output_dir = os.path.join(FISSURE_ROOT, "artifacts", self.opid, "files")
        os.makedirs(output_dir, exist_ok=True)

        # Optional status update (no lifecycle words; runner owns those)
        if getattr(self, "status_callback", None):
            try:
                await self.status_callback(f"Running: Capture @ {self.frequency_mhz:.3f} MHz")
            except Exception:
                self.logger.exception("status_callback failed")

        # Path to GNU Radio flowgraph (relative to this file in install_files/)
        base_dir = os.path.dirname(__file__)
        flowgraph_path = os.path.abspath(
            os.path.join(base_dir, "..", "promote_to_soi_lib", "normal_decay.py")
        )

        python3_path = "/usr/bin/python3"  # or shutil.which("python3")

        cmd = [
            python3_path,
            flowgraph_path,
            "--sample-rate", "1e6",
            "--threshold", "0.004",
            "--decay", "0.0002",
            "--max-bursts", str(max_files),
            "--rx-freq", str(self.frequency_mhz),
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

        known_files: Dict[str, os.stat_result] = {}
        stable_files = set()  # optional debug only
        stop_reason = "unknown"

        # Latch selection when max_files is reached, then wait for last to settle
        cap_selected: Optional[List[str]] = None
        cap_last: Optional[str] = None
        cap_wait_started: Optional[float] = None

        try:
            while True:
                now = time.time()

                if self._stop:
                    stop_reason = "stop_requested"
                    self.logger.info("Stop requested; exiting capture loop.")
                    break

                current = list_files(output_dir)  # fname -> stat
                n_files = len(current)

                # Snapshot previous stat for cap_last BEFORE overwriting known_files
                prev_last = known_files.get(cap_last) if cap_last else None

                # Track stability during capture (and update known_files)
                for fname, stat in current.items():
                    prev = known_files.get(fname)
                    if prev is not None and is_file_stable(prev, stat, settle_seconds):
                        if fname not in stable_files:
                            stable_files.add(fname)
                            self.logger.debug(f"File settled (during capture): {fname}")
                    known_files[fname] = stat

                if n_files >= max_files:
                    if cap_selected is None:
                        ordered = sorted(current.items(), key=lambda kv: (kv[1].st_mtime, kv[0]))
                        cap_selected = [fname for fname, _ in ordered[:max_files]]
                        cap_last = cap_selected[-1] if cap_selected else None
                        cap_wait_started = now
                        self.logger.info(
                            f"Reached {n_files} files; latched selection={cap_selected}. "
                            f"Waiting for last file to settle: {cap_last}"
                        )
                        prev_last = known_files.get(cap_last) if cap_last else None

                    if cap_last is None or cap_last not in current:
                        self.logger.warning(
                            f"Latched last file missing ({cap_last}); re-latching selection."
                        )
                        cap_selected = None
                        cap_last = None
                        cap_wait_started = None
                        await asyncio.sleep(settle_poll)
                        continue

                    last_stat = current[cap_last]

                    if prev_last is not None and is_file_stable(prev_last, last_stat, settle_seconds):
                        stop_reason = "max_files_and_last_settled"
                        self.logger.info(f"Last file settled: {cap_last}. Stopping capture.")
                        break

                    if settle_max_wait is not None and cap_wait_started is not None:
                        if (now - cap_wait_started) > settle_max_wait:
                            stop_reason = "max_files_settle_timeout"
                            self.logger.warning(
                                f"Timed out waiting for last file to settle ({cap_last}); stopping anyway."
                            )
                            break

                await asyncio.sleep(settle_poll)

        finally:
            if proc.returncode is None:
                self.logger.info(f"Stopping flowgraph... (reason={stop_reason})")
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.logger.warning("Flowgraph did not terminate quickly; killing...")
                    proc.kill()
                    await proc.wait()

            if proc.stderr:
                err = await proc.stderr.read()
                if err:
                    self.logger.warning("Flowgraph stderr:\n" + err.decode(errors="ignore"))

        # If we were stopped, don't block indefinitely on settle
        if self._stop:
            self.logger.info("Stop requested; skipping post-capture settle stage.")
            return

        # -----------------------------
        # Artifact selection + settle gate
        # -----------------------------
        current = list_files(output_dir)
        if not current:
            self.logger.warning("No artifacts captured.")
            return

        ordered = sorted(current.items(), key=lambda kv: (kv[1].st_mtime, kv[0]))
        selected = [fname for fname, _ in ordered[:max_files]]
        selected_paths = [os.path.join(output_dir, f) for f in selected]

        final_stats = await wait_for_files_to_settle(
            selected_paths,
            settle_seconds=settle_seconds,
            max_wait=settle_max_wait,
            poll=settle_poll,
            logger=self.logger,
            stop_check=lambda: self._stop,
        )

        for fname in selected:
            full_path = os.path.join(output_dir, fname)
            st = final_stats.get(full_path)
            if st is not None:
                self.logger.info(f"Final artifact: {full_path} (size={st.st_size} bytes)")
            else:
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
