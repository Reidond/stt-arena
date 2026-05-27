import json

from stt_arena.config import Settings
from stt_arena.providers.deepgram import DeepgramProvider
from stt_arena.providers.google import GoogleProvider
from stt_arena.providers.openai_whisper import OpenAIWhisperProvider
from stt_arena.providers.xai_grok import XAIGrokProvider


def test_deepgram_requires_api_key() -> None:
    provider = DeepgramProvider(Settings(deepgram_api_key=None))
    assert provider.is_available() is False
    assert provider.unavailable_reason() == "DEEPGRAM_API_KEY not set"


def test_openai_requires_api_key() -> None:
    provider = OpenAIWhisperProvider(Settings(openai_api_key=None))
    assert provider.is_available() is False


def test_xai_requires_api_key() -> None:
    provider = XAIGrokProvider(Settings(xai_api_key=None))
    assert provider.is_available() is False


def test_google_requires_credentials_file(tmp_path) -> None:
    provider = GoogleProvider(Settings(google_application_credentials=None))
    assert provider.is_available() is False

    missing = tmp_path / "missing.json"
    provider = GoogleProvider(
        Settings(google_application_credentials=str(missing)),
    )
    assert provider.is_available() is False

    creds = tmp_path / "service-account.json"
    creds.write_text(
        json.dumps(
            {
                "type": "service_account",
                "project_id": "demo",
                "private_key_id": "id",
                "private_key": (
                    "-----BEGIN PRIVATE KEY-----\nMIIE\n-----END PRIVATE KEY-----\n"
                ),
                "client_email": "demo@demo.iam.gserviceaccount.com",
                "client_id": "123",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        ),
        encoding="utf-8",
    )
    provider = GoogleProvider(
        Settings(google_application_credentials=str(creds)),
    )
    assert provider.is_available() is True
