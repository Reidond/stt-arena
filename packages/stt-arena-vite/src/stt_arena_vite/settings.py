from __future__ import annotations

import os
import tempfile
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class ViteSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    dev: bool = False
    vite_socket_path: str = str(
        Path(tempfile.gettempdir()) / "stt-arena" / "vite.sock"
    )

    @property
    def is_dev(self) -> bool:
        return self.dev or os.getenv("STT_ARENA_DEV") == "1"

    @property
    def resolved_vite_socket_path(self) -> str:
        path = Path(self.vite_socket_path).expanduser()
        if path.is_absolute():
            return str(path)
        return str(Path.cwd() / path)
