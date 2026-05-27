from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from google.api_core.client_options import ClientOptions
from google.cloud import storage
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

from stt_arena.audio import wav_duration_sec
from stt_arena.provider_timeouts import (
    GOOGLE_SYNC_MAX_DURATION_SEC,
    google_batch_operation_timeout_sec,
)
from stt_arena.providers.base import STTProvider, TranscriptionResult, word_count

if TYPE_CHECKING:
    from stt_arena.config import Settings

SYNC_MAX_DURATION_SEC = GOOGLE_SYNC_MAX_DURATION_SEC


class GoogleProvider(STTProvider):
    id = "google"
    display_name = "Google Cloud STT (Chirp 3)"

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
            language_codes = [language] if language else ["auto"]
            # Route on the normalized WAV we upload, not container metadata.
            audio_duration = wav_duration_sec(audio)
            if audio_duration <= 0 and duration_sec is not None:
                audio_duration = duration_sec

            needs_batch = audio_duration > SYNC_MAX_DURATION_SEC
            if needs_batch and not self._settings.google_storage_bucket:
                msg = (
                    "Google Cloud STT requires GOOGLE_STORAGE_BUCKET for audio "
                    f"longer than {int(SYNC_MAX_DURATION_SEC)}s"
                )
                raise RuntimeError(msg)

            def _run() -> tuple[str, float | None]:
                client = _speech_client(self._settings)
                project_id = _project_id(self._settings)
                region = self._settings.google_speech_region
                recognizer = (
                    f"projects/{project_id}/locations/{region}/recognizers/_"
                )
                config = cloud_speech.RecognitionConfig(
                    auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                    language_codes=language_codes,
                    model=self._settings.google_speech_model,
                )
                api_timeout = float(self._settings.provider_timeout_sec)
                batch_timeout = google_batch_operation_timeout_sec(
                    self._settings,
                    audio_duration,
                )
                gcs_uri: str | None = None

                try:
                    if needs_batch:
                        gcs_uri = _upload_audio_to_gcs(self._settings, audio)
                        file_metadata = cloud_speech.BatchRecognizeFileMetadata(
                            uri=gcs_uri,
                        )
                        request = cloud_speech.BatchRecognizeRequest(
                            recognizer=recognizer,
                            config=config,
                            files=[file_metadata],
                            recognition_output_config=cloud_speech.RecognitionOutputConfig(
                                inline_response_config=cloud_speech.InlineOutputConfig(),
                            ),
                        )
                        operation = client.batch_recognize(request=request)
                        response = operation.result(timeout=batch_timeout)
                        return _parse_batch_response(response, gcs_uri)
                    request = cloud_speech.RecognizeRequest(
                        recognizer=recognizer,
                        config=config,
                        content=audio,
                    )
                    response = client.recognize(
                        request=request,
                        timeout=min(60.0, api_timeout),
                    )
                    return _parse_recognize_response(response)
                finally:
                    if gcs_uri is not None:
                        _delete_gcs_blob(self._settings, gcs_uri)

            text, confidence = await asyncio.to_thread(_run)
            if not text:
                msg = "Google returned an empty transcript"
                raise RuntimeError(msg)
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


def _project_id(settings: Settings) -> str:
    cred_path = _credentials_path(settings)
    if cred_path is None:
        msg = "Valid Google service account JSON not configured"
        raise RuntimeError(msg)
    payload = json.loads(cred_path.read_text(encoding="utf-8"))
    project_id = payload.get("project_id")
    if not isinstance(project_id, str) or not project_id:
        msg = "Google service account JSON is missing project_id"
        raise RuntimeError(msg)
    return project_id


def _speech_client(settings: Settings) -> SpeechClient:
    cred_path = _credentials_path(settings)
    if cred_path is None:
        msg = "Valid Google service account JSON not configured"
        raise RuntimeError(msg)

    region = settings.google_speech_region
    return SpeechClient.from_service_account_file(
        str(cred_path),
        client_options=ClientOptions(api_endpoint=f"{region}-speech.googleapis.com"),
    )


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
        return


def _parse_recognize_response(
    response: cloud_speech.RecognizeResponse | cloud_speech.BatchRecognizeResults,
) -> tuple[str, float | None]:
    parts: list[str] = []
    for result in response.results:
        if not result.alternatives:
            continue
        alt = result.alternatives[0]
        if alt.transcript:
            parts.append(alt.transcript)

    text = " ".join(parts).strip()
    # Chirp 3 always returns confidence=0.0; Google docs say it is not meaningful.
    return text, None


def _batch_file_error_message(
    file_result: cloud_speech.BatchRecognizeFileResult,
) -> str | None:
    error = file_result.error
    if error is None:
        return None
    code = getattr(error, "code", 0)
    if not code:
        return None
    message = getattr(error, "message", "") or f"Google batch error code {code}"
    return message.strip()


def _batch_transcript_results(
    file_result: cloud_speech.BatchRecognizeFileResult,
) -> cloud_speech.BatchRecognizeResults | None:
    inline = file_result.inline_result
    if inline is not None and inline.transcript is not None:
        return inline.transcript
    if file_result.transcript is not None:
        return file_result.transcript
    return None


def _lookup_batch_file_result(
    response: cloud_speech.BatchRecognizeResponse,
    audio_uri: str,
) -> cloud_speech.BatchRecognizeFileResult:
    file_result = response.results.get(audio_uri)
    if file_result is not None:
        return file_result
    if len(response.results) == 1:
        return next(iter(response.results.values()))
    keys = ", ".join(response.results)
    msg = f"Google batch response missing result for {audio_uri} (got: {keys})"
    raise RuntimeError(msg)


def _parse_batch_response(
    response: cloud_speech.BatchRecognizeResponse,
    audio_uri: str,
) -> tuple[str, float | None]:
    file_result = _lookup_batch_file_result(response, audio_uri)
    error_message = _batch_file_error_message(file_result)
    if error_message:
        raise RuntimeError(error_message)

    transcript = _batch_transcript_results(file_result)
    if transcript is None:
        msg = "Google batch returned no transcript payload"
        raise RuntimeError(msg)

    return _parse_recognize_response(transcript)
