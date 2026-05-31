from typing import cast

from stt_arena_providers import ProviderService

from stt_arena.config import Settings


def test_provider_service_exposes_statuses_languages_and_billing() -> None:
    providers = ProviderService(Settings(enabled_providers="openai_whisper"))

    statuses = providers.status_payloads()
    by_id = {item["id"]: item for item in statuses}
    assert by_id["openai_whisper"]["enabled"] is True
    assert by_id["deepgram"]["enabled"] is False
    billing = cast(dict[str, object], by_id["openai_whisper"]["billing"])
    assert billing["plan_id"] == "gpt-4o-transcribe"

    assert providers.resolve_language("en-US") == "en-US"
    assert providers.language_options()
    assert providers.billing_plan_payloads()
