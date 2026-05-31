from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest
from stt_arena_providers.base import STTProvider, TranscriptionResult
from stt_arena_providers.orchestration import transcribe_all
from stt_arena_providers.retries import retry_delay_sec

from stt_arena.config import Settings


class FlakyProvider(STTProvider):
    id = "flaky"
    display_name = "Flaky"

    def __init__(self, *, retryable: bool = True) -> None:
        self.calls = 0
        self.retryable = retryable

    def is_available(self) -> bool:
        return True

    def unavailable_reason(self) -> str | None:
        return None

    async def transcribe(
        self,
        audio: bytes,
        *,
        mime_type: str,
        source_audio: bytes | None = None,
        source_filename: str | None = None,
        language: str | None = None,
        duration_sec: float | None = None,
        diarization: bool = False,
    ) -> TranscriptionResult:
        del (
            audio,
            mime_type,
            source_audio,
            source_filename,
            language,
            duration_sec,
            diarization,
        )
        self.calls += 1
        if self.calls == 1:
            return TranscriptionResult(
                provider_id=self.id,
                status="error",
                latency_ms=1,
                error="temporary provider failure",
                retryable=self.retryable,
            )
        return TranscriptionResult(
            provider_id=self.id,
            status="ok",
            latency_ms=1,
            text="hello",
        )


def test_retry_delay_uses_bounded_exponential_backoff() -> None:
    settings = Settings(
        provider_retry_base_delay_sec=0.5,
        provider_retry_max_delay_sec=1.0,
    )

    assert retry_delay_sec(settings, 1) == 0.5
    assert retry_delay_sec(settings, 2) == 1.0
    assert retry_delay_sec(settings, 3) == 1.0


@pytest.mark.anyio
@patch(
    "stt_arena_providers.orchestration.asyncio.sleep",
    new_callable=AsyncMock,
)
async def test_transcription_retries_retryable_provider_result(
    mock_sleep: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = FlakyProvider()
    settings = Settings(
        provider_max_attempts=3,
        provider_retry_base_delay_sec=0.25,
    )

    with caplog.at_level(logging.INFO):
        results = await transcribe_all(
            settings,
            [provider],
            b"wav",
            mime_type="audio/wav",
        )

    assert results[0].status == "ok"
    assert provider.calls == 2
    mock_sleep.assert_awaited_once_with(0.25)
    assert "retrying after attempt=1/3 delay_sec=0.25" in caplog.text


@pytest.mark.anyio
@patch(
    "stt_arena_providers.orchestration.asyncio.sleep",
    new_callable=AsyncMock,
)
async def test_transcription_does_not_retry_permanent_provider_result(
    mock_sleep: AsyncMock,
) -> None:
    provider = FlakyProvider(retryable=False)

    results = await transcribe_all(
        Settings(provider_max_attempts=3),
        [provider],
        b"wav",
        mime_type="audio/wav",
    )

    assert results[0].status == "error"
    assert provider.calls == 1
    mock_sleep.assert_not_awaited()


def test_retryable_flag_is_internal_only() -> None:
    result = TranscriptionResult(
        provider_id="flaky",
        status="error",
        latency_ms=1,
        error="temporary provider failure",
        retryable=True,
    )

    assert result.retryable is True
    assert "retryable" not in result.model_dump()
