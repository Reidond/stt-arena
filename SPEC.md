# stt-arena

**Status:** MVP implemented  
**Version:** 0.1  
**Last updated:** 2026-05-27

**Project:** stt-arena  
**Description:** Local-first web application to compare multiple Speech-to-Text (STT) providers side-by-side in a masonry grid layout.  
**Goal:** Quickly test and benchmark providers (local Whisper, Deepgram, Google Cloud, OpenAI Whisper, xAI Grok, etc.) with your own audio.

---

## MVP

> Upload a single audio file (WAV/MP3/WebM, ≤25 MB, ≤15 min), transcribe in parallel across all enabled providers, display results in a masonry grid with text, latency, and per-provider errors. No persistence. Runs locally via `uv run`.

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

1. User opens `GET /` → React SPA loads; client fetches providers (`GET /api/providers`) and languages (`GET /api/languages`).
2. User drops, selects, or records an audio file (multiple files supported).
3. Client `POST`s multipart form to `/api/transcribe` with `X-Progressive: 1` and `Accept: application/json`.
4. Server validates audio, normalizes once, returns session JSON (`session_id`, pending providers).
5. Client opens SSE (`GET /api/transcribe/sessions/{id}/events`); providers run in parallel.
6. Each completed provider updates the results workspace (Cards, Table, or Compare view).
7. User exports combined results as CSV or JSON.

---

## Features

### Audio input (v1)

- Upload pre-recorded audio files: WAV, MP3, WebM, OGG, M4A
- Drag-and-drop, file picker, or browser microphone recording
- Multiple files per run (processed sequentially)
- Waveform preview for the selected clip
- Max file size: 25 MB; max duration: 15 minutes (validated server-side)

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
  ├── Jinja2 shell (FastAPI :8000) — mounts React SPA at #root
  └── Vite + React SPA (Tailwind CSS, shadcn/ui components)
        ├── dev:  FastAPI proxies Vite over a Unix socket with HMR
        └── prod: built to static/dist/
        │
        ▼
FastAPI (main.py)
        │
        ├── config.py          ← Pydantic Settings
        ├── audio.py           ← decode/normalize (shared preprocessor)
        ├── sessions.py        ← in-memory SSE session store
        └── ProviderService    ← stt-arena-providers facade
                ├── providers/
                │     ├── deepgram.py
                │     ├── google.py    ← GCS upload for audio > ~59s
                │     ├── openai_whisper.py
                │     └── xai_grok.py
                ├── orchestration.py   ← parallel fan-out + timeouts
                ├── languages.py       ← provider code normalization
                └── billing.py         ← plans + cost estimates
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
        diarization: bool = False,
    ) -> TranscriptionResult:
        """Transcribe normalized WAV bytes. Must not raise; return status=error instead."""
```

---

## API

### `GET /`

Minimal Jinja2 shell that mounts the React SPA at `#root`.

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
| `diarization` | boolean | No | Enables speaker labels where the provider supports diarization |

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

**Progressive UI:** With `X-Progressive: 1`, the POST returns a JSON session payload immediately. React renders loading cards, then receives results via SSE at `GET /api/transcribe/sessions/{session_id}/events`.

### `GET /api/transcribe/sessions/{session_id}/events`

Server-Sent Events stream for a transcription session created by progressive `POST /api/transcribe`.

**Events:**

| Event | Payload | When |
|-------|---------|------|
| `result` | `{"provider_id": "...", "result": {...}}` | One provider finished |
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
| `MAX_AUDIO_DURATION_SEC`      | `900`                    | Max audio duration                               |
| `PROVIDER_TIMEOUT_SEC`        | `120`                    | Per-provider timeout                             |
| `PROVIDER_MAX_ATTEMPTS`       | `3`                      | Max attempts for transient provider failures     |
| `PROVIDER_RETRY_BASE_DELAY_SEC` | `1.0`                  | Initial exponential-backoff delay                 |
| `PROVIDER_RETRY_MAX_DELAY_SEC` | `8.0`                   | Maximum delay between provider attempts           |
| `LOG_LEVEL`                   | `INFO`                   | Python logging level                             |
| `LOG_DIR`                     | `logs`                   | Runtime log directory                            |
| `LOG_FILE`                    | `stt-arena.log`          | Runtime log filename                             |
| `OPENAI_TRANSCRIBE_MODEL`     | `gpt-4o-transcribe`      | OpenAI transcription model                       |
| `OPENAI_DIARIZE_MODEL`        | `gpt-4o-transcribe-diarize` | OpenAI speaker diarization model               |
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
- **Jinja2** – minimal HTML shell for SPA mount
- **React 19** + **TypeScript** – client UI (upload, SSE, comparison views)
- **Vite** – asset pipeline and dev server
- **Tailwind CSS v4** – styling (`@tailwindcss/vite`)
- **Radix UI / shadcn-style components** – accessible UI primitives
- **Pydantic v2** – settings and validation
- **httpx** – async HTTP client for cloud providers
- **ruff** – linter/formatter
- **basedpyright** – type checker
- **pytest** – tests

### UI architecture

FastAPI serves a minimal Jinja2 shell with a `#root` mount point. Vite bundles a React SPA for all interactive UI.

| Mode | HTML | Assets |
|------|------|--------|
| **Dev** (`uv run dev`) | FastAPI `:8000` | Vite over a Unix socket with HMR via `@vite/client` |
| **Prod** | FastAPI | `assets/` → `uv run build` → `static/dist/` + `manifest.json` |

Progressive transcription uses JSON session responses plus SSE result events with structured `result` payloads.

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
├── assets/                     # Vite + React frontend
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx            # React entry
│       ├── App.tsx             # App shell and layout
│       ├── index.css           # Tailwind + design tokens
│       ├── api/                # fetch + SSE clients
│       ├── hooks/              # providers, waveform, recorder, stream
│       ├── components/         # layout, audio, results, ui
│       └── lib/                # export, format, diff helpers
├── src/stt_arena/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entrypoint
│   ├── config.py               # Pydantic Settings
│   ├── audio.py                # Decode, validate, normalize audio
│   ├── sessions.py             # In-memory SSE transcription sessions
│   ├── templates/
│   │   └── index.html          # Minimal shell for the React SPA
│   └── static/
│       └── dist/               # Vite build output (gitignored)
├── packages/
│   ├── stt-arena-providers/    # ProviderService, adapters, billing, languages
│   ├── stt-arena-vite/         # Python-side Vite settings, tags, proxy, assets
│   └── stt-arena-tooling/      # `uv run dev`, `build`, and `start` commands
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

Open http://127.0.0.1:8000 — Vite HMR runs automatically through FastAPI over
a Unix socket in the system temp directory.

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
- Transient provider failures retry with bounded exponential backoff
- Latency displayed per card so users can compare providers directly
- Local Whisper on CPU may exceed cloud latency for longer clips — acceptable

### Reliability

- One provider failing must not fail the request or other providers
- Timeouts and exceptions become `status: "error"` on that provider's result
- Provider failures log safe request context, per-attempt details, and stack traces

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
- [x] File > 25 MB or > 15 min → `400`/`413` with clear message
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
