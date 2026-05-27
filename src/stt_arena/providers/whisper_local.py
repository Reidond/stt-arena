from __future__ import annotations

import asyncio
import io
import math
import time
from typing import TYPE_CHECKING

from stt_arena.providers.base import STTProvider, TranscriptionResult, word_count

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

    from stt_arena.config import Settings

_model: WhisperModel | None = None
_model_key: tuple[str, str] | None = None
_model_lock = asyncio.Lock()


class WhisperLocalProvider(STTProvider):
    id = "whisper_local"
    display_name = "faster-whisper"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_available(self) -> bool:
        return True

    def unavailable_reason(self) -> str | None:
        return None

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
            model = await _get_model(self._settings)

            def _run() -> tuple[str, float | None]:
                segments, _info = model.transcribe(
                    io.BytesIO(audio),
                    language=language,
                )
                parts: list[str] = []
                confidences: list[float] = []
                for segment in segments:
                    text = segment.text.strip()
                    if text:
                        parts.append(text)
                    confidences.append(
                        min(1.0, max(0.0, math.exp(segment.avg_logprob)))
                    )
                transcript = " ".join(parts)
                confidence = (
                    sum(confidences) / len(confidences) if confidences else None
                )
                return transcript, confidence

            text, confidence = await asyncio.to_thread(_run)
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


async def _get_model(settings: Settings) -> WhisperModel:
    global _model, _model_key

    key = (settings.whisper_model, settings.whisper_device)
    if _model is not None and _model_key == key:
        return _model

    async with _model_lock:
        if _model is not None and _model_key == key:
            return _model

        from faster_whisper import WhisperModel

        _model = await asyncio.to_thread(
            WhisperModel,
            settings.whisper_model,
            device=settings.whisper_device,
        )
        _model_key = key
        return _model
