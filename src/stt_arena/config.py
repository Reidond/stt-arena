import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 8000
    dev: bool = False

    vite_host: str = "127.0.0.1"
    vite_port: int = 5173

    enabled_providers: str = "openai_whisper"
    max_upload_mb: int = 25
    max_audio_duration_sec: int = 300
    provider_timeout_sec: int = 120

    whisper_model: str = "base"
    whisper_device: str = "cpu"

    deepgram_api_key: str | None = None
    google_application_credentials: str | None = None
    google_storage_bucket: str | None = None
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    xai_api_key: str | None = None
    xai_base_url: str = "https://api.x.ai/v1"

    @property
    def is_dev(self) -> bool:
        return self.dev or os.getenv("STT_ARENA_DEV") == "1"

    @property
    def vite_origin(self) -> str:
        return f"http://{self.vite_host}:{self.vite_port}"

    @property
    def enabled_provider_ids(self) -> list[str]:
        return [p.strip() for p in self.enabled_providers.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
