# stt-arena

**Status:** Draft  
**Version:** 0.1  
**Last updated:** 2026-05-27

**Project:** stt-arena  
**Description:** Local-first web application to compare multiple Speech-to-Text (STT) providers side-by-side in a masonry grid layout.  
**Goal:** Quickly test and benchmark providers (local Whisper, Deepgram, Google Cloud, OpenAI Whisper, xAI Grok, etc.) with your own audio.

---

## MVP

> Upload a single audio file (WAV/MP3/WebM, ≤25 MB, ≤5 min), transcribe in parallel across all enabled providers, display results in a masonry grid with text, latency, and per-provider errors. No persistence. Runs locally via `uv run`.

### In scope (v1)

- File upload (drag-and-drop + file picker)
- Parallel transcription across enabled providers
- Masonry result cards (provider name, text, latency, word count, optional confidence)
- Provider status page section (available / unavailable / error)
- Graceful per-provider failure (others still complete)
- `.env`-driven provider enablement and API keys

### Out of scope (v1)

- Live browser microphone recording
- User accounts and transcription history
- Batch processing (multiple files)
- Audio waveform visualization
- Export to CSV/JSON
- Per-transcription cost tracking and billing dashboards

---

## User stories

1. As a developer evaluating STT for a product, I upload a sample clip and compare transcripts and latency across providers in one view.
2. As a developer with only local Whisper configured, I run the app with no API keys and still get useful results.
3. As a developer testing a cloud provider, I see a clear error on that provider's card when the API key is missing or the request fails.

---

## User flow

1. User opens `GET /` → page loads provider status (via embedded data or `GET /api/providers`).
2. User selects or drops an audio file.
3. Client `POST`s multipart form to `/api/transcribe`.
4. Server reads audio into memory, normalizes once, fans out to enabled providers in parallel.
5. Server returns aggregated JSON; HTMX swaps in result cards in the masonry grid.
6. Each card shows success fields or an error message for that provider.

---

## Features

### Audio input (v1)

- Upload pre-recorded audio files: WAV, MP3, WebM, OGG, M4A
- Max file size: 25 MB; max duration: 5 minutes (validated server-side)

### Audio input (future)

- Live recording via browser microphone

### Multi-provider comparison

- Run transcription on all enabled providers in parallel (`asyncio.gather(..., return_exceptions=True)`)
- Display results in responsive masonry layout
- Card fields: provider name, transcription text, latency (ms), word count, confidence (when supported)
- Failed providers render an error card; successful providers are unaffected

### Local-first

- Local faster-whisper enabled by default (no API key)
- Cloud providers are opt-in via `ENABLED_PROVIDERS` and credentials

### Configuration

- Providers and API keys managed via `.env`
- Enable/disable providers with a single comma-separated env var

### Extensibility

- All providers implement a shared abstract base class
- New providers: subclass + register in provider registry

---

## Supported providers

| Provider ID       | Display name      | Type  | API key | Confidence | Streaming | Cost (v1) |
|-------------------|-------------------|-------|---------|------------|-----------|-----------|
| `whisper_local`   | faster-whisper    | Local | No      | Segment    | No        | N/A ($0)  |
| `deepgram`        | Deepgram          | Cloud | Yes     | Yes        | Yes*      | Deferred  |
| `google`          | Google Cloud STT  | Cloud | Yes†    | Yes        | Yes*      | Deferred  |
| `openai_whisper`  | OpenAI Whisper    | Cloud | Yes     | No         | No        | Deferred  |
| `xai_grok`        | xAI Grok          | Cloud | Yes     | No         | No        | Deferred  |

\* Streaming supported by provider SDK but not used in v1 (batch upload only).  
† Google uses a service account JSON path, not a simple API key.

**OpenAI vs xAI:** `openai_whisper` calls the OpenAI `/v1/audio/transcriptions` API. `xai_grok` uses the same client shape with `XAI_API_KEY` and `XAI_BASE_URL` (OpenAI-compatible endpoint). They are separate provider IDs so results can be compared side-by-side.

---

## Architecture

```
Browser
  ├── Jinja2 HTML (FastAPI :8000)
  ├── HTMX (upload, partial updates)
  └── Vite assets (Tailwind CSS, client JS)
        ├── dev:  Vite :5173 with HMR
        └── prod: built to static/dist/
        │
        ▼
FastAPI (main.py)
        │
        ├── config.py          ← Pydantic Settings
        ├── audio.py           ← decode/normalize (shared preprocessor)
        └── providers/
                ├── base.py
                ├── whisper_local.py
                ├── deepgram.py
                ├── google.py
                ├── openai_whisper.py
                └── xai_grok.py
                        │
                        └── asyncio.gather → per-provider transcribe()
```

Audio is normalized once to **16 kHz mono PCM (WAV bytes)** before fan-out. Providers that need a different format convert internally if required.

---

## Data models

### `TranscriptionResult`

