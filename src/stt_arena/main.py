import json
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from stt_arena.audio import AudioValidationError, prepare_audio
from stt_arena.config import Settings, get_settings
from stt_arena.providers import available_providers, list_provider_statuses
from stt_arena.sessions import TranscriptionSession, create_session, take_session
from stt_arena.transcribe import (
    NoProvidersError,
    transcribe_all,
    transcribe_as_completed,
)
from stt_arena.vite import vite_tags

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))

app = FastAPI(title="stt-arena", version="0.1.0")

if (PACKAGE_DIR / "static" / "dist").is_dir():
    app.mount(
        "/static",
        StaticFiles(directory=str(PACKAGE_DIR / "static")),
        name="static",
    )


class TranscribeResponse(BaseModel):
    audio_duration_sec: float
    results: list[dict[str, object]]


def _wants_html(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _wants_progressive(request: Request) -> bool:
    return request.headers.get("X-Progressive") == "1"


def _display_names(settings: Settings) -> dict[str, str]:
    return {
        item.id: item.display_name for item in list_provider_statuses(settings)
    }


def _render_partial(name: str, **context: object) -> str:
    template = TEMPLATES.env.get_template(name)
    return template.render(**context)


def _enrich_result(
    result: dict[str, object],
    display_names: dict[str, str],
) -> dict[str, object]:
    provider_id = str(result["provider_id"])
    return {
        **result,
        "display_name": display_names.get(provider_id, provider_id),
    }


async def _prepare_upload(
    file: UploadFile | None,
    *,
    max_upload_mb: int,
    max_duration_sec: int,
):
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="Missing audio file")

    data = await file.read()
    max_bytes = max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {max_upload_mb} MB limit",
        )

    try:
        return prepare_audio(
            data,
            content_type=file.content_type,
            filename=file.filename,
            max_upload_mb=max_upload_mb,
            max_duration_sec=max_duration_sec,
        )
    except AudioValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/")
async def index(request: Request):
    settings = get_settings()
    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {
            "settings": settings,
            "vite_tags": vite_tags(settings),
        },
    )


@app.get("/api/providers")
async def list_providers(request: Request):
    settings = get_settings()
    providers = [item.model_dump() for item in list_provider_statuses(settings)]

    if _wants_html(request):
        return TEMPLATES.TemplateResponse(
            request,
            "partials/providers.html",
            {"providers": providers},
        )

    return {"providers": providers}


@app.post("/api/transcribe")
async def transcribe(
    request: Request,
    file: UploadFile | None = File(default=None),
    language: str | None = Form(default=None),
):
    settings = get_settings()
    prepared = await _prepare_upload(
        file,
        max_upload_mb=settings.max_upload_mb,
        max_duration_sec=settings.max_audio_duration_sec,
    )

    if _wants_progressive(request):
        providers = available_providers(settings)
        if not providers:
            raise HTTPException(
                status_code=503,
                detail="No enabled providers are available",
            )

        session_id = create_session(
            TranscriptionSession(
                wav_bytes=prepared.wav_bytes,
                mime_type=prepared.mime_type,
                language=language or None,
                duration_sec=prepared.duration_sec,
                provider_ids=tuple(provider.id for provider in providers),
            )
        )
        display_names = _display_names(settings)
        pending_providers = [
            {"id": provider.id, "display_name": display_names[provider.id]}
            for provider in providers
        ]
        return TEMPLATES.TemplateResponse(
            request,
            "partials/results_pending.html",
            {
                "audio_duration_sec": round(prepared.duration_sec, 1),
                "providers": pending_providers,
                "session_id": session_id,
            },
        )

    try:
        results = await transcribe_all(
            settings,
            prepared.wav_bytes,
            mime_type=prepared.mime_type,
            language=language or None,
            duration_sec=prepared.duration_sec,
        )
    except NoProvidersError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    payload = TranscribeResponse(
        audio_duration_sec=round(prepared.duration_sec, 1),
        results=[result.model_dump() for result in results],
    )

    if _wants_html(request):
        display_names = _display_names(settings)
        enriched = [
            _enrich_result(result, display_names) for result in payload.results
        ]
        return TEMPLATES.TemplateResponse(
            request,
            "partials/results.html",
            {
                "audio_duration_sec": payload.audio_duration_sec,
                "results": enriched,
            },
        )

    return JSONResponse(content=payload.model_dump())


@app.get("/api/transcribe/sessions/{session_id}/events")
async def transcribe_events(session_id: str) -> StreamingResponse:
    session = take_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Transcription session not found")

    settings = get_settings()
    display_names = _display_names(settings)

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for result in transcribe_as_completed(
                settings,
                session.wav_bytes,
                mime_type=session.mime_type,
                language=session.language,
                duration_sec=session.duration_sec,
            ):
                enriched = _enrich_result(result.model_dump(), display_names)
                html = _render_partial("partials/result_card.html", result=enriched)
                payload = json.dumps(
                    {"provider_id": result.provider_id, "html": html},
                    ensure_ascii=False,
                )
                yield f"event: result\ndata: {payload}\n\n"
        except Exception as exc:
            payload = json.dumps({"message": str(exc)}, ensure_ascii=False)
            yield f"event: error\ndata: {payload}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
