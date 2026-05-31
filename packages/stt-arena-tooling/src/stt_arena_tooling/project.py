from __future__ import annotations

from pathlib import Path

from stt_arena_vite import ViteAssets


def _find_root() -> Path:
    for path in (Path.cwd(), *Path.cwd().parents):
        if (path / "assets" / "package.json").is_file() and (
            path / "src" / "stt_arena"
        ).is_dir():
            return path
    msg = "Could not locate the STT Arena repository root."
    raise RuntimeError(msg)


ROOT = _find_root()
ASSETS = ROOT / "assets"
SRC = ROOT / "src"
DIST_DIR = SRC / "stt_arena" / "static" / "dist"
VITE_ASSETS = ViteAssets(assets_dir=ASSETS, dist_dir=DIST_DIR)
