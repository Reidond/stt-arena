from google.cloud.speech_v2.types import cloud_speech
from google.rpc import status_pb2
from stt_arena_providers.providers.google import (
    _batch_file_error_message,
    _lookup_batch_file_result,
    _parse_batch_response,
    _parse_recognize_response,
)


def _speech_result(transcript: str) -> cloud_speech.SpeechRecognitionResult:
    return cloud_speech.SpeechRecognitionResult(
        alternatives=[cloud_speech.SpeechRecognitionAlternative(transcript=transcript)],
    )


def _word(word: str, speaker_label: str) -> cloud_speech.WordInfo:
    return cloud_speech.WordInfo(word=word, speaker_label=speaker_label)


def test_parse_batch_response_reads_inline_result() -> None:
    transcript = cloud_speech.BatchRecognizeResults(
        results=[_speech_result("hello batch")],
    )
    file_result = cloud_speech.BatchRecognizeFileResult(
        inline_result=cloud_speech.InlineResult(transcript=transcript),
    )
    response = cloud_speech.BatchRecognizeResponse(
        results={"gs://bucket/audio.wav": file_result},
    )

    text, confidence = _parse_batch_response(response, "gs://bucket/audio.wav")
    assert text == "hello batch"
    assert confidence is None


def test_parse_recognize_response_formats_diarization_words() -> None:
    response = cloud_speech.RecognizeResponse(
        results=[
            cloud_speech.SpeechRecognitionResult(
                alternatives=[
                    cloud_speech.SpeechRecognitionAlternative(
                        transcript="hello there hi",
                        words=[
                            _word("hello", "1"),
                            _word("there", "1"),
                            _word("hi", "2"),
                        ],
                    )
                ],
            )
        ],
    )

    text, confidence = _parse_recognize_response(
        response,
        diarization_enabled=True,
    )
    assert text == "Speaker 1: hello there\n\nSpeaker 2: hi"
    assert confidence is None


def test_parse_batch_response_surfaces_file_error() -> None:
    file_result = cloud_speech.BatchRecognizeFileResult(
        error=status_pb2.Status(code=3, message="invalid config"),
    )
    response = cloud_speech.BatchRecognizeResponse(
        results={"gs://bucket/audio.wav": file_result},
    )

    try:
        _parse_batch_response(response, "gs://bucket/audio.wav")
    except RuntimeError as exc:
        assert "invalid config" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_batch_file_error_message_ignores_success() -> None:
    file_result = cloud_speech.BatchRecognizeFileResult(
        error=status_pb2.Status(code=0, message="ok"),
    )
    assert _batch_file_error_message(file_result) is None


def test_lookup_batch_file_result_falls_back_to_single_entry() -> None:
    file_result = cloud_speech.BatchRecognizeFileResult(
        inline_result=cloud_speech.InlineResult(
            transcript=cloud_speech.BatchRecognizeResults(
                results=[_speech_result("fallback")],
            ),
        ),
    )
    response = cloud_speech.BatchRecognizeResponse(
        results={"gs://bucket/other.wav": file_result},
    )
    resolved = _lookup_batch_file_result(response, "gs://bucket/expected.wav")
    alt = resolved.inline_result.transcript.results[0].alternatives[0]
    assert alt.transcript == "fallback"
