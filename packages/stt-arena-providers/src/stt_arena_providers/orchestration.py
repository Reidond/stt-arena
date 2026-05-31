from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from stt_arena_providers.base import STTProvider, TranscriptionResult
from stt_arena_providers.languages import language_for_provider
from stt_arena_providers.retries import (
    exception_detail,
    exception_message,
    is_retryable_exception,
    retry_delay_sec,
)
from stt_arena_providers.timeouts import (
    provider_timeout_sec as resolve_provider_timeout,
)

if TYPE_CHECKING:
    from stt_arena_providers.settings import ProviderSettings

logger = logging.getLogger(__name__)


class NoProvidersError(Exception):
    """Raised when no enabled providers are available for transcription."""


async def _run_provider(
    provider: STTProvider,
    settings: ProviderSettings,
    audio: bytes,
    *,
    mime_type: str,
    source_audio: bytes | None,
    source_filename: str | None,
    language: str | None,
    duration_sec: float | None,
    diarization: bool,
) -> TranscriptionResult:
    started = time.perf_counter()
    provider_language = language_for_provider(provider.id, language)
    timeout_sec = resolve_provider_timeout(
        settings,
        provider.id,
        duration_sec,
        diarization=diarization,
    )
    max_attempts = max(1, int(settings.provider_max_attempts))
    logger.info(
        "Provider %s transcription scheduled attempts=%s timeout_sec=%.1f "
        "audio_bytes=%s duration_sec=%s language=%s diarization=%s",
        provider.id,
        max_attempts,
        timeout_sec,
        len(audio),
        duration_sec,
        provider_language,
        diarization,
    )

    for attempt in range(1, max_attempts + 1):
        attempt_started = time.perf_counter()
        logger.info(
            "Provider %s transcription attempt %s/%s started",
            provider.id,
            attempt,
            max_attempts,
        )
        try:
            result = await asyncio.wait_for(
                provider.transcribe(
                    audio,
                    mime_type=mime_type,
                    source_audio=source_audio,
                    source_filename=source_filename,
                    language=provider_language,
                    duration_sec=duration_sec,
                    diarization=diarization,
                ),
                timeout=timeout_sec,
            )
        except TimeoutError:
            attempt_latency_ms = int((time.perf_counter() - attempt_started) * 1000)
            logger.warning(
                "Provider %s transcription attempt %s/%s timed out after %.1fs",
                provider.id,
                attempt,
                max_attempts,
                timeout_sec,
            )
            result = TranscriptionResult(
                provider_id=provider.id,
                status="error",
                latency_ms=attempt_latency_ms,
                error=f"Timed out after {timeout_sec:g}s",
                retryable=True,
            )
        except Exception as exc:
            attempt_latency_ms = int((time.perf_counter() - attempt_started) * 1000)
            retryable = is_retryable_exception(exc)
            logger.exception(
                "Provider %s transcription attempt %s/%s raised retryable=%s "
                "detail=%s",
                provider.id,
                attempt,
                max_attempts,
                retryable,
                exception_detail(exc),
            )
            result = TranscriptionResult(
                provider_id=provider.id,
                status="error",
                latency_ms=attempt_latency_ms,
                error=exception_message(exc),
                retryable=retryable,
            )

        if result.status == "ok":
            total_latency_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "Provider %s transcription completed attempt=%s/%s "
                "attempt_latency_ms=%s total_latency_ms=%s",
                provider.id,
                attempt,
                max_attempts,
                result.latency_ms,
                total_latency_ms,
            )
            return result.model_copy(update={"latency_ms": total_latency_ms})

        logger.error(
            "Provider %s transcription failed attempt=%s/%s latency_ms=%s "
            "retryable=%s error=%s",
            provider.id,
            attempt,
            max_attempts,
            result.latency_ms,
            result.retryable,
            result.error,
        )
        if not result.retryable or attempt == max_attempts:
            total_latency_ms = int((time.perf_counter() - started) * 1000)
            return result.model_copy(update={"latency_ms": total_latency_ms})

        delay_sec = retry_delay_sec(settings, attempt)
        logger.warning(
            "Provider %s transcription retrying after attempt=%s/%s delay_sec=%.2f",
            provider.id,
            attempt,
            max_attempts,
            delay_sec,
        )
        await asyncio.sleep(delay_sec)

    raise AssertionError("Provider retry loop exited unexpectedly")


async def transcribe_as_completed(
    settings: ProviderSettings,
    providers: list[STTProvider],
    audio: bytes,
    *,
    mime_type: str,
    source_audio: bytes | None = None,
    source_filename: str | None = None,
    language: str | None = None,
    duration_sec: float | None = None,
    diarization: bool = False,
) -> AsyncIterator[TranscriptionResult]:
    if not providers:
        raise NoProvidersError("No enabled providers are available")
    logger.info(
        "Starting progressive transcription for %s providers",
        len(providers),
    )

    tasks = [
        asyncio.create_task(
            _run_provider(
                provider,
                settings,
                audio,
                mime_type=mime_type,
                source_audio=source_audio,
                source_filename=source_filename,
                language=language,
                duration_sec=duration_sec,
                diarization=diarization,
            )
        )
        for provider in providers
    ]

    for task in asyncio.as_completed(tasks):
        yield await task


async def transcribe_all(
    settings: ProviderSettings,
    providers: list[STTProvider],
    audio: bytes,
    *,
    mime_type: str,
    source_audio: bytes | None = None,
    source_filename: str | None = None,
    language: str | None = None,
    duration_sec: float | None = None,
    diarization: bool = False,
) -> list[TranscriptionResult]:
    if not providers:
        raise NoProvidersError("No enabled providers are available")
    logger.info("Starting batch transcription for %s providers", len(providers))

    gathered = await asyncio.gather(
        *(
            _run_provider(
                provider,
                settings,
                audio,
                mime_type=mime_type,
                source_audio=source_audio,
                source_filename=source_filename,
                language=language,
                duration_sec=duration_sec,
                diarization=diarization,
            )
            for provider in providers
        ),
        return_exceptions=True,
    )

    results: list[TranscriptionResult] = []
    for provider, item in zip(providers, gathered, strict=True):
        if isinstance(item, TranscriptionResult):
            results.append(item)
            continue
        results.append(
            TranscriptionResult(
                provider_id=provider.id,
                status="error",
                latency_ms=0,
                error=str(item),
            )
        )
    return results
