import tempfile
from pathlib import Path

from stt_arena.config import Settings


def test_enabled_provider_ids_parses_csv() -> None:
    settings = Settings(enabled_providers="deepgram, openai_whisper, google")
    assert settings.enabled_provider_ids == [
        "deepgram",
        "openai_whisper",
        "google",
    ]


def test_default_enabled_provider_is_openai_whisper() -> None:
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert settings.enabled_provider_ids == ["openai_whisper"]


def test_default_vite_socket_uses_system_temp_directory() -> None:
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    expected = Path(tempfile.gettempdir()) / "stt-arena" / "vite.sock"
    assert Path(settings.resolved_vite_socket_path) == expected
