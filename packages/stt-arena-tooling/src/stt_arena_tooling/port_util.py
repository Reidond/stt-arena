from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time


def release_port(port: int, *, grace_sec: float = 2.0) -> list[int]:
    pids = _listening_pids(port)
    if not pids:
        return []

    current_pid = os.getpid()
    targets = [pid for pid in pids if pid != current_pid]
    if not targets:
        return []

    for pid in targets:
        _kill(pid, signal.SIGTERM)

    deadline = time.monotonic() + grace_sec
    while time.monotonic() < deadline:
        remaining = set(_listening_pids(port)).intersection(targets)
        if not remaining:
            return targets
        time.sleep(0.1)

    for pid in set(_listening_pids(port)).intersection(targets):
        _kill(pid, signal.SIGKILL)

    return targets


def _listening_pids(port: int) -> list[int]:
    if shutil.which("lsof") is None:
        return []

    result = subprocess.run(
        ["lsof", f"-tiTCP:{port}", "-sTCP:LISTEN"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in {0, 1}:
        return []

    pids: list[int] = []
    for line in result.stdout.splitlines():
        try:
            pids.append(int(line.strip()))
        except ValueError:
            continue
    return pids


def _kill(pid: int, sig: signal.Signals) -> None:
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        return
