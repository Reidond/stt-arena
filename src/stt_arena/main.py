import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from stt_arena_providers import NoProvidersError, ProviderService
from stt_arena_vite import (
    register_vite_dev_proxy,
    start_vite_dev_proxy,
    stop_vite_dev_proxy,
    vite_tags,
)

from stt_arena.audio import AudioValidationError, prepare_audio
from stt_arena.config import get_settings
from stt_arena.logging_config import configure_logging
from stt_arena.sessions import TranscriptionSession, create_session, take_session

PACKAGE_DIR = Path(__file__).resolve().parent
VITE_MANIFEST_PATH = PACKAGE_DIR / "static" / "dist" / ".vite" / "manifest.json"
TEMPLATES = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    log_path = configure_logging(settings)
    logger.info("STT Arena starting; logs=%s", log_path)
    await start_vite_dev_proxy(app, settings)
    try:
        yield
    finally:
        await stop_vite_dev_proxy(app)
        logger.info("STT Arena shutting down")


app = FastAPI(title="STT Arena", version="0.1.0", lifespan=lifespan)

app.mount(
    "/static",
    StaticFiles(directory=str(PACKAGE_DIR / "static")),
    name="static",
)


class TranscribeResponse(BaseModel):
    audio_duration_sec: float
    results: list[dict[str, object]]


def _wants_progressive(request: Request) -> bool:
    return request.headers.get("X-Progressive") == "1"


def _enrich_result(
    result: dict[str, object],
    display_names: dict[str, str],
    *,
    providers: ProviderService,
    duration_sec: float | None = None,
) -> dict[str, object]:
    provider_id = str(result["provider_id"])
    enriched: dict[str, object] = {
        **result,
        "display_name": display_names.get(provider_id, provider_id),
    }
    if duration_sec is not None and result.get("status") == "ok":
        cost = providers.estimate_cost(
            provider_id,
            duration_sec,
        )
        if cost is not None:
            enriched["cost"] = cost.model_dump()
            enriched["estimated_cost_usd"] = cost.usd
    return enriched


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
        logger.warning(
            "Rejected upload %s: %s bytes exceeds %s MB",
            file.filename,
            len(data),
            max_upload_mb,
        )
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
        logger.warning("Rejected upload %s: %s", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/")
async def index(request: Request):
    settings = get_settings()
    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {
            "vite_tags": vite_tags(settings, manifest_path=VITE_MANIFEST_PATH),
            "is_dev": settings.is_dev,
        },
    )


@app.get("/api/languages")
async def list_languages():
    providers = ProviderService(get_settings())
    return {"languages": providers.language_options()}


@app.get("/api/providers")
async def list_providers():
    settings = get_settings()
    providers = ProviderService(settings).status_payloads()
    return {"providers": providers}


@app.get("/api/billing/plans")
async def list_billing_plans():
    providers = ProviderService(get_settings())
    return {"plans": providers.billing_plan_payloads()}


@app.post("/api/transcribe")
async def transcribe(
    request: Request,
    file: UploadFile | None = File(default=None),
    language: str | None = Form(default=None),
    diarization: bool = Form(default=False),
):
    settings = get_settings()
    provider_service = ProviderService(settings)
    try:
        canonical_language = provider_service.resolve_language(language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    prepared = await _prepare_upload(
        file,
        max_upload_mb=settings.max_upload_mb,
        max_duration_sec=settings.max_audio_duration_sec,
    )

    if _wants_progressive(request):
        providers = provider_service.available()
        if not providers:
            logger.warning("Transcription rejected: no providers available")
            raise HTTPException(
                status_code=503,
                detail="No enabled providers are available",
            )

        session_id = create_session(
            TranscriptionSession(
                wav_bytes=prepared.wav_bytes,
                source_bytes=prepared.source_bytes,
                source_filename=prepared.source_filename,
                mime_type=prepared.mime_type,
                language=canonical_language,
                diarization=diarization,
                duration_sec=prepared.duration_sec,
                provider_ids=tuple(provider.id for provider in providers),
            )
        )
        display_names = provider_service.display_names()
        pending_providers = [
            {"id": provider.id, "display_name": display_names[provider.id]}
            for provider in providers
        ]
        logger.info(
            "Created transcription session %s for %.1fs audio with providers=%s",
            session_id,
            prepared.duration_sec,
            ",".join(provider.id for provider in providers),
        )
        progressive_payload = {
            "session_id": session_id,
            "audio_duration_sec": round(prepared.duration_sec, 1),
            "providers": pending_providers,
        }
        return JSONResponse(content=progressive_payload)

    try:
        results = await provider_service.transcribe_all(
            prepared.wav_bytes,
            mime_type=prepared.mime_type,
            source_audio=prepared.source_bytes,
            source_filename=prepared.source_filename,
            language=canonical_language,
            duration_sec=prepared.duration_sec,
            diarization=diarization,
        )
    except NoProvidersError as exc:
        logger.warning("Transcription rejected: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    payload = TranscribeResponse(
        audio_duration_sec=round(prepared.duration_sec, 1),
        results=[result.model_dump() for result in results],
    )

    return JSONResponse(content=payload.model_dump())


@app.get("/api/transcribe/sessions/{session_id}/events")
async def transcribe_events(session_id: str) -> StreamingResponse:
    session = take_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Transcription session not found")

    settings = get_settings()
    provider_service = ProviderService(settings)
    display_names = provider_service.display_names()

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for result in provider_service.transcribe_as_completed(
                session.wav_bytes,
                mime_type=session.mime_type,
                source_audio=session.source_bytes,
                source_filename=session.source_filename,
                language=session.language,
                duration_sec=session.duration_sec,
                diarization=session.diarization,
            ):
                enriched = _enrich_result(
                    result.model_dump(),
                    display_names,
                    providers=provider_service,
                    duration_sec=session.duration_sec,
                )
                payload = json.dumps(
                    {
                        "provider_id": result.provider_id,
                        "result": enriched,
                    },
                    ensure_ascii=False,
                )
                yield f"event: result\ndata: {payload}\n\n"
        except Exception as exc:
            logger.exception("Transcription session %s failed", session_id)
            payload = json.dumps({"message": str(exc)}, ensure_ascii=False)
            yield f"event: error\ndata: {payload}\n\n"
        done_payload = json.dumps(
            {"audio_duration_sec": round(session.duration_sec, 1)},
            ensure_ascii=False,
        )
        yield f"event: done\ndata: {done_payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


register_vite_dev_proxy(app, get_settings)
