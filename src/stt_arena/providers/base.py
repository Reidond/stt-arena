from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel


class TranscriptionResult(BaseModel):
    provider_id: str
    status: Literal["ok", "error"]
    text: str | None = None
    latency_ms: int
    word_count: int | None = None
    confidence: float | None = None
    error: str | None = None


class ProviderStatus(BaseModel):
    id: str
    display_name: str
    enabled: bool
    available: bool
    reason: str | None = None


class STTProvider(ABC):
    id: str
    display_name: str

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
        language: str | None = None,
        duration_sec: float | None = None,
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
            reason=reason,
        )


def word_count(text: str | None) -> int | None:
    if not text:
        return None
    return len(text.split())
