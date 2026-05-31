from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, Field


class TranscriptionResult(BaseModel):
    provider_id: str
    status: Literal["ok", "error"]
    text: str | None = None
    latency_ms: int
    word_count: int | None = None
    confidence: float | None = None
    error: str | None = None
    retryable: bool = Field(default=False, exclude=True)


class ProviderStatus(BaseModel):
    id: str
    display_name: str
    enabled: bool
    available: bool
    supports_diarization: bool
    reason: str | None = None


class STTProvider(ABC):
    id: str
    display_name: str
    supports_diarization = False

    @abstractmethod
    def is_available(self) -> bool:
        """True when configured and ready (e.g. API key present)."""

    @abstractmethod
    def unavailable_reason(self) -> str | None:
        """Human-readable reason when not available."""

    @abstractmethod
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
        """Transcribe normalized WAV bytes.

        Must not raise; return status=error instead.
        """

    def status(self, *, enabled: bool) -> ProviderStatus:
        available = self.is_available()
        reason = None if available else self.unavailable_reason()
        return ProviderStatus(
            id=self.id,
            display_name=self.display_name,
            enabled=enabled,
            available=available,
            supports_diarization=self.supports_diarization,
            reason=reason,
        )


def word_count(text: str | None) -> int | None:
    if not text:
        return None
    return len(text.split())


def speaker_label(value: object, *, zero_based: bool = False) -> str:
    raw = str(value).strip()
    if not raw:
        return "Speaker"
    if raw.lower().startswith("speaker"):
        return raw
    if isinstance(value, int) or raw.isdigit():
        number = int(raw)
        if zero_based:
            number += 1
        return f"Speaker {number}"
    return f"Speaker {raw}"


def format_speaker_turns(
    turns: Iterable[tuple[object, str]],
    *,
    zero_based_speakers: bool = False,
) -> str:
    grouped: list[list[str]] = []
    for speaker, text in turns:
        clean_text = " ".join(text.split())
        if not clean_text:
            continue

        label = speaker_label(speaker, zero_based=zero_based_speakers)
        if grouped and grouped[-1][0] == label:
            grouped[-1][1] = f"{grouped[-1][1]} {clean_text}"
            continue
        grouped.append([label, clean_text])

    return "\n\n".join(f"{label}: {text}" for label, text in grouped)
