from stt_arena.config import Settings
from stt_arena.provider_timeouts import (
    google_batch_operation_timeout_sec,
    provider_timeout_sec,
)
from stt_arena.providers.google import GOOGLE_SYNC_MAX_DURATION_SEC


def test_cloud_providers_use_default_timeout() -> None:
    settings = Settings(provider_timeout_sec=120, google_batch_timeout_sec=600)
    assert provider_timeout_sec(settings, "openai_whisper", 106.0) == 120.0
    assert provider_timeout_sec(settings, "google", 30.0) == 120.0


def test_google_sync_uses_default_timeout_at_sixty_seconds() -> None:
    settings = Settings(provider_timeout_sec=120, google_batch_timeout_sec=600)
    assert provider_timeout_sec(settings, "google", 60.0) == 120.0


def test_google_batch_uses_extended_timeout() -> None:
    settings = Settings(provider_timeout_sec=120, google_batch_timeout_sec=600)
    assert provider_timeout_sec(settings, "google", 106.0) == 600.0
    over_sync = GOOGLE_SYNC_MAX_DURATION_SEC + 0.1
    assert provider_timeout_sec(settings, "google", over_sync) == 600.0


def test_google_batch_operation_timeout_scales_with_duration() -> None:
    settings = Settings(google_batch_timeout_sec=600)
    assert google_batch_operation_timeout_sec(settings, 106.0) == 600.0
    assert google_batch_operation_timeout_sec(settings, 300.0) == 1020.0
