from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from stt_arena.config import get_settings
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
async def list_providers():
    settings = get_settings()
    # Stub until provider registry is implemented.
    providers = [
        {
            "id": "whisper_local",
            "display_name": "faster-whisper",
            "enabled": "whisper_local" in settings.enabled_provider_ids,
            "available": "whisper_local" in settings.enabled_provider_ids,
            "reason": None,
        }
    ]
    return {"providers": providers}


@app.post("/api/transcribe")
async def transcribe():
    return JSONResponse(
        status_code=501,
        content={"detail": "Transcription not implemented yet."},
    )