```python
class TranscriptionResult(BaseModel):
    provider_id: str
    status: Literal["ok", "error"]
    text: str | None = None
    latency_ms: int
    word_count: int | None = None
    confidence: float | None = None  # 0.0–1.0; omit when unsupported
    error: str | None = None
```

### Provider interface

```python
class STTProvider(ABC):
    id: str
    display_name: str

    def is_available(self) -> bool:
        """True when configured and ready (e.g. API key present)."""

    async def transcribe(
        self,
        audio: bytes,
        *,
        mime_type: str,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe normalized WAV bytes. Must not raise; return status=error instead."""
```

---

## API

### `GET /`

Main masonry UI (Jinja2 template).

### `GET /api/providers`

List configured providers and availability.

**Response `200`:**

```json
{
  "providers": [
    {
      "id": "whisper_local",
      "display_name": "faster-whisper",
      "enabled": true,
      "available": true,
      "reason": null
    },
    {
      "id": "deepgram",
      "display_name": "Deepgram",
      "enabled": true,
      "available": false,
      "reason": "DEEPGRAM_API_KEY not set"
    }
  ]
}
```

### `POST /api/transcribe`

Upload audio and transcribe with all enabled, available providers.

**Request:** `multipart/form-data`

| Field      | Type   | Required | Notes                          |
|------------|--------|----------|--------------------------------|
| `file`     | file   | Yes      | WAV, MP3, WebM, OGG, M4A         |
| `language` | string | No       | BCP-47 or ISO 639-1 (e.g. `en`) |

**Response `200`:**

```json
{
  "audio_duration_sec": 10.2,
  "results": [
    {
      "provider_id": "whisper_local",
      "status": "ok",
      "text": "Hello world.",
      "latency_ms": 1240,
      "word_count": 2,
      "confidence": null,
      "error": null
    },
    {
      "provider_id": "deepgram",
      "status": "error",
      "text": null,
      "latency_ms": 842,
      "word_count": null,
      "confidence": null,
      "error": "401 Unauthorized"
    }
  ]
}
```

**Error responses:**

| Status | When                                      |
|--------|-------------------------------------------|
| `400`  | Missing file, unsupported MIME, file too large, duration too long |
| `413`  | Payload exceeds 25 MB                     |
| `503`  | No providers enabled or available         |

Per-provider timeouts do not fail the whole request; they appear as `status: "error"` on that provider's result.

---

## Configuration

Copy `.env.example` to `.env`. All settings load via Pydantic Settings.

| Variable                      | Default                  | Description                                      |
|-------------------------------|--------------------------|--------------------------------------------------|
| `ENABLED_PROVIDERS`           | `whisper_local`          | Comma-separated provider IDs                     |
| `HOST`                        | `127.0.0.1`              | Bind address (local only by default)             |
| `PORT`                        | `8000`                   | Server port                                      |
| `MAX_UPLOAD_MB`               | `25`                     | Max upload size                                  |
| `MAX_AUDIO_DURATION_SEC`      | `300`                    | Max audio duration                               |
| `PROVIDER_TIMEOUT_SEC`        | `120`                    | Per-provider timeout                             |
| `WHISPER_MODEL`               | `base`                   | faster-whisper model (`tiny`, `base`, `small`…)  |
| `WHISPER_DEVICE`              | `cpu`                    | `cpu` or `cuda`                                  |
| `DEEPGRAM_API_KEY`            | —                        | Required when `deepgram` is enabled              |
| `GOOGLE_APPLICATION_CREDENTIALS` | —                     | Path to service account JSON                     |
| `OPENAI_API_KEY`              | —                        | Required when `openai_whisper` is enabled        |
| `OPENAI_BASE_URL`             | `https://api.openai.com/v1` | Override for OpenAI-compatible APIs           |
| `XAI_API_KEY`                 | —                        | Required when `xai_grok` is enabled              |
| `XAI_BASE_URL`                | `https://api.x.ai/v1`    | xAI OpenAI-compatible base URL                   |

**Example `.env`:**

```env
ENABLED_PROVIDERS=whisper_local,deepgram,openai_whisper

WHISPER_MODEL=base
WHISPER_DEVICE=cpu

DEEPGRAM_API_KEY=your_key_here

GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

OPENAI_API_KEY=your_key_here

XAI_API_KEY=your_xai_key_here
```

---

## Tech stack

- **Python 3.13+**
- **uv** – package manager
- **FastAPI** + **Uvicorn** – backend
- **Jinja2** – server-rendered HTML
- **HTMX** – progressive enhancement (upload, swaps)
- **Vite** – asset pipeline (Tailwind CSS, client JS modules)
- **Tailwind CSS v4** – styling (`@tailwindcss/vite`)
- **Pydantic v2** – settings and validation
- **httpx** – async HTTP client for cloud providers
- **ruff** – linter/formatter
- **basedpyright** – type checker
- **pytest** – tests

