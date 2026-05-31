from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import httpx

from stt_arena_providers.base import (
    STTProvider,
    TranscriptionResult,
    format_speaker_turns,
    word_count,
)
from stt_arena_providers.retries import (
    exception_detail,
    exception_message,
    is_retryable_exception,
)

if TYPE_CHECKING:
    from stt_arena_providers.settings import ProviderSettings

logger = logging.getLogger(__name__)


class XAIGrokProvider(STTProvider):
    id = "xai_grok"
    display_name = "xAI Grok"
    supports_diarization = True

    def __init__(self, settings: ProviderSettings) -> None:
        self._settings = settings

    def is_available(self) -> bool:
        return bool(self._settings.xai_api_key)

    def unavailable_reason(self) -> str | None:
        if self.is_available():
            return None
        return "XAI_API_KEY not set"

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
        del mime_type, source_audio, source_filename, duration_sec
        started = time.perf_counter()

        try:
            base_url = self._settings.xai_base_url.rstrip("/")
            data: dict[str, str] = {}
            if diarization:
                data["diarize"] = "true"
            if language:
                data["language"] = language

            async with httpx.AsyncClient(
                timeout=float(self._settings.provider_timeout_sec)
            ) as client:
                response = await client.post(
                    f"{base_url}/stt",
                    headers={"Authorization": f"Bearer {self._settings.xai_api_key}"},
                    files={"file": ("audio.wav", audio, "audio/wav")},
                    data=data or None,
                )
                response.raise_for_status()
                payload = response.json()

            text = _format_diarized_response(payload) if diarization else ""
            if not text:
                text = _extract_text(payload)
            latency_ms = int((time.perf_counter() - started) * 1000)
            return TranscriptionResult(
                provider_id=self.id,
                status="ok",
                text=text or None,
                latency_ms=latency_ms,
                word_count=word_count(text),
                confidence=None,
            )
        except httpx.HTTPStatusError as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            retryable = is_retryable_exception(exc)
            logger.exception(
                "Provider %s request failed status_code=%s retryable=%s detail=%s",
                self.id,
                exc.response.status_code,
                retryable,
                exception_detail(exc),
            )
            return TranscriptionResult(
                provider_id=self.id,
                status="error",
                latency_ms=latency_ms,
                error=exception_message(exc),
                retryable=retryable,
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            retryable = is_retryable_exception(exc)
            logger.exception(
                "Provider %s request failed retryable=%s detail=%s",
                self.id,
                retryable,
                exception_detail(exc),
            )
            return TranscriptionResult(
                provider_id=self.id,
                status="error",
                latency_ms=latency_ms,
                error=exception_message(exc),
                retryable=retryable,
            )


def _format_diarized_response(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""

    words = payload.get("words")
    if not isinstance(words, list):
        return ""

    turns: list[tuple[object, str]] = []
    for word in words:
        if not isinstance(word, dict):
            continue
        speaker = word.get("speaker")
        text = word.get("text")
        if speaker is None or not isinstance(text, str):
            continue
        turns.append((speaker, text))

    return format_speaker_turns(turns, zero_based_speakers=True)


def _extract_text(payload: object) -> str:
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        return str(payload)

    for key in ("text", "transcript", "transcription"):
        value = payload.get(key)
        if isinstance(value, str):
            return value

    return ""
