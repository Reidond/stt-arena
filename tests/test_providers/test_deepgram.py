from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from stt_arena_providers.providers.deepgram import (
    DeepgramProvider,
    _parse_response,
)

from stt_arena.config import Settings


@pytest.mark.anyio
@patch("stt_arena_providers.providers.deepgram.AsyncDeepgramClient")
async def test_diarization_uses_versioned_model_without_legacy_flag(
    mock_client_cls: MagicMock,
) -> None:
    response = SimpleNamespace(
        results=SimpleNamespace(
            utterances=[
                SimpleNamespace(speaker=0, transcript="hello", confidence=0.9),
                SimpleNamespace(speaker=1, transcript="hi", confidence=0.8),
            ],
        ),
    )
    transcribe_file = AsyncMock(return_value=response)
    client = MagicMock()
    client.listen.v1.media.transcribe_file = transcribe_file
    mock_client_cls.return_value = client

    provider = DeepgramProvider(Settings(deepgram_api_key="test-key"))
    result = await provider.transcribe(
        b"normalized-wav",
        mime_type="audio/wav",
        diarization=True,
    )

    assert result.status == "ok"
    assert result.text == "Speaker 1: hello\n\nSpeaker 2: hi"
    await_args = transcribe_file.await_args
    assert await_args is not None
    kwargs = await_args.kwargs
    assert kwargs["detect_language"] is True
    assert "diarize" not in kwargs
    assert kwargs["diarize_model"] == "latest"
    assert kwargs["utterances"] is True


@pytest.mark.anyio
@patch("stt_arena_providers.providers.deepgram.AsyncDeepgramClient")
async def test_explicit_language_disables_detection(
    mock_client_cls: MagicMock,
) -> None:
    response = SimpleNamespace(
        results=SimpleNamespace(
            channels=[
                SimpleNamespace(
                    alternatives=[
                        SimpleNamespace(transcript="hello", confidence=0.9),
                    ],
                ),
            ],
        ),
    )
    transcribe_file = AsyncMock(return_value=response)
    client = MagicMock()
    client.listen.v1.media.transcribe_file = transcribe_file
    mock_client_cls.return_value = client

    provider = DeepgramProvider(Settings(deepgram_api_key="test-key"))
    result = await provider.transcribe(
        b"normalized-wav",
        mime_type="audio/wav",
        language="uk",
    )

    assert result.status == "ok"
    await_args = transcribe_file.await_args
    assert await_args is not None
    kwargs = await_args.kwargs
    assert kwargs["language"] == "uk"
    assert kwargs["detect_language"] is None


def test_diarization_falls_back_to_word_speakers() -> None:
    response = SimpleNamespace(
        results=SimpleNamespace(
            utterances=[],
            channels=[
                SimpleNamespace(
                    alternatives=[
                        SimpleNamespace(
                            words=[
                                SimpleNamespace(
                                    speaker="0",
                                    word="hello",
                                    punctuated_word="Hello,",
                                ),
                                SimpleNamespace(
                                    speaker="0",
                                    word="there",
                                    punctuated_word="there.",
                                ),
                                SimpleNamespace(
                                    speaker="1",
                                    word="hi",
                                    punctuated_word="Hi.",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    )

    text, confidence = _parse_response(response, diarization_enabled=True)

    assert text == "Speaker 1: Hello, there.\n\nSpeaker 2: Hi."
    assert confidence is None
