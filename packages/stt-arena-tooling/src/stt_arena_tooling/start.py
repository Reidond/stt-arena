"""Run the production server after an asset build."""

from __future__ import annotations

import os
import subprocess
import sys

from stt_arena_tooling.port_util import release_port
from stt_arena_tooling.project import ROOT, SRC, VITE_ASSETS
from stt_arena_tooling.settings import get_settings


def main() -> None:
    if not VITE_ASSETS.manifest_path.is_file():
        print("Assets not built. Run `uv run build` first.", file=sys.stderr)
        sys.exit(1)

    settings = get_settings()
    released = release_port(settings.port)
    if released:
        print(
            f"Released port {settings.port} from PID(s): "
            f"{', '.join(map(str, released))}"
        )

    env = os.environ.copy()
    env.pop("STT_ARENA_DEV", None)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(SRC), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)

    print()
    print("  stt-arena (production)")
    print(f"  -> http://{settings.host}:{settings.port}")
    print()

    subprocess.run(
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
        check=True,
    )


if __name__ == "__main__":
    main()
