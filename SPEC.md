# stt-arena

**Status:** MVP implemented  
**Version:** 0.1  
**Last updated:** 2026-05-27

**Project:** stt-arena  
**Description:** Local-first web application to compare multiple Speech-to-Text (STT) providers side-by-side in a masonry grid layout.  
**Goal:** Quickly test and benchmark providers (local Whisper, Deepgram, Google Cloud, OpenAI Whisper, xAI Grok, etc.) with your own audio.

---

## MVP

> Upload a single audio file (WAV/MP3/WebM, ≤25 MB, ≤5 min), transcribe in parallel across all enabled providers, display results in a masonry grid with text, latency, and per-provider errors. No persistence. Runs locally via `uv run`.

### In scope (v1)

- File upload (drag-and-drop, file picker, and microphone recording)
- Batch upload (multiple files processed sequentially)
- Parallel transcription across enabled providers
- Masonry result cards (provider name, text, latency, word count, optional confidence, billing plan cost)
- Waveform preview for selected audio
- Export results to CSV/JSON
- Provider status page section (available / unavailable / error)
- Graceful per-provider failure (others still complete)
- `.env`-driven provider enablement and API keys

### Out of scope (v1)

- User accounts and transcription history
- Per-transcription cost tracking using provider-specific billing plans (official rates, rounding, free tiers)
- CI test automation

---

## User stories

1. As a developer evaluating STT for a product, I upload a sample clip and compare transcripts and latency across providers in one view.
2. As a developer with only local Whisper configured, I run the app with no API keys and still get useful results.
3. As a developer testing a cloud provider, I see a clear error on that provider's card when the API key is missing or the request fails.

---

## User flow

1. User opens `GET /` → provider status loads via HTMX (`GET /api/providers`).
2. User drops, selects, or records an audio file (multiple files supported).
3. Client `POST`s multipart form to `/api/transcribe` with `X-Progressive: 1`.
4. Server validates audio, normalizes once, returns loading skeleton cards.
5. Client opens SSE (`GET /api/transcribe/sessions/{id}/events`); providers run in parallel.
6. Each completed provider swaps its card in the masonry grid (fastest first).
7. User exports combined results as CSV or JSON.

---

## Features

### Audio input (v1)

- Upload pre-recorded audio files: WAV, MP3, WebM, OGG, M4A
- Drag-and-drop, file picker, or browser microphone recording
- Multiple files per run (processed sequentially)
- Waveform preview for the selected clip
- Max file size: 25 MB; max duration: 5 minutes (validated server-side)

### Audio input (future)

- Live streaming transcription (not just record-then-upload)

### Multi-provider comparison

- Run transcription on all enabled providers in parallel (`asyncio.gather` / `asyncio.as_completed`)
- Display results in responsive masonry layout; cards stream in via SSE as each provider finishes
- Card fields: provider name, transcription text, latency (ms or seconds when ≥ 1s), word count, confidence (when supported), cost (plan label, billable duration, USD)
- Export all results as CSV or JSON after a run completes
- Failed providers render an error card; successful providers are unaffected
- Upload form locked while a transcription is in progress

### Local-first

- Default enabled provider is `openai_whisper` (cloud)
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
| `deepgram`        | Deepgram          | Cloud | Yes     | Yes        | Yes*      | Deferred  |
| `google`          | Google Cloud STT  | Cloud | Yes†    | Yes        | Yes*      | Deferred  |
| `openai_whisper`  | OpenAI GPT-4o Transcribe | Cloud | Yes | No    | No        | Deferred  |
| `xai_grok`        | xAI Grok          | Cloud | Yes     | No         | No        | Deferred  |

\* Streaming supported by provider SDK but not used in v1 (batch upload only).  
† Google uses a service account JSON path, not a simple API key.

**OpenAI vs xAI:** `openai_whisper` calls the OpenAI `/v1/audio/transcriptions` API. `xai_grok` uses the xAI `/v1/stt` endpoint with `XAI_API_KEY` and `XAI_BASE_URL`. They are separate provider IDs so results can be compared side-by-side.

---

## Architecture

