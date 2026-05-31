from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from stt_arena_providers.providers.openai_whisper import (
    OpenAIWhisperProvider,
    _format_diarized_response,
    _select_upload,
)

from stt_arena.config import Settings


def test_select_upload_prefers_supported_source_audio() -> None:
    assert _select_upload(
        b"normalized-wav",
        source_audio=b"compressed-m4a",
        source_filename="meeting.m4a",
        source_mime_type="audio/mp4",
    ) == ("meeting.m4a", b"compressed-m4a", "audio/mp4")


def test_select_upload_falls_back_to_wav_for_unsupported_source() -> None:
    assert _select_upload(
        b"normalized-wav",
        source_audio=b"unsupported-source",
        source_filename="meeting.aac",
        source_mime_type="audio/aac",
    ) == ("audio.wav", b"normalized-wav", "audio/wav")


@pytest.mark.anyio
@patch(
    "stt_arena_providers.providers.openai_whisper._post_transcription",
    new_callable=AsyncMock,
)
async def test_diarization_uses_dedicated_model_and_formats_speaker_segments(
    mock_post_transcription: AsyncMock,
) -> None:
    response = MagicMock()
    response.json.return_value = {
        "text": "raw text",
        "segments": [
            {"speaker": "A", "text": "Hello there."},
            {"speaker": "A", "text": "How are you?"},
            {"speaker": "B", "text": "Doing well."},
        ],
    }
    mock_post_transcription.return_value = response

    provider = OpenAIWhisperProvider(Settings(openai_api_key="test-key"))
    result = await provider.transcribe(
        b"normalized-wav",
        mime_type="audio/wav",
        diarization=True,
    )

    assert result.status == "ok"
    assert result.text == (
        "Speaker A: Hello there. How are you?\n\nSpeaker B: Doing well."
    )
    mock_post_transcription.assert_awaited_once()
    await_args = mock_post_transcription.await_args
    assert await_args is not None
    assert await_args.kwargs["data"] == {
        "model": "gpt-4o-transcribe-diarize",
        "response_format": "diarized_json",
        "chunking_strategy": "auto",
    }
    assert await_args.kwargs["timeout_sec"] == 600.0


def test_format_diarized_response_skips_invalid_segments() -> None:
    assert (
        _format_diarized_response(
            {
                "segments": [
                    {"speaker": "A", "text": "hello"},
                    {"speaker": "B"},
                    {"speaker": None, "text": "missing speaker"},
                    "not an object",
                ],
            }
        )
        == "Speaker A: hello"
    )


@pytest.mark.anyio
@patch("stt_arena_providers.providers.openai_whisper.httpx.AsyncClient")
async def test_transcribe_marks_transport_error_retryable_and_logs_detail(
    mock_client_cls: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = AsyncMock()
    client.post.side_effect = httpx.ReadError("temporary TLS failure")
    context = AsyncMock()
    context.__aenter__.return_value = client
    mock_client_cls.return_value = context

    provider = OpenAIWhisperProvider(Settings(openai_api_key="test-key"))
    with caplog.at_level(logging.ERROR):
        result = await provider.transcribe(
            b"normalized-wav",
            mime_type="audio/mp4",
            source_audio=b"compressed-m4a",
            source_filename="meeting.m4a",
        )

    assert result.status == "error"
    assert result.retryable is True
    assert result.error == "temporary TLS failure"
    client.post.assert_awaited_once()
    files = client.post.await_args.kwargs["files"]
    assert files == {"file": ("meeting.m4a", b"compressed-m4a", "audio/mp4")}
    assert "retryable=True" in caplog.text
    assert "temporary TLS failure" in caplog.text
