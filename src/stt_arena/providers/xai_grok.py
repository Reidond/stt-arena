from __future__ import annotations

import time
from typing import TYPE_CHECKING

import httpx

from stt_arena.providers.base import STTProvider, TranscriptionResult, word_count

if TYPE_CHECKING:
    from stt_arena.config import Settings


class XAIGrokProvider(STTProvider):
    id = "xai_grok"
    display_name = "xAI Grok"

    def __init__(self, settings: Settings) -> None:
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
        language: str | None = None,
        duration_sec: float | None = None,
    ) -> TranscriptionResult:
        del mime_type, duration_sec
        started = time.perf_counter()

        try:
            base_url = self._settings.xai_base_url.rstrip("/")
            data: dict[str, str] = {}
            if language:
                data["language"] = language

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{base_url}/stt",
                    headers={"Authorization": f"Bearer {self._settings.xai_api_key}"},
                    files={"file": ("audio.wav", audio, "audio/wav")},
                    data=data or None,
                )
                response.raise_for_status()
                payload = response.json()

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
            detail = exc.response.text.strip() or str(exc)
            return TranscriptionResult(
                provider_id=self.id,
                status="error",
                latency_ms=latency_ms,
                error=detail,
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return TranscriptionResult(
                provider_id=self.id,
                status="error",
                latency_ms=latency_ms,
                error=str(exc),
            )


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
