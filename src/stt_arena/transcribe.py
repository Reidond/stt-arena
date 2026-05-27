from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from stt_arena.languages import language_for_provider
from stt_arena.provider_timeouts import provider_timeout_sec as resolve_provider_timeout
from stt_arena.providers.base import STTProvider, TranscriptionResult

if TYPE_CHECKING:
    from stt_arena.config import Settings


class NoProvidersError(Exception):
    """Raised when no enabled providers are available for transcription."""


async def _run_provider(
    provider: STTProvider,
    settings: Settings,
    audio: bytes,
    *,
    mime_type: str,
    language: str | None,
    duration_sec: float | None,
) -> TranscriptionResult:
    started = time.perf_counter()
    provider_language = language_for_provider(provider.id, language)
    timeout_sec = resolve_provider_timeout(settings, provider.id, duration_sec)
    try:
        return await asyncio.wait_for(
            provider.transcribe(
                audio,
                mime_type=mime_type,
                language=provider_language,
                duration_sec=duration_sec,
            ),
            timeout=timeout_sec,
        )
    except TimeoutError:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return TranscriptionResult(
            provider_id=provider.id,
            status="error",
            latency_ms=latency_ms,
            error=f"Timed out after {int(timeout_sec)}s",
        )
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return TranscriptionResult(
            provider_id=provider.id,
            status="error",
            latency_ms=latency_ms,
            error=str(exc),
        )


async def transcribe_as_completed(
    settings: Settings,
    audio: bytes,
    *,
    mime_type: str,
    language: str | None = None,
    duration_sec: float | None = None,
) -> AsyncIterator[TranscriptionResult]:
    from stt_arena.providers import available_providers

    providers = available_providers(settings)
    if not providers:
        raise NoProvidersError("No enabled providers are available")

    tasks = [
        asyncio.create_task(
            _run_provider(
                provider,
                settings,
                audio,
                mime_type=mime_type,
                language=language,
                duration_sec=duration_sec,
            )
        )
        for provider in providers
    ]

    for task in asyncio.as_completed(tasks):
        yield await task


async def transcribe_all(
    settings: Settings,
    audio: bytes,
    *,
    mime_type: str,
    language: str | None = None,
    duration_sec: float | None = None,
) -> list[TranscriptionResult]:
    from stt_arena.providers import available_providers

    providers = available_providers(settings)
    if not providers:
        raise NoProvidersError("No enabled providers are available")

    gathered = await asyncio.gather(
        *(
            _run_provider(
                provider,
                settings,
                audio,
                mime_type=mime_type,
                language=language,
                duration_sec=duration_sec,
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
