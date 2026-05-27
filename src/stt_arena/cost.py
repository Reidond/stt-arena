"""Provider billing plans and transcription cost estimates."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from stt_arena.config import Settings


class DurationRounding(StrEnum):
    """How providers round audio duration before billing."""

    NEAREST_SECOND = "nearest_second"
    CEIL_SECOND = "ceil_second"
    EXACT = "exact"


@dataclass(frozen=True, slots=True)
class BillingPlan:
    id: str
    provider_id: str
    label: str
    model: str
    billing_mode: str
    usd_per_minute: float
    rounding: DurationRounding
    free_minutes_monthly: float = 0.0
    volume_tiers: tuple[tuple[float, float], ...] = ()
    pricing_url: str = ""
    notes: str = ""

    def rate_for_monthly_minutes(self, monthly_minutes_used: float) -> float:
        if not self.volume_tiers:
            return self.usd_per_minute
        for threshold, rate in self.volume_tiers:
            if monthly_minutes_used < threshold:
                return rate
        return self.volume_tiers[-1][1]


BILLING_PLANS: dict[str, BillingPlan] = {
    "whisper-1": BillingPlan(
        id="whisper-1",
        provider_id="openai_whisper",
        label="OpenAI Whisper-1",
        model="whisper-1",
        billing_mode="batch",
        usd_per_minute=0.006,
        rounding=DurationRounding.NEAREST_SECOND,
        pricing_url="https://developers.openai.com/api/docs/models/whisper-1",
        notes="Billed to the nearest second.",
    ),
    "gpt-4o-mini-transcribe": BillingPlan(
        id="gpt-4o-mini-transcribe",
        provider_id="openai_whisper",
        label="OpenAI GPT-4o mini transcribe",
        model="gpt-4o-mini-transcribe",
        billing_mode="batch",
        usd_per_minute=0.003,
        rounding=DurationRounding.NEAREST_SECOND,
        pricing_url="https://developers.openai.com/api/docs/models/whisper-1",
        notes="Billed to the nearest second.",
    ),
    "gpt-4o-transcribe": BillingPlan(
        id="gpt-4o-transcribe",
        provider_id="openai_whisper",
        label="OpenAI GPT-4o transcribe",
        model="gpt-4o-transcribe",
        billing_mode="batch",
        usd_per_minute=0.006,
        rounding=DurationRounding.NEAREST_SECOND,
        pricing_url="https://developers.openai.com/api/docs/models/whisper-1",
        notes="Billed to the nearest second.",
    ),
    "nova-2-batch-payg": BillingPlan(
        id="nova-2-batch-payg",
        provider_id="deepgram",
        label="Deepgram Nova-2 · batch · PAYG",
        model="nova-2",
        billing_mode="batch",
        usd_per_minute=0.0043,
        rounding=DurationRounding.EXACT,
        pricing_url="https://deepgram.com/pricing",
        notes="Pre-recorded batch API; billed by audio duration.",
    ),
    "nova-3-batch-payg": BillingPlan(
        id="nova-3-batch-payg",
        provider_id="deepgram",
        label="Deepgram Nova-3 · batch · PAYG",
        model="nova-3",
        billing_mode="batch",
        usd_per_minute=0.0077,
        rounding=DurationRounding.EXACT,
        pricing_url="https://deepgram.com/pricing",
        notes="Pre-recorded batch API; billed by audio duration.",
    ),
    "nova-3-batch-growth": BillingPlan(
        id="nova-3-batch-growth",
        provider_id="deepgram",
        label="Deepgram Nova-3 · batch · Growth",
        model="nova-3",
        billing_mode="batch",
        usd_per_minute=0.0065,
        rounding=DurationRounding.EXACT,
        pricing_url="https://deepgram.com/pricing",
        notes="Annual commitment plan.",
    ),
    "google-v1-standard-logging": BillingPlan(
        id="google-v1-standard-logging",
        provider_id="google",
        label="Google STT v1 · standard · data logging",
        model="default",
        billing_mode="sync_or_long_running",
        usd_per_minute=0.016,
        rounding=DurationRounding.CEIL_SECOND,
        free_minutes_monthly=60.0,
        pricing_url="https://cloud.google.com/speech-to-text/pricing",
        notes="First 60 minutes/month free; rounded up to the nearest second.",
    ),
    "google-v1-standard-no-logging": BillingPlan(
        id="google-v1-standard-no-logging",
        provider_id="google",
        label="Google STT v1 · standard · no data logging",
        model="default",
        billing_mode="sync_or_long_running",
        usd_per_minute=0.024,
        rounding=DurationRounding.CEIL_SECOND,
        free_minutes_monthly=60.0,
        pricing_url="https://cloud.google.com/speech-to-text/pricing",
        notes="First 60 minutes/month free; rounded up to the nearest second.",
    ),
    "google-v2-standard-tier1": BillingPlan(
        id="google-v2-standard-tier1",
        provider_id="google",
        label="Google STT v2 · Chirp 3 · 0–500k min/mo",
        model="chirp_3",
        billing_mode="sync_or_batch",
        usd_per_minute=0.016,
        rounding=DurationRounding.CEIL_SECOND,
        pricing_url="https://cloud.google.com/speech-to-text/pricing",
        notes="Speech-to-Text v2 standard tier with Chirp 3.",
        volume_tiers=(
            (500_000, 0.016),
            (1_000_000, 0.01),
            (2_000_000, 0.008),
            (math.inf, 0.004),
        ),
    ),
    "google-v2-dynamic-batch": BillingPlan(
        id="google-v2-dynamic-batch",
        provider_id="google",
        label="Google STT v2 · dynamic batch",
        model="chirp_3",
        billing_mode="dynamic_batch",
        usd_per_minute=0.003,
        rounding=DurationRounding.CEIL_SECOND,
        pricing_url="https://cloud.google.com/speech-to-text/pricing",
        notes="Up to 24-hour turnaround.",
    ),
    "xai-stt-batch": BillingPlan(
        id="xai-stt-batch",
        provider_id="xai_grok",
        label="xAI Grok STT · batch (REST)",
        model="grok-stt",
        billing_mode="batch",
        usd_per_minute=0.10 / 60,
        rounding=DurationRounding.EXACT,
        pricing_url="https://docs.x.ai/docs/models",
        notes="$0.10 per hour of audio.",
    ),
    "xai-stt-streaming": BillingPlan(
        id="xai-stt-streaming",
        provider_id="xai_grok",
        label="xAI Grok STT · streaming",
        model="grok-stt",
        billing_mode="streaming",
        usd_per_minute=0.20 / 60,
        rounding=DurationRounding.EXACT,
        pricing_url="https://docs.x.ai/docs/models",
        notes="$0.20 per hour of audio.",
    ),
}

DEFAULT_PLAN_BY_PROVIDER: dict[str, str] = {
    "openai_whisper": "gpt-4o-transcribe",
    "deepgram": "nova-3-batch-payg",
    "google": "google-v2-standard-tier1",
    "xai_grok": "xai-stt-batch",
}


class CostBreakdown(BaseModel):
    usd: float
    plan_id: str
    plan_label: str
    model: str
    billing_mode: str
    audio_duration_sec: float
    billable_duration_sec: float
    rate_usd_per_minute: float
    free_minutes_applied: float
    monthly_minutes_used: float
    pricing_url: str
    notes: str


def list_plans_for_provider(provider_id: str) -> list[BillingPlan]:
    return [
        plan
        for plan in BILLING_PLANS.values()
        if plan.provider_id == provider_id
    ]


def resolve_billing_plan(provider_id: str, settings: Settings) -> BillingPlan:
    plan_id = settings.billing_plan_for(provider_id)
    plan = BILLING_PLANS.get(plan_id)
    if plan is None:
        msg = f"Unknown billing plan {plan_id!r} for provider {provider_id!r}"
        raise ValueError(msg)
    if plan.provider_id != provider_id:
        msg = (
            f"Billing plan {plan_id!r} belongs to {plan.provider_id!r}, "
            f"not {provider_id!r}"
        )
        raise ValueError(msg)
    return plan


def billing_summary(provider_id: str, settings: Settings) -> dict[str, object]:
    plan = resolve_billing_plan(provider_id, settings)
    monthly_used = settings.billing_monthly_minutes_used_for(provider_id)
    rate = plan.rate_for_monthly_minutes(monthly_used)
    return {
        "plan_id": plan.id,
        "plan_label": plan.label,
        "model": plan.model,
        "billing_mode": plan.billing_mode,
        "rate_usd_per_minute": rate,
        "free_minutes_monthly": plan.free_minutes_monthly,
        "monthly_minutes_used": monthly_used,
        "pricing_url": plan.pricing_url,
    }


def _round_duration(duration_sec: float, rounding: DurationRounding) -> float:
    if duration_sec <= 0:
        return 0.0
    match rounding:
        case DurationRounding.NEAREST_SECOND:
            return float(max(1, round(duration_sec)))
        case DurationRounding.CEIL_SECOND:
            return float(max(1, math.ceil(duration_sec)))
        case DurationRounding.EXACT:
            return duration_sec


def estimate_transcription_cost(
    provider_id: str,
    duration_sec: float,
    *,
    settings: Settings,
) -> CostBreakdown | None:
    if provider_id not in DEFAULT_PLAN_BY_PROVIDER:
        return None

    plan = resolve_billing_plan(provider_id, settings)
    monthly_used = settings.billing_monthly_minutes_used_for(provider_id)
    billable_duration_sec = _round_duration(duration_sec, plan.rounding)

    duration_min = billable_duration_sec / 60
    remaining_free = max(0.0, plan.free_minutes_monthly - monthly_used)
    free_applied = min(duration_min, remaining_free)
    chargeable_min = max(0.0, duration_min - free_applied)

    rate = plan.rate_for_monthly_minutes(monthly_used)
    usd = round(chargeable_min * rate, 6)

    return CostBreakdown(
        usd=usd,
        plan_id=plan.id,
        plan_label=plan.label,
        model=plan.model,
        billing_mode=plan.billing_mode,
        audio_duration_sec=round(duration_sec, 3),
        billable_duration_sec=round(billable_duration_sec, 3),
        rate_usd_per_minute=rate,
        free_minutes_applied=round(free_applied, 4),
        monthly_minutes_used=monthly_used,
        pricing_url=plan.pricing_url,
        notes=plan.notes,
    )


def estimate_cost_usd(
    provider_id: str,
    duration_sec: float,
    *,
    settings: Settings | None = None,
) -> float | None:
    """Backward-compatible helper returning USD only."""
    if settings is None:
        from stt_arena.config import get_settings

        settings = get_settings()
    breakdown = estimate_transcription_cost(
        provider_id,
        duration_sec,
        settings=settings,
    )
    if breakdown is None:
        return None
    return breakdown.usd
