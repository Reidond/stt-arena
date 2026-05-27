"""Run the production server (requires a prior asset build)."""

from __future__ import annotations

import os
import subprocess
import sys

from stt_arena.assets_util import MANIFEST_PATH, ROOT, SRC
from stt_arena.config import get_settings


def main() -> None:
    if not MANIFEST_PATH.is_file():
        print("Assets not built. Run `uv run build` first.", file=sys.stderr)
        sys.exit(1)

    settings = get_settings()
    env = os.environ.copy()
    env.pop("STT_ARENA_DEV", None)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(SRC), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)

    print()
    print("  stt-arena (production)")
    print(f"  → http://{settings.host}:{settings.port}")
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
