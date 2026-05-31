from __future__ import annotations

import io
import wave
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from stt_arena_providers import TranscriptionResult

from stt_arena.config import get_settings
from stt_arena.main import app


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
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
    by_id = {item["id"]: item for item in payload["providers"]}
    assert by_id["deepgram"]["supports_diarization"] is True
    assert by_id["openai_whisper"]["supports_diarization"] is True
    assert by_id["xai_grok"]["supports_diarization"] is True


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


@patch("stt_arena_vite.proxy.httpx.AsyncClient")
def test_vite_dev_proxy_serves_node_modules(
    mock_client_cls: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STT_ARENA_DEV", "1")
    get_settings.cache_clear()

    mock_response = AsyncMock()
    mock_response.content = b"font-bytes"
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "font/woff2"}

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)
    mock_client.aclose = AsyncMock()
    mock_client_cls.return_value = mock_client

    with TestClient(app) as client:
        first_response = client.get(
            "/node_modules/"
            "@fontsource/geist-sans/files/geist-sans-latin-400-normal.woff2",
        )
        second_response = client.get(
            "/node_modules/"
            "@fontsource/geist-sans/files/geist-sans-latin-500-normal.woff2",
        )

    assert first_response.status_code == 200
    assert first_response.content == b"font-bytes"
    assert second_response.status_code == 200
    assert second_response.content == b"font-bytes"
    mock_client_cls.assert_called_once()
    assert mock_client.request.await_count == 2
    await_args = mock_client.request.await_args_list[0]
    method, target = await_args.args[:2]
    assert method == "GET"
    assert target == (
        "http://vite/node_modules/"
        "@fontsource/geist-sans/files/geist-sans-latin-400-normal.woff2"
    )
    mock_client.aclose.assert_awaited_once()
    get_settings.cache_clear()


def test_transcribe_missing_file(client: TestClient) -> None:
    response = client.post("/api/transcribe")
    assert response.status_code == 400


@patch("stt_arena.main.ProviderService.transcribe_all", new_callable=AsyncMock)
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
    await_args = mock_transcribe.await_args
    assert await_args is not None
    assert await_args.kwargs["diarization"] is False


@patch("stt_arena.main.ProviderService.transcribe_all", new_callable=AsyncMock)
def test_transcribe_passes_diarization_setting(
    mock_transcribe: AsyncMock,
    client: TestClient,
) -> None:
    mock_transcribe.return_value = [
        TranscriptionResult(
            provider_id="deepgram",
            status="ok",
            text="Speaker 1: hello",
            latency_ms=100,
            word_count=3,
        )
    ]

    response = client.post(
        "/api/transcribe",
        data={"diarization": "true"},
        files={"file": ("sample.wav", _make_wav(), "audio/wav")},
    )
    assert response.status_code == 200
    await_args = mock_transcribe.await_args
    assert await_args is not None
    assert await_args.kwargs["diarization"] is True


@patch("stt_arena.main.ProviderService.transcribe_as_completed")
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
        data={"diarization": "true"},
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
    call_args = mock_stream.call_args
    assert call_args is not None
    assert call_args.kwargs["diarization"] is True
