from functools import lru_cache

from stt_arena_vite import ViteSettings


class ToolingSettings(ViteSettings):
    host: str = "127.0.0.1"
    port: int = 8000


@lru_cache
def get_settings() -> ToolingSettings:
    return ToolingSettings()
