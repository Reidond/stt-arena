"""Shared helpers for the Vite assets toolchain."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
SRC = ROOT / "src"
DIST_DIR = Path(__file__).resolve().parent / "static" / "dist"
MANIFEST_PATH = DIST_DIR / ".vite" / "manifest.json"


def npm() -> str:
    return shutil.which("npm") or "npm"


def ensure_assets_deps() -> None:
    if (ASSETS / "node_modules").is_dir():
        return
    print("Installing asset dependencies…")
    subprocess.run([npm(), "install"], cwd=ASSETS, check=True)


def build_assets() -> None:
    ensure_assets_deps()
    print("Building assets…")
    subprocess.run([npm(), "run", "build"], cwd=ASSETS, check=True)
    if not MANIFEST_PATH.is_file():
        msg = f"Expected Vite manifest at {MANIFEST_PATH} after build."
        raise RuntimeError(msg)
    print(f"Assets built → {DIST_DIR}")
