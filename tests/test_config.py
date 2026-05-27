from stt_arena.config import Settings


def test_enabled_provider_ids_parses_csv() -> None:
    settings = Settings(enabled_providers="deepgram, openai_whisper, google")
    assert settings.enabled_provider_ids == [
        "deepgram",
        "openai_whisper",
        "google",
    ]


def test_default_enabled_provider_is_openai_whisper() -> None:
    settings = Settings(_env_file=None)
    assert settings.enabled_provider_ids == ["openai_whisper"]
