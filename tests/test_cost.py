import pytest

from stt_arena.config import Settings
from stt_arena.cost import (
    estimate_transcription_cost,
    resolve_billing_plan,
)


def test_openai_gpt4o_transcribe_rounds_to_nearest_second() -> None:
    settings = Settings()
    cost = estimate_transcription_cost(
        "openai_whisper",
        19.4,
        settings=settings,
    )
    assert cost is not None
    assert cost.plan_id == "gpt-4o-transcribe"
    assert cost.billable_duration_sec == 19.0
    assert cost.usd == pytest.approx(19 / 60 * 0.006, rel=1e-6)


def test_openai_gpt4o_minimum_one_second() -> None:
    settings = Settings()
    cost = estimate_transcription_cost(
        "openai_whisper",
        0.2,
        settings=settings,
    )
    assert cost is not None
    assert cost.billable_duration_sec == 1.0
    assert cost.usd == pytest.approx(0.006 / 60, rel=1e-6)


def test_google_applies_monthly_free_tier() -> None:
    settings = Settings(
        billing_plan_google="google-v1-standard-logging",
        billing_monthly_minutes_google=55,
    )
    cost = estimate_transcription_cost("google", 600, settings=settings)
    assert cost is not None
    assert cost.billable_duration_sec == 600.0
    assert cost.free_minutes_applied == pytest.approx(5.0, rel=1e-6)
    assert cost.usd == pytest.approx(5 * 0.016, rel=1e-6)


def test_google_free_within_monthly_allowance() -> None:
    settings = Settings(
        billing_plan_google="google-v1-standard-logging",
        billing_monthly_minutes_google=10,
    )
    cost = estimate_transcription_cost("google", 30, settings=settings)
    assert cost is not None
    assert cost.usd == 0.0
    assert cost.free_minutes_applied == pytest.approx(0.5, rel=1e-6)


def test_deepgram_nova3_batch_exact_duration() -> None:
    settings = Settings(billing_plan_deepgram="nova-3-batch-payg")
    cost = estimate_transcription_cost("deepgram", 90, settings=settings)
    assert cost is not None
    assert cost.billable_duration_sec == 90.0
    assert cost.usd == pytest.approx(1.5 * 0.0077, rel=1e-6)
    assert cost.plan_label.startswith("Deepgram Nova-3")


def test_xai_batch_hourly_rate() -> None:
    settings = Settings(billing_plan_xai_grok="xai-stt-batch")
    cost = estimate_transcription_cost("xai_grok", 3600, settings=settings)
    assert cost is not None
    assert cost.usd == pytest.approx(0.10, rel=1e-6)


def test_google_v2_volume_tier_rate() -> None:
    settings = Settings(
        billing_plan_google="google-v2-standard-tier1",
        billing_monthly_minutes_google=600_000,
    )
    plan = resolve_billing_plan("google", settings)
    assert plan.rate_for_monthly_minutes(600_000) == 0.01
    cost = estimate_transcription_cost("google", 60, settings=settings)
    assert cost is not None
    assert cost.rate_usd_per_minute == 0.01
    assert cost.usd == pytest.approx(0.01, rel=1e-6)
def test_unknown_provider_returns_none() -> None:
    settings = Settings()
    assert (
        estimate_transcription_cost("unknown_provider", 10, settings=settings) is None
    )


def test_invalid_plan_raises() -> None:
    settings = Settings(billing_plan_openai_whisper="not-a-plan")
    with pytest.raises(ValueError, match="Unknown billing plan"):
        resolve_billing_plan("openai_whisper", settings)
