"""Run Vite and Uvicorn together for local development."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from contextlib import suppress

from stt_arena_tooling.port_util import release_port
from stt_arena_tooling.project import ASSETS, ROOT, SRC, VITE_ASSETS
from stt_arena_tooling.settings import get_settings


def _terminate_process(
    proc: subprocess.Popen[bytes],
    *,
    timeout_sec: float = 5.0,
) -> None:
    if proc.poll() is not None:
        return

    proc.terminate()
    try:
        proc.wait(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        proc.kill()
        with suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=timeout_sec)


def _shutdown_processes(
    *,
    uvicorn: subprocess.Popen[bytes] | None,
    vite: subprocess.Popen[bytes] | None,
) -> None:
    if uvicorn is not None:
        _terminate_process(uvicorn)
    if vite is not None:
        _terminate_process(vite)


def main() -> None:
    VITE_ASSETS.ensure_dependencies()
    settings = get_settings()

    released = release_port(settings.port)
    if released:
        released_pids = ", ".join(map(str, released))
        print(f"Released port {settings.port} from PID(s): {released_pids}")

    env = os.environ.copy()
    env["STT_ARENA_DEV"] = "1"
    env["VITE_SOCKET_PATH"] = settings.resolved_vite_socket_path
    env["VITE_HMR_HOST"] = (
        "localhost" if settings.host in {"127.0.0.1", "0.0.0.0"} else settings.host
    )
    env["VITE_HMR_CLIENT_PORT"] = str(settings.port)
    env["VITE_DEV_ORIGIN"] = f"http://{env['VITE_HMR_HOST']}:{settings.port}"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(SRC), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)

    vite: subprocess.Popen[bytes] | None = None
    uvicorn: subprocess.Popen[bytes] | None = None
    stopping = False

    def shutdown(signum: int | None = None, frame: object | None = None) -> None:
        nonlocal stopping
        del signum, frame
        if stopping:
            return
        stopping = True
        _shutdown_processes(uvicorn=uvicorn, vite=vite)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    vite = subprocess.Popen(
        VITE_ASSETS.dev_command(),
        cwd=ASSETS,
        env=env,
        start_new_session=True,
    )

    uvicorn = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "stt_arena.main:app",
            "--host",
            settings.host,
            "--port",
            str(settings.port),
        ],
        cwd=ROOT,
        env=env,
        start_new_session=True,
    )

    print()
    print("  stt-arena dev")
    print(f"  -> http://{settings.host}:{settings.port}")
    if settings.host in {"127.0.0.1", "0.0.0.0"}:
        print(f"  -> http://localhost:{settings.port}")
    print()
    print("  Press Ctrl+C to stop")
    print()

    try:
        while True:
            for proc in (vite, uvicorn):
                if proc.poll() is not None:
                    shutdown()
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
