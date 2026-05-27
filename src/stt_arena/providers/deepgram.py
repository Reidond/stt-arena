from __future__ import annotations

import time
from typing import TYPE_CHECKING

from deepgram import AsyncDeepgramClient

from stt_arena.providers.base import STTProvider, TranscriptionResult, word_count

if TYPE_CHECKING:
    from stt_arena.config import Settings


class DeepgramProvider(STTProvider):
    id = "deepgram"
    display_name = "Deepgram"

    def __init__(self, settings: Settings) -> None:
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
        language: str | None = None,
        duration_sec: float | None = None,
    ) -> TranscriptionResult:
        del mime_type, duration_sec
        started = time.perf_counter()

        try:
            client = AsyncDeepgramClient(api_key=self._settings.deepgram_api_key)
            response = await client.listen.v1.media.transcribe_file(
                request=audio,
                model="nova-2",
                language=language,
                smart_format=True,
                punctuate=True,
            )

            text = ""
            confidence: float | None = None
            results = getattr(response, "results", None)
            if results is not None:
                channels = results.channels
                if channels:
                    alternatives = channels[0].alternatives
                    if alternatives:
                        text = alternatives[0].transcript or ""
                        confidence = alternatives[0].confidence

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
            return TranscriptionResult(
                provider_id=self.id,
                status="error",
                latency_ms=latency_ms,
                error=str(exc),
            )
