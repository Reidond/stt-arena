from __future__ import annotations

import io
import wave
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from stt_arena.config import get_settings
from stt_arena.main import app
from stt_arena.providers.base import TranscriptionResult


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _make_wav(duration_sec: float = 0.2) -> bytes:
    frame_count = int(duration_sec * 16000)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * frame_count)
    return buffer.getvalue()


def test_list_providers_json(client: TestClient) -> None:
    response = client.get("/api/providers")
    assert response.status_code == 200
    payload = response.json()
    assert "providers" in payload
    assert any(item["id"] == "openai_whisper" for item in payload["providers"])


def test_list_providers_html_for_htmx(client: TestClient) -> None:
    response = client.get("/api/providers", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "openai_whisper" in response.text


def test_transcribe_missing_file(client: TestClient) -> None:
    response = client.post("/api/transcribe")
    assert response.status_code == 400


@patch("stt_arena.main.transcribe_all", new_callable=AsyncMock)
def test_transcribe_returns_results(
    mock_transcribe: AsyncMock,
    client: TestClient,
) -> None:
    mock_transcribe.return_value = [
        TranscriptionResult(
            provider_id="openai_whisper",
            status="ok",
            text="hello world",
            latency_ms=100,
            word_count=2,
        )
    ]

    response = client.post(
        "/api/transcribe",
        files={"file": ("sample.wav", _make_wav(), "audio/wav")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["audio_duration_sec"] > 0
    assert payload["results"][0]["text"] == "hello world"


@patch("stt_arena.main.transcribe_as_completed")
def test_transcribe_progressive_returns_loading_cards(
    mock_stream: AsyncMock,
    client: TestClient,
) -> None:
    async def fake_stream(*_args, **_kwargs):
        yield TranscriptionResult(
            provider_id="openai_whisper",
            status="ok",
            text="hello world",
            latency_ms=100,
            word_count=2,
        )

    mock_stream.side_effect = fake_stream

    start = client.post(
        "/api/transcribe",
        headers={"Accept": "text/html", "X-Progressive": "1"},
        files={"file": ("sample.wav", _make_wav(), "audio/wav")},
    )
    assert start.status_code == 200
    assert "transcribing" in start.text
    assert "data-stream-url" in start.text

    stream_url = "/api/transcribe/sessions/"
    session_path = start.text.split('data-stream-url="', 1)[1].split('"', 1)[0]
    assert session_path.startswith(stream_url)

    with client.stream("GET", session_path) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
        assert "event: result" in body
        assert "hello world" in body
        assert "event: done" in body