### UI architecture

Server-rendered HTML stays in Jinja2 templates. Vite is **not** a SPA — it bundles CSS and client-side JS only.

| Mode | HTML | Assets |
|------|------|--------|
| **Dev** (`uv run dev`) | FastAPI `:8000` | Vite `:5173` with HMR via `@vite/client` |
| **Prod** | FastAPI | `assets/` → `uv run build` → `static/dist/` + `manifest.json` |

`stt_arena/vite.py` reads the Vite manifest in production and injects hashed asset URLs into templates.

**Commands:**

```bash
uv run dev     # Vite HMR + Uvicorn reload (development)
uv run build   # Vite production build → static/dist/
uv run start   # Uvicorn without dev mode (requires build first)
```

---

## Project structure

```
stt-arena/
├── assets/                     # Vite asset pipeline (CSS, client JS)
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.ts             # HTMX + future client modules
│       └── style.css           # Tailwind entry
├── src/stt_arena/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entrypoint
│   ├── dev.py                  # `uv run dev` orchestrator
│   ├── build.py                # `uv run build` production asset build
│   ├── start.py                # `uv run start` production server
│   ├── assets_util.py          # Shared npm/Vite helpers
│   ├── config.py               # Pydantic Settings
│   ├── vite.py                 # Dev/prod asset URL helper
│   ├── audio.py                # Decode, validate, normalize audio
│   ├── providers/
│   │   ├── __init__.py         # Provider registry
│   │   ├── base.py             # Abstract base class + TranscriptionResult
│   │   ├── whisper_local.py
│   │   ├── deepgram.py
│   │   ├── google.py
│   │   ├── openai_whisper.py
│   │   └── xai_grok.py
│   ├── templates/
│   │   └── index.html          # Main UI (Jinja2 + HTMX)
│   └── static/
│       └── dist/               # Vite build output (gitignored)
├── tests/
│   ├── test_config.py
│   ├── test_audio.py
│   └── test_providers/
├── pyproject.toml
├── .env.example
├── README.md
└── SPEC.md
```

---

## Setup

**Requirements:** Python 3.13+, [uv](https://docs.astral.sh/uv/), Node.js 20+ (for Vite).

```bash
git clone <repo-url> stt-arena
cd stt-arena
cp .env.example .env
uv sync
uv run dev
```

Open http://127.0.0.1:8000 — Vite HMR runs automatically on port 5173.

**Production:**

```bash
uv run build
uv run start
```

---

## Non-functional requirements

### Privacy

- Audio processed in memory; no persistent storage in v1
- If temporary files are used during decode, delete in a `finally` block
- Never log API keys, credentials paths, or audio content

### Performance

- Providers run in parallel; total wall time ≈ slowest provider (not sum)
- Per-provider timeout: `PROVIDER_TIMEOUT_SEC` (default 120s)
- Latency displayed per card so users can compare providers directly
- Local Whisper on CPU may exceed cloud latency for longer clips — acceptable

### Reliability

- One provider failing must not fail the request or other providers
- Timeouts and exceptions become `status: "error"` on that provider's result

### UI

- Responsive CSS columns masonry grid: desktop (≥1024px) multi-column, mobile single column
- Loading state while transcription is in progress
- Clear distinction between unavailable (not configured) and error (request failed)

### Security (local tool)

- Bind to `127.0.0.1` by default
- Validate MIME type and file size before processing
- Document that binding to `0.0.0.0` exposes an unauthenticated upload endpoint

---

## Acceptance criteria (MVP)

- [ ] Upload a 10s WAV → all enabled, available providers return results within `PROVIDER_TIMEOUT_SEC`
- [ ] Upload MP3/WebM → server normalizes and transcribes successfully
- [ ] One provider misconfigured or failing → other providers still return; failed card shows error
- [ ] Provider with missing API key → listed as `available: false` in `/api/providers`; excluded from transcribe
- [ ] File > 25 MB or > 5 min → `400`/`413` with clear message
- [ ] No audio files remain on disk after request completes
- [ ] App runs with only `whisper_local` enabled and no cloud keys

---

## Testing

| Layer        | What to test                                              |
|--------------|-----------------------------------------------------------|
| Unit         | Settings loading, provider `is_available()`, audio validation |
| Unit         | Each provider with mocked HTTP / SDK responses            |
| Integration  | `POST /api/transcribe` with a short fixture WAV           |
| CI           | `ruff check`, `basedpyright`, `pytest`                    |

Optional: golden-file test — fixed sample WAV, assert non-empty text from `whisper_local`.

---

## Future roadmap

- Live browser microphone recording
- Estimated cost per transcription (provider-specific pricing tables)
- Export results (CSV, JSON)
- Audio waveform visualization
- Batch processing (multiple files)
- Progressive HTMX updates (cards appear as each provider completes)
- User accounts and transcription history

---

*This SPEC.md is the single source of truth for the project.*
