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
    google_batch_timeout_sec: int = 600

    openai_transcribe_model: str = "gpt-4o-transcribe"
    deepgram_model: str = "nova-3"
    google_speech_model: str = "chirp_3"
    google_speech_region: str = "us"

    deepgram_api_key: str | None = None
    google_application_credentials: str | None = None
    google_storage_bucket: str | None = None
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    xai_api_key: str | None = None
    xai_base_url: str = "https://api.x.ai/v1"

    billing_plan_openai_whisper: str = "gpt-4o-transcribe"
    billing_plan_deepgram: str = "nova-3-batch-payg"
    billing_plan_google: str = "google-v2-standard-tier1"
    billing_plan_xai_grok: str = "xai-stt-batch"

    billing_monthly_minutes_openai_whisper: float = 0
    billing_monthly_minutes_deepgram: float = 0
    billing_monthly_minutes_google: float = 0
    billing_monthly_minutes_xai_grok: float = 0

    @property
    def is_dev(self) -> bool:
        return self.dev or os.getenv("STT_ARENA_DEV") == "1"

    @property
    def vite_origin(self) -> str:
        return f"http://{self.vite_host}:{self.vite_port}"

    @property
    def enabled_provider_ids(self) -> list[str]:
        return [p.strip() for p in self.enabled_providers.split(",") if p.strip()]

    def billing_plan_for(self, provider_id: str) -> str:
        field = f"billing_plan_{provider_id}"
        override = getattr(self, field, None)
        if isinstance(override, str) and override:
            return override
        from stt_arena.cost import DEFAULT_PLAN_BY_PROVIDER

        return DEFAULT_PLAN_BY_PROVIDER[provider_id]

    def billing_monthly_minutes_used_for(self, provider_id: str) -> float:
        field = f"billing_monthly_minutes_{provider_id}"
        return float(getattr(self, field, 0))


@lru_cache
def get_settings() -> Settings:
    return Settings()
