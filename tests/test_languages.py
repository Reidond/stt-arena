import pytest

from stt_arena.languages import (
    language_for_provider,
    list_language_options,
    provider_language_map,
    resolve_canonical_language,
)


def test_resolve_canonical_language_auto_detect() -> None:
    assert resolve_canonical_language(None) is None
    assert resolve_canonical_language("") is None
    assert resolve_canonical_language("  ") is None


def test_resolve_canonical_language_valid_code() -> None:
    assert resolve_canonical_language("en-US") == "en-US"


def test_resolve_canonical_language_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unsupported language code"):
        resolve_canonical_language("xx-YY")


def test_language_for_openai_uses_iso639_1() -> None:
    assert language_for_provider("openai_whisper", "en-US") == "en"
    assert language_for_provider("openai_whisper", "cmn-Hans-CN") == "zh"


def test_language_for_google_uses_bcp47() -> None:
    assert language_for_provider("google", "en-US") == "en-US"
    assert language_for_provider("google", "cmn-Hans-CN") == "cmn-Hans-CN"
    assert language_for_provider("google", "he-IL") == "iw-IL"


def test_language_for_deepgram_uses_bcp47() -> None:
    assert language_for_provider("deepgram", "fr-CA") == "fr-CA"


def test_provider_language_map_includes_all_providers() -> None:
    mapping = provider_language_map("pt-BR")
    assert mapping["openai_whisper"] == "pt"
    assert mapping["deepgram"] == "pt-BR"
    assert mapping["google"] == "pt-BR"


def test_list_language_options_has_labels_and_provider_codes() -> None:
    options = list_language_options()
    assert options[0]["code"] == "en-US"
    assert options[0]["label"] == "English (United States)"
    assert "providers" in options[0]
