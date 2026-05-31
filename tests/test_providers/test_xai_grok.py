from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from stt_arena_providers.providers.xai_grok import (
    XAIGrokProvider,
    _format_diarized_response,
)

from stt_arena.config import Settings


@pytest.mark.anyio
@patch("stt_arena_providers.providers.xai_grok.httpx.AsyncClient")
async def test_diarization_sends_flag_and_formats_speaker_words(
    mock_client_cls: MagicMock,
) -> None:
    response = MagicMock()
    response.json.return_value = {
        "text": "raw text",
        "words": [
            {"speaker": 0, "text": "Hello"},
            {"speaker": 0, "text": "there."},
            {"speaker": 1, "text": "Hi."},
        ],
    }
    client = AsyncMock()
    client.post.return_value = response
    context = AsyncMock()
    context.__aenter__.return_value = client
    mock_client_cls.return_value = context

    provider = XAIGrokProvider(Settings(xai_api_key="test-key"))
    result = await provider.transcribe(
        b"normalized-wav",
        mime_type="audio/wav",
        language="en",
        diarization=True,
    )

    assert result.status == "ok"
    assert result.text == "Speaker 1: Hello there.\n\nSpeaker 2: Hi."
    client.post.assert_awaited_once()
    assert client.post.await_args.kwargs["data"] == {
        "diarize": "true",
        "language": "en",
    }


def test_format_diarized_response_skips_invalid_words() -> None:
    assert (
        _format_diarized_response(
            {
                "words": [
                    {"speaker": 0, "text": "hello"},
                    {"speaker": 1},
                    {"speaker": None, "text": "missing speaker"},
                    "not an object",
                ],
            }
        )
        == "Speaker 1: hello"
    )
