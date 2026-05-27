from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".webm",
    ".ogg",
    ".m4a",
    ".mp4",
    ".mpeg",
    ".mpga",
}

SUPPORTED_MIME_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/vnd.wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/webm",
    "audio/ogg",
    "application/ogg",
    "audio/mp4",
    "audio/x-m4a",
    "audio/m4a",
    "video/webm",
}


class AudioValidationError(ValueError):
    """Raised when uploaded audio fails validation."""


@dataclass(frozen=True, slots=True)
class PreparedAudio:
    wav_bytes: bytes
    duration_sec: float
    mime_type: str


def validate_mime_type(content_type: str | None, filename: str | None) -> str:
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized in SUPPORTED_MIME_TYPES:
        return normalized

    if filename:
        ext = Path(filename).suffix.lower()
        if ext in SUPPORTED_EXTENSIONS:
            return _mime_from_extension(ext)

    msg = (
        "Unsupported audio format. Allowed: WAV, MP3, WebM, OGG, M4A "
        f"(got {content_type or 'unknown type'})"
    )
    raise AudioValidationError(msg)


def prepare_audio(
    data: bytes,
    *,
    content_type: str | None,
    filename: str | None,
    max_upload_mb: int,
    max_duration_sec: int,
) -> PreparedAudio:
    if not data:
        raise AudioValidationError("Uploaded file is empty")

    max_bytes = max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        msg = f"File exceeds {max_upload_mb} MB limit"
        raise AudioValidationError(msg)

    mime_type = validate_mime_type(content_type, filename)
    wav_bytes = normalize_to_wav(data, filename=filename)
    duration_sec = wav_duration_sec(wav_bytes)
    if duration_sec > max_duration_sec:
        msg = (
            f"Audio duration {duration_sec:.1f}s exceeds "
            f"{max_duration_sec}s limit"
        )
        raise AudioValidationError(msg)

    return PreparedAudio(
        wav_bytes=wav_bytes,
        duration_sec=duration_sec,
        mime_type=mime_type,
    )


def wav_duration_sec(data: bytes) -> float:
    with wave.open(io.BytesIO(data), "rb") as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        if rate <= 0:
            return 0.0
        return frames / rate


def probe_duration(data: bytes, *, filename: str | None) -> float:
    ffprobe = _require_binary("ffprobe")
    suffix = _suffix_for_filename(filename)

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)

    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(tmp_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip() or "ffprobe failed"
        raise AudioValidationError(stderr) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise AudioValidationError("Could not determine audio duration") from exc


def normalize_to_wav(data: bytes, *, filename: str | None) -> bytes:
    ffmpeg = _require_binary("ffmpeg")
    suffix = _suffix_for_filename(filename)

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as src:
        src.write(data)
        src_path = Path(src.name)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as dst:
        dst_path = Path(dst.name)

    try:
        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(src_path),
                "-ar",
                "16000",
                "-ac",
                "1",
                "-f",
                "wav",
                str(dst_path),
            ],
            check=True,
            capture_output=True,
        )
        return dst_path.read_bytes()
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        msg = stderr or "ffmpeg failed to decode audio"
        raise AudioValidationError(msg) from exc
    finally:
        src_path.unlink(missing_ok=True)
        dst_path.unlink(missing_ok=True)


def _require_binary(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        msg = f"{name} is required for audio processing but was not found on PATH"
        raise AudioValidationError(msg)
    return path


def _suffix_for_filename(filename: str | None) -> str:
    if filename:
        ext = Path(filename).suffix.lower()
        if ext:
            return ext
    return ".bin"


def _mime_from_extension(ext: str) -> str:
    mapping = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".webm": "audio/webm",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".mp4": "audio/mp4",
        ".mpeg": "audio/mpeg",
        ".mpga": "audio/mpeg",
    }
    return mapping.get(ext, "application/octet-stream")
