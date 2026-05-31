from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ViteAssets:
    assets_dir: Path
    dist_dir: Path

    @property
    def manifest_path(self) -> Path:
        return self.dist_dir / ".vite" / "manifest.json"

    def ensure_dependencies(self) -> None:
        if (self.assets_dir / "node_modules").is_dir():
            return
        print("Installing asset dependencies...")
        subprocess.run([_npm(), "install"], cwd=self.assets_dir, check=True)

    def dev_command(self) -> list[str]:
        return ["node", "scripts/vite-socket-dev.mjs"]

    def build(self) -> None:
        self.ensure_dependencies()
        print("Building assets...")
        subprocess.run([_npm(), "run", "build"], cwd=self.assets_dir, check=True)
        if not self.manifest_path.is_file():
            msg = f"Expected Vite manifest at {self.manifest_path} after build."
            raise RuntimeError(msg)
        print(f"Assets built -> {self.dist_dir}")


def _npm() -> str:
    return shutil.which("npm") or "npm"
