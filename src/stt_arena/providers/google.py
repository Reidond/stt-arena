from __future__ import annotations

import asyncio
import io
import json
import time
import uuid
import wave
from pathlib import Path
from typing import TYPE_CHECKING

from google.cloud import storage
from google.cloud.speech_v1 import SpeechClient
from google.cloud.speech_v1.types import cloud_speech

from stt_arena.providers.base import STTProvider, TranscriptionResult, word_count

if TYPE_CHECKING:
    from stt_arena.config import Settings

# Google inline audio is limited to ~60s even for long-running requests.
SYNC_MAX_DURATION_SEC = 55.0


class GoogleProvider(STTProvider):
    id = "google"
    display_name = "Google Cloud STT"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_available(self) -> bool:
        return _credentials_path(self._settings) is not None

    def unavailable_reason(self) -> str | None:
        if self.is_available():
            return None
        path = self._settings.google_application_credentials
        if not path:
            return "GOOGLE_APPLICATION_CREDENTIALS not set"
        return f"GOOGLE_APPLICATION_CREDENTIALS file not found: {path}"

    async def transcribe(
        self,
        audio: bytes,
        *,
        mime_type: str,
        language: str | None = None,
        duration_sec: float | None = None,
    ) -> TranscriptionResult:
        del mime_type
        started = time.perf_counter()

        try:
            language_code = _to_google_language(language)
            if duration_sec is not None:
                audio_duration = duration_sec
            else:
                audio_duration = _wav_duration_sec(audio)

            needs_gcs = audio_duration > SYNC_MAX_DURATION_SEC
            if needs_gcs and not self._settings.google_storage_bucket:
                msg = (
                    "Google Cloud STT requires GOOGLE_STORAGE_BUCKET for audio "
                    f"longer than {int(SYNC_MAX_DURATION_SEC)}s"
                )
                raise RuntimeError(msg)

            def _run() -> tuple[str, float | None]:
                client = _speech_client(self._settings)
                config = cloud_speech.RecognitionConfig(
                    encoding=cloud_speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=16000,
                    language_code=language_code,
                    enable_automatic_punctuation=True,
                )
                api_timeout = float(self._settings.provider_timeout_sec)
                gcs_uri: str | None = None

                try:
                    if audio_duration > SYNC_MAX_DURATION_SEC:
                        gcs_uri = _upload_audio_to_gcs(self._settings, audio)
                        audio_obj = cloud_speech.RecognitionAudio(uri=gcs_uri)
                        operation = client.long_running_recognize(
                            config=config,
                            audio=audio_obj,
                            timeout=30.0,
                        )
                        response = operation.result(timeout=api_timeout)
                    else:
                        audio_obj = cloud_speech.RecognitionAudio(content=audio)
                        response = client.recognize(
                            config=config,
                            audio=audio_obj,
                            timeout=min(60.0, api_timeout),
                        )
                    return _parse_response(response)
                finally:
                    if gcs_uri is not None:
                        _delete_gcs_blob(self._settings, gcs_uri)

            text, confidence = await asyncio.to_thread(_run)
            latency_ms = int((time.perf_counter() - started) * 1000)
            return TranscriptionResult(
                provider_id=self.id,
                status="ok",
                text=text or None,
                latency_ms=latency_ms,
                word_count=word_count(text),
                confidence=confidence,
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return TranscriptionResult(
                provider_id=self.id,
                status="error",
                latency_ms=latency_ms,
                error=str(exc),
            )


def _credentials_path(settings: Settings) -> Path | None:
    raw = settings.google_application_credentials
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("type") != "service_account":
        return None
    return path


def _speech_client(settings: Settings) -> SpeechClient:
    cred_path = _credentials_path(settings)
    if cred_path is None:
        msg = "Valid Google service account JSON not configured"
        raise RuntimeError(msg)

    return SpeechClient.from_service_account_file(str(cred_path))


def _storage_client(settings: Settings) -> storage.Client:
    cred_path = _credentials_path(settings)
    if cred_path is None:
        msg = "Valid Google service account JSON not configured"
        raise RuntimeError(msg)

    return storage.Client.from_service_account_json(str(cred_path))


def _upload_audio_to_gcs(settings: Settings, audio: bytes) -> str:
    bucket_name = settings.google_storage_bucket
    if not bucket_name:
        msg = (
            "Google Cloud STT requires GOOGLE_STORAGE_BUCKET for audio "
            f"longer than {int(SYNC_MAX_DURATION_SEC)}s"
        )
        raise RuntimeError(msg)

    client = _storage_client(settings)
    blob_name = f"stt-arena/{uuid.uuid4()}.wav"
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(audio, content_type="audio/wav")
    return f"gs://{bucket_name}/{blob_name}"


def _delete_gcs_blob(settings: Settings, uri: str) -> None:
    if not uri.startswith("gs://"):
        return

    bucket_name, blob_name = uri.removeprefix("gs://").split("/", 1)
    try:
        client = _storage_client(settings)
        client.bucket(bucket_name).blob(blob_name).delete()
    except Exception:
        # Best-effort cleanup; transcription already finished or failed.
        return


def _parse_response(
    response: cloud_speech.RecognizeResponse
    | cloud_speech.LongRunningRecognizeResponse,
) -> tuple[str, float | None]:
    parts: list[str] = []
    confidences: list[float] = []
    for result in response.results:
        if not result.alternatives:
            continue
        alt = result.alternatives[0]
        if alt.transcript:
            parts.append(alt.transcript)
        confidences.append(alt.confidence)

    text = " ".join(parts).strip()
    confidence = sum(confidences) / len(confidences) if confidences else None
    return text, confidence


def _wav_duration_sec(audio: bytes) -> float:
    with wave.open(io.BytesIO(audio), "rb") as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        if rate <= 0:
            return 0.0
        return frames / rate


def _to_google_language(language: str | None) -> str:
    if not language:
        return "en-US"
    if "-" in language:
        return language
    return f"{language}-US"
