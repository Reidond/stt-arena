"""Per-provider transcription timeout helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from stt_arena_providers.settings import ProviderSettings

# Chirp 3 synchronous Recognize supports audio up to one minute (batch above that).
GOOGLE_SYNC_MAX_DURATION_SEC = 60.0


def provider_timeout_sec(
    settings: ProviderSettings,
    provider_id: str,
    duration_sec: float | None,
    *,
    diarization: bool = False,
) -> float:
    if provider_id == "openai_whisper" and diarization:
        return float(settings.openai_diarize_timeout_sec)
    if _uses_google_batch(provider_id, duration_sec):
        return float(settings.google_batch_timeout_sec)
    return float(settings.provider_timeout_sec)


def google_batch_operation_timeout_sec(
    settings: ProviderSettings,
    duration_sec: float,
) -> float:
    configured = float(settings.google_batch_timeout_sec)
    # Chirp 3 batch can run slower than real time; scale slightly with clip length.
    scaled = duration_sec * 3.0 + 120.0
    return max(configured, scaled)


def _uses_google_batch(provider_id: str, duration_sec: float | None) -> bool:
    return (
        provider_id == "google"
        and duration_sec is not None
        and duration_sec > GOOGLE_SYNC_MAX_DURATION_SEC
    )
