from __future__ import annotations

from collections.abc import AsyncIterator

from stt_arena_providers.base import ProviderStatus, STTProvider, TranscriptionResult
from stt_arena_providers.billing import (
    BILLING_PLANS,
    BillingPlan,
    CostBreakdown,
    billing_summary,
    estimate_transcription_cost,
)
from stt_arena_providers.languages import (
    list_language_options,
    resolve_canonical_language,
)
from stt_arena_providers.orchestration import (
    transcribe_all,
    transcribe_as_completed,
)
from stt_arena_providers.registry import available_providers, list_provider_statuses
from stt_arena_providers.settings import ProviderSettings


class ProviderService:
    def __init__(self, settings: ProviderSettings) -> None:
        self._settings = settings

    def statuses(self) -> list[ProviderStatus]:
        return list_provider_statuses(self._settings)

    def available(self) -> list[STTProvider]:
        return available_providers(self._settings)

    def display_names(self) -> dict[str, str]:
        return {item.id: item.display_name for item in self.statuses()}

    def status_payloads(self) -> list[dict[str, object]]:
        payloads: list[dict[str, object]] = []
        for item in self.statuses():
            payload = item.model_dump()
            if item.enabled:
                payload["billing"] = self.billing_summary(item.id)
            payloads.append(payload)
        return payloads

    def language_options(self) -> list[dict[str, object]]:
        return list_language_options()

    def resolve_language(self, language: str | None) -> str | None:
        return resolve_canonical_language(language)

    def billing_plans(self) -> list[BillingPlan]:
        return list(BILLING_PLANS.values())

    def billing_plan_payloads(self) -> list[dict[str, object]]:
        return [
            {
                "id": plan.id,
                "provider_id": plan.provider_id,
                "label": plan.label,
                "model": plan.model,
                "billing_mode": plan.billing_mode,
                "usd_per_minute": plan.usd_per_minute,
                "free_minutes_monthly": plan.free_minutes_monthly,
                "pricing_url": plan.pricing_url,
                "notes": plan.notes,
                "active_for_provider": (
                    self._settings.billing_plan_for(plan.provider_id) == plan.id
                ),
            }
            for plan in self.billing_plans()
        ]

    def billing_summary(self, provider_id: str) -> dict[str, object]:
        return billing_summary(provider_id, self._settings)

    def estimate_cost(
        self,
        provider_id: str,
        duration_sec: float,
    ) -> CostBreakdown | None:
        return estimate_transcription_cost(
            provider_id,
            duration_sec,
            settings=self._settings,
        )

    async def transcribe_all(
        self,
        audio: bytes,
        *,
        mime_type: str,
        source_audio: bytes | None = None,
        source_filename: str | None = None,
        language: str | None = None,
        duration_sec: float | None = None,
        diarization: bool = False,
    ) -> list[TranscriptionResult]:
        return await transcribe_all(
            self._settings,
            self.available(),
            audio,
            mime_type=mime_type,
            source_audio=source_audio,
            source_filename=source_filename,
            language=language,
            duration_sec=duration_sec,
            diarization=diarization,
        )

    async def transcribe_as_completed(
        self,
        audio: bytes,
        *,
        mime_type: str,
        source_audio: bytes | None = None,
        source_filename: str | None = None,
        language: str | None = None,
        duration_sec: float | None = None,
        diarization: bool = False,
    ) -> AsyncIterator[TranscriptionResult]:
        async for result in transcribe_as_completed(
            self._settings,
            self.available(),
            audio,
            mime_type=mime_type,
            source_audio=source_audio,
            source_filename=source_filename,
            language=language,
            duration_sec=duration_sec,
            diarization=diarization,
        ):
            yield result
