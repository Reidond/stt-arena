from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TranscriptionSession:
    wav_bytes: bytes
    mime_type: str
    language: str | None
    duration_sec: float
    provider_ids: tuple[str, ...]


_sessions: dict[str, TranscriptionSession] = {}


def create_session(session: TranscriptionSession) -> str:
    session_id = str(uuid.uuid4())
    _sessions[session_id] = session
    return session_id


def take_session(session_id: str) -> TranscriptionSession | None:
    return _sessions.pop(session_id, None)
