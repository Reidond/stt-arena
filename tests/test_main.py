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


def test_index_includes_react_refresh_preamble_in_dev(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STT_ARENA_DEV", "1")
    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "@react-refresh" in response.text
    assert "__vite_plugin_react_preamble_installed__" in response.text
    get_settings.cache_clear()


@patch("stt_arena.vite_proxy.httpx.AsyncClient")
def test_vite_dev_proxy_serves_node_modules(
    mock_client_cls: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STT_ARENA_DEV", "1")
    get_settings.cache_clear()

    mock_response = AsyncMock()
    mock_response.content = b"font-bytes"
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "font/woff2"}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.request = AsyncMock(return_value=mock_response)
    mock_client_cls.return_value = mock_client

    client = TestClient(app)
    response = client.get(
        "/node_modules/@fontsource/geist-sans/files/geist-sans-latin-400-normal.woff2",
    )
    assert response.status_code == 200
    assert response.content == b"font-bytes"
    mock_client.request.assert_awaited_once()
    get_settings.cache_clear()


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
def test_transcribe_progressive_returns_session_json(
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
        headers={"Accept": "application/json", "X-Progressive": "1"},
        files={"file": ("sample.wav", _make_wav(), "audio/wav")},
    )
    assert start.status_code == 200
    payload = start.json()
    assert "session_id" in payload
    assert payload["providers"]
    assert payload["audio_duration_sec"] > 0

    session_path = f"/api/transcribe/sessions/{payload['session_id']}/events"
    with client.stream("GET", session_path) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
        assert "event: result" in body
        assert "hello world" in body
        assert "event: done" in body


@patch("stt_arena.main.transcribe_as_completed")
def test_transcribe_progressive_returns_loading_cards_html(
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

    session_path = start.text.split('data-stream-url="', 1)[1].split('"', 1)[0]
    with client.stream("GET", session_path) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
        assert "event: result" in body
        assert "hello world" in body
        assert "event: done" in body
