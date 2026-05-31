from __future__ import annotations

import logging
import time
from pathlib import Path
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
from stt_arena_providers.timeouts import provider_timeout_sec

if TYPE_CHECKING:
    from stt_arena_providers.settings import ProviderSettings

logger = logging.getLogger(__name__)

OPENAI_TRANSCRIPTION_EXTENSIONS = {
    ".flac",
    ".m4a",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".ogg",
    ".wav",
    ".webm",
}


class OpenAIWhisperProvider(STTProvider):
    id = "openai_whisper"
    display_name = "OpenAI GPT-4o Transcribe"
    supports_diarization = True

    def __init__(self, settings: ProviderSettings) -> None:
        self._settings = settings

    def is_available(self) -> bool:
        return bool(self._settings.openai_api_key)

    def unavailable_reason(self) -> str | None:
        if self.is_available():
            return None
        return "OPENAI_API_KEY not set"

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
        started = time.perf_counter()
        model = (
            self._settings.openai_diarize_model
            if diarization
            else self._settings.openai_transcribe_model
        )

        try:
            base_url = self._settings.openai_base_url.rstrip("/")
            data: dict[str, str] = {
                "model": model,
            }
            if diarization:
                data["response_format"] = "diarized_json"
                data["chunking_strategy"] = "auto"
            if language:
                data["language"] = language

            filename, upload_audio, upload_mime_type = _select_upload(
                audio,
                source_audio=source_audio,
                source_filename=source_filename,
                source_mime_type=mime_type,
            )
            logger.info(
                "Uploading OpenAI transcription audio as %s (%s bytes)",
                Path(filename).suffix or ".wav",
                len(upload_audio),
            )
            response = await _post_transcription(
                f"{base_url}/audio/transcriptions",
                api_key=self._settings.openai_api_key,
                filename=filename,
                audio=upload_audio,
                mime_type=upload_mime_type,
                data=data,
                timeout_sec=provider_timeout_sec(
                    self._settings,
                    self.id,
                    duration_sec,
                    diarization=diarization,
                ),
            )
            response.raise_for_status()
            payload = response.json()

            if diarization and isinstance(payload, dict):
                text = _format_diarized_response(payload) or payload.get("text", "")
            elif isinstance(payload, dict):
                text = payload.get("text", "")
            else:
                text = str(payload)
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
                "Provider %s request failed model=%s status_code=%s "
                "retryable=%s detail=%s",
                self.id,
                model,
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
                "Provider %s request failed model=%s retryable=%s detail=%s",
                self.id,
                model,
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


def _format_diarized_response(payload: dict[str, object]) -> str:
    segments = payload.get("segments")
    if not isinstance(segments, list):
        return ""

    turns: list[tuple[object, str]] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        speaker = segment.get("speaker")
        text = segment.get("text")
        if speaker is None or not isinstance(text, str):
            continue
        turns.append((speaker, text))

    return format_speaker_turns(turns)


def _select_upload(
    audio: bytes,
    *,
    source_audio: bytes | None,
    source_filename: str | None,
    source_mime_type: str,
) -> tuple[str, bytes, str]:
    if source_audio is not None and source_filename:
        filename = Path(source_filename).name
        if Path(filename).suffix.lower() in OPENAI_TRANSCRIPTION_EXTENSIONS:
            return filename, source_audio, source_mime_type
    return "audio.wav", audio, "audio/wav"


async def _post_transcription(
    url: str,
    *,
    api_key: str | None,
    filename: str,
    audio: bytes,
    mime_type: str,
    data: dict[str, str],
    timeout_sec: float,
) -> httpx.Response:
    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        return await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (filename, audio, mime_type)},
            data=data,
        )
