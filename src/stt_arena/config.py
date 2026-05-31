from functools import lru_cache

from pydantic_settings import SettingsConfigDict
from stt_arena_providers.billing import default_billing_plan
from stt_arena_vite import ViteSettings


class Settings(ViteSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 8000
    enabled_providers: str = "openai_whisper"
    max_upload_mb: int = 25
    max_audio_duration_sec: int = 900
    provider_timeout_sec: int = 120
    provider_max_attempts: int = 3
    provider_retry_base_delay_sec: float = 1.0
    provider_retry_max_delay_sec: float = 8.0
    openai_diarize_timeout_sec: int = 600
    google_batch_timeout_sec: int = 600

    log_level: str = "INFO"
    log_dir: str = "logs"
    log_file: str = "stt-arena.log"
    log_max_bytes: int = 5 * 1024 * 1024
    log_backup_count: int = 5

    openai_transcribe_model: str = "gpt-4o-transcribe"
    openai_diarize_model: str = "gpt-4o-transcribe-diarize"
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
    def enabled_provider_ids(self) -> list[str]:
        return [p.strip() for p in self.enabled_providers.split(",") if p.strip()]

    def billing_plan_for(self, provider_id: str) -> str:
        field = f"billing_plan_{provider_id}"
        override = getattr(self, field, None)
        if isinstance(override, str) and override:
            return override
        return default_billing_plan(provider_id)

    def billing_monthly_minutes_used_for(self, provider_id: str) -> float:
        field = f"billing_monthly_minutes_{provider_id}"
        return float(getattr(self, field, 0))


@lru_cache
def get_settings() -> Settings:
    return Settings()
