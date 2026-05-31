from __future__ import annotations

from typing import Protocol


class ProviderSettings(Protocol):
    provider_timeout_sec: int
    provider_max_attempts: int
    provider_retry_base_delay_sec: float
    provider_retry_max_delay_sec: float
    openai_diarize_timeout_sec: int
    google_batch_timeout_sec: int

    openai_transcribe_model: str
    openai_diarize_model: str
    deepgram_model: str
    google_speech_model: str
    google_speech_region: str

    deepgram_api_key: str | None
    google_application_credentials: str | None
    google_storage_bucket: str | None
    openai_api_key: str | None
    openai_base_url: str
    xai_api_key: str | None
    xai_base_url: str

    @property
    def enabled_provider_ids(self) -> list[str]: ...

    def billing_plan_for(self, provider_id: str) -> str: ...

    def billing_monthly_minutes_used_for(self, provider_id: str) -> float: ...
