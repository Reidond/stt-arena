from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from typing import TYPE_CHECKING

from deepgram import AsyncDeepgramClient

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


class DeepgramProvider(STTProvider):
    id = "deepgram"
    display_name = "Deepgram"
    supports_diarization = True

    def __init__(self, settings: ProviderSettings) -> None:
        self._settings = settings

    def is_available(self) -> bool:
        return bool(self._settings.deepgram_api_key)

    def unavailable_reason(self) -> str | None:
        if self.is_available():
            return None
        return "DEEPGRAM_API_KEY not set"

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
            client = AsyncDeepgramClient(api_key=self._settings.deepgram_api_key)
            response = await client.listen.v1.media.transcribe_file(
                request=audio,
                model=self._settings.deepgram_model,
                language=language,
                detect_language=True if language is None else None,
                diarize_model="latest" if diarization else None,
                utterances=diarization,
                smart_format=True,
                punctuate=True,
            )

            text, confidence = _parse_response(
                response,
                diarization_enabled=diarization,
            )

            latency_ms = int((time.perf_counter() - started) * 1000)
            return TranscriptionResult(
                provider_id=self.id,
                status="ok",
                text=text or None,
                latency_ms=latency_ms,
                word_count=word_count(text),
                confidence=confidence,
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            retryable = is_retryable_exception(exc)
            logger.exception(
                "Provider %s request failed model=%s language=%s diarization=%s "
                "audio_bytes=%s retryable=%s detail=%s",
                self.id,
                self._settings.deepgram_model,
                language,
                diarization,
                len(audio),
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


def _parse_response(
    response: object,
    *,
    diarization_enabled: bool,
) -> tuple[str, float | None]:
    results = getattr(response, "results", None)
    if results is None:
        return "", None

    if diarization_enabled:
        text = _format_diarized_response(results)
        if text:
            return text, _utterance_confidence(getattr(results, "utterances", None))

    channels = getattr(results, "channels", None)
    if not channels:
        return "", None

    alternatives = getattr(channels[0], "alternatives", None)
    if not alternatives:
        return "", None

    alternative = alternatives[0]
    return alternative.transcript or "", alternative.confidence


def _format_diarized_response(results: object) -> str:
    text = _format_utterances(getattr(results, "utterances", None))
    if text:
        return text
    return _format_channel_words(getattr(results, "channels", None))


def _format_utterances(utterances: object) -> str:
    if not utterances:
        return ""

    turns: list[tuple[object, str]] = []
    for utterance in _iter_items(utterances):
        transcript = getattr(utterance, "transcript", None)
        speaker = getattr(utterance, "speaker", None)
        if not transcript or speaker is None:
            continue
        turns.append((speaker, transcript))

    return format_speaker_turns(turns, zero_based_speakers=True)


def _format_channel_words(channels: object) -> str:
    turns: list[tuple[object, str]] = []
    for channel in _iter_items(channels):
        alternatives = getattr(channel, "alternatives", None)
        if not alternatives:
            continue
        words = getattr(alternatives[0], "words", None)
        current_speaker: object | None = None
        current_words: list[str] = []
        for word in _iter_items(words):
            speaker = getattr(word, "speaker", None)
            text = getattr(word, "punctuated_word", None) or getattr(
                word,
                "word",
                None,
            )
            if speaker is None or not text:
                continue
            if current_speaker != speaker and current_words:
                turns.append((current_speaker, " ".join(current_words)))
                current_words = []
            current_speaker = speaker
            current_words.append(text)
        if current_speaker is not None and current_words:
            turns.append((current_speaker, " ".join(current_words)))

    return format_speaker_turns(turns, zero_based_speakers=True)


def _utterance_confidence(utterances: object) -> float | None:
    if not utterances:
        return None

    values: list[float] = []
    for utterance in _iter_items(utterances):
        confidence = getattr(utterance, "confidence", None)
        if isinstance(confidence, int | float):
            values.append(float(confidence))
    if not values:
        return None
    return sum(values) / len(values)


def _iter_items(value: object) -> Iterable[object]:
    if isinstance(value, Iterable) and not isinstance(value, str | bytes):
        return value
    return ()
