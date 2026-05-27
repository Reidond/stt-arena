"""Run Vite and Uvicorn together for local development."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

from stt_arena.assets_util import ASSETS, ROOT, SRC, ensure_assets_deps, npm


def main() -> None:
    ensure_assets_deps()

    env = os.environ.copy()
    env["STT_ARENA_DEV"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(SRC), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)

    procs: list[subprocess.Popen[bytes]] = []

    def shutdown(signum: int | None = None, frame: object | None = None) -> None:
        del signum, frame
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
        for proc in procs:
            if proc.poll() is None:
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    vite = subprocess.Popen(
        [npm(), "run", "dev"],
        cwd=ASSETS,
        env=env,
    )
    procs.append(vite)

    uvicorn = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "stt_arena.main:app",
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--reload-dir",
            str(SRC),
        ],
        cwd=ROOT,
        env=env,
    )
    procs.append(uvicorn)

    print()
    print("  stt-arena dev")
    print("  App   → http://127.0.0.1:8000")
    print("  Vite  → http://127.0.0.1:5173  (asset HMR)")
    print()
    print("  Press Ctrl+C to stop")
    print()

    try:
        while True:
            for proc in procs:
                if proc.poll() is not None:
                    shutdown()
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