```
Browser
  ├── Jinja2 HTML (FastAPI :8000)
  ├── HTMX (provider status panel)
  └── Vite assets (Tailwind CSS, client JS — upload, SSE)
        ├── dev:  Vite :5173 with HMR
        └── prod: built to static/dist/
        │
        ▼
FastAPI (main.py)
        │
        ├── config.py          ← Pydantic Settings
        ├── audio.py           ← decode/normalize (shared preprocessor)
        ├── transcribe.py      ← parallel fan-out + timeouts
        ├── sessions.py        ← in-memory SSE session store
        └── providers/
                ├── base.py
                ├── deepgram.py
                ├── google.py    ← GCS upload for audio > ~59s
                ├── openai_whisper.py
                └── xai_grok.py
                        │
                        └── asyncio → per-provider transcribe()
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
      "id": "openai_whisper",
      "display_name": "OpenAI GPT-4o Transcribe",
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

Enabled providers include a `billing` object with the active plan and rate.

### `GET /api/billing/plans`

Catalog of supported billing plans with official rates, rounding rules, and which plan is active per provider.

**Response `200`:**

```json
{
  "plans": [
    {
      "id": "nova-2-batch-payg",
      "provider_id": "deepgram",
      "label": "Deepgram Nova-2 · batch · PAYG",
      "model": "nova-2",
      "billing_mode": "batch",
      "usd_per_minute": 0.0043,
      "free_minutes_monthly": 0,
      "pricing_url": "https://deepgram.com/pricing",
      "active_for_provider": true
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
      "provider_id": "openai_whisper",
      "status": "ok",
      "text": "Hello world.",
      "latency_ms": 1240,
      "word_count": 2,
      "confidence": null,
      "error": null,
      "cost": {
        "usd": 0.001,
        "plan_id": "gpt-4o-transcribe",
        "plan_label": "OpenAI GPT-4o Transcribe",
        "billable_duration_sec": 10.2,
        "rate_usd_per_minute": 0.006
      }
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

**Progressive UI:** With `X-Progressive: 1`, the POST returns loading cards immediately; results stream via SSE at `GET /api/transcribe/sessions/{session_id}/events`.

### `GET /api/transcribe/sessions/{session_id}/events`

Server-Sent Events stream for a transcription session created by progressive `POST /api/transcribe`.

**Events:**

| Event | Payload | When |
|-------|---------|------|
| `result` | `{"provider_id": "...", "html": "...", "result": {...}}` | One provider finished |
| `error` | `{"message": "..."}` | Stream-level failure |
| `done` | `{"audio_duration_sec": 10.2}` | All providers finished |

---

## Configuration

Copy `.env.example` to `.env`. All settings load via Pydantic Settings.

| Variable                      | Default                  | Description                                      |
|-------------------------------|--------------------------|--------------------------------------------------|
| `ENABLED_PROVIDERS`           | `openai_whisper`         | Comma-separated provider IDs                     |
| `HOST`                        | `127.0.0.1`              | Bind address (local only by default)             |
| `PORT`                        | `8000`                   | Server port                                      |
| `MAX_UPLOAD_MB`               | `25`                     | Max upload size                                  |
| `MAX_AUDIO_DURATION_SEC`      | `300`                    | Max audio duration                               |
| `PROVIDER_TIMEOUT_SEC`        | `120`                    | Per-provider timeout                             |
| `OPENAI_TRANSCRIBE_MODEL`     | `gpt-4o-transcribe`      | OpenAI transcription model                       |
| `DEEPGRAM_MODEL`              | `nova-3`                 | Deepgram model                                   |
| `GOOGLE_SPEECH_MODEL`         | `chirp_3`                | Google Speech-to-Text v2 model                   |
| `GOOGLE_SPEECH_REGION`        | `us`                     | Google STT region (`us`, `eu`, …)                |
| `DEEPGRAM_API_KEY`            | —                        | Required when `deepgram` is enabled              |
| `GOOGLE_APPLICATION_CREDENTIALS` | —                     | Path to service account JSON                     |
| `GOOGLE_STORAGE_BUCKET`       | —                        | GCS bucket for Google audio longer than ~60s     |
| `OPENAI_API_KEY`              | —                        | Required when `openai_whisper` is enabled        |
| `OPENAI_BASE_URL`             | `https://api.openai.com/v1` | Override for OpenAI-compatible APIs           |
| `XAI_API_KEY`                 | —                        | Required when `xai_grok` is enabled              |
| `XAI_BASE_URL`                | `https://api.x.ai/v1`    | xAI OpenAI-compatible base URL                   |
| `BILLING_PLAN_*`              | per provider             | Billing plan ID (see `GET /api/billing/plans`)   |
| `BILLING_MONTHLY_MINUTES_*`   | `0`                      | Minutes used this month (free/volume tier calc)  |

**Example `.env`:**

```env
ENABLED_PROVIDERS=openai_whisper,deepgram,google

OPENAI_API_KEY=your_key_here

DEEPGRAM_API_KEY=your_key_here

GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
GOOGLE_STORAGE_BUCKET=your-bucket-name

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
uv run dev     # Vite HMR + Uvicorn (no reload)
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
│       ├── main.ts             # App bootstrap
│       ├── transcribe.ts       # Upload, SSE, batch, export
│       ├── record.ts           # Microphone capture
│       ├── waveform.ts         # Waveform preview
│       ├── export.ts           # CSV/JSON download helpers
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
│   ├── cost.py                 # Billing plans and cost calculation
│   ├── transcribe.py           # Parallel fan-out orchestration
│   ├── sessions.py             # In-memory SSE transcription sessions
│   ├── providers/
│   │   ├── __init__.py         # Provider registry
│   │   ├── base.py             # Abstract base class + TranscriptionResult
│   │   ├── deepgram.py
│   │   ├── google.py
│   │   ├── openai_whisper.py
│   │   └── xai_grok.py
│   ├── templates/
│   │   ├── index.html          # Main UI
│   │   └── partials/           # Provider panel, result cards, SSE shell
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

- [x] Upload a 10s WAV → all enabled, available providers return results within `PROVIDER_TIMEOUT_SEC`
- [x] Upload MP3/WebM → server normalizes and transcribes successfully
- [x] One provider misconfigured or failing → other providers still return; failed card shows error
- [x] Provider with missing API key → listed as `available: false` in `/api/providers`; excluded from transcribe
- [x] File > 25 MB or > 5 min → `400`/`413` with clear message
- [x] No audio files remain on disk after request completes (ffmpeg temps and GCS objects cleaned up)
- [x] Drag-and-drop, microphone recording, batch upload, waveform preview, and CSV/JSON export

---

## Testing

Manual verification is sufficient for v1. Optional local checks:

```bash
uv run ruff check src
uv run basedpyright src
uv run pytest
```

## Future roadmap

- Live streaming transcription (real-time partial results while speaking)
- User accounts and transcription history

---

*This SPEC.md is the single source of truth for the project.*
