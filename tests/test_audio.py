from __future__ import annotations

import io
import wave

import pytest

from stt_arena.audio import (
    AudioValidationError,
    prepare_audio,
    validate_mime_type,
)


def _ffmpeg_available() -> bool:
    import shutil

    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _make_wav(duration_sec: float = 0.5, sample_rate: int = 16000) -> bytes:
    frame_count = int(duration_sec * sample_rate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frame_count)
    return buffer.getvalue()


def test_validate_mime_type_accepts_wav() -> None:
    assert validate_mime_type("audio/wav", "sample.wav") == "audio/wav"


def test_validate_mime_type_accepts_extension_fallback() -> None:
    assert validate_mime_type(None, "sample.mp3") == "audio/mpeg"


def test_validate_mime_type_rejects_unknown() -> None:
    with pytest.raises(AudioValidationError):
        validate_mime_type("text/plain", "notes.txt")


@pytest.mark.skipif(
    not _ffmpeg_available(),
    reason="ffmpeg required for audio normalization tests",
)
def test_prepare_audio_normalizes_wav() -> None:
    wav = _make_wav()
    prepared = prepare_audio(
        wav,
        content_type="audio/wav",
        filename="sample.wav",
        max_upload_mb=25,
        max_duration_sec=300,
    )
    assert prepared.mime_type == "audio/wav"
    assert prepared.duration_sec > 0
    assert prepared.wav_bytes.startswith(b"RIFF")


def test_prepare_audio_rejects_empty_file() -> None:
    with pytest.raises(AudioValidationError, match="empty"):
        prepare_audio(
            b"",
            content_type="audio/wav",
            filename="empty.wav",
            max_upload_mb=25,
            max_duration_sec=300,
        )


def test_prepare_audio_rejects_oversized_payload() -> None:
    with pytest.raises(AudioValidationError, match="25 MB"):
        prepare_audio(
            b"x" * (26 * 1024 * 1024),
            content_type="audio/wav",
            filename="large.wav",
            max_upload_mb=25,
            max_duration_sec=300,
        )

