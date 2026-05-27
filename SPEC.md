# stt-arena

**Project:** stt-arena  
**Description:** Local-first web application to compare multiple Speech-to-Text (STT) providers side-by-side in a masonry grid layout.  
**Goal:** Quickly test and benchmark providers (Deepgram, local Whisper, Google Cloud, Grok/xAI, etc.) with your own audio.

## Features

- **Audio Input**
  - Live recording via browser microphone
  - Upload pre-recorded audio files (WAV, MP3, etc.)
- **Multi-Provider Comparison**
  - Run transcription on all configured providers in parallel
  - Display results in responsive masonry layout (cards with provider name, transcription, latency, confidence, word count, estimated cost)
- **Local-First**
  - Prioritize local Whisper (faster-whisper) when configured
  - Cloud providers as fallback or additional options
- **Configuration**
  - Providers and API keys managed via `.env` file
  - Easy to enable/disable providers
- **Extensibility**
  - Simple base class for adding new STT providers

## Supported Providers (initial)

| Provider          | Type     | Notes                          |
|-------------------|----------|--------------------------------|
| faster-whisper    | Local    | Default, no API key needed     |
| Deepgram          | Cloud    | High accuracy, fast            |
| Google Cloud STT  | Cloud    | Requires service account       |
| OpenAI Whisper    | Cloud    | Compatible with Grok ecosystem |
| Custom            | Any      | Implement via base class       |

## Tech Stack

- **Python 3.12+**
- **uv** – fast package manager
- **FastAPI** + **Uvicorn** – backend
- **HTMX** + **Tailwind CSS** + **Masonry.js** – modern frontend (no heavy JS framework)
- **Pydantic v2** – settings & validation
- **httpx** – async HTTP client
- **ruff** – linter/formatter
- **basedpyright** – type checker

## Project Structure

```
stt-arena/
├── src/stt_arena/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entrypoint
│   ├── config.py               # Pydantic Settings (providers, keys)
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract base class
│   │   ├── whisper_local.py
│   │   ├── deepgram.py
│   │   ├── google.py
│   │   └── openai_whisper.py
│   ├── templates/
│   │   └── index.html          # Main UI with masonry grid
│   └── static/
│       ├── css/
│       └── js/
├── pyproject.toml
├── .env.example
├── README.md
└── SPEC.md
```

## API Endpoints

- `GET /` — Main masonry UI
- `POST /api/transcribe` — Upload audio → returns JSON with results from all active providers
- `GET /api/providers` — List configured providers and status

## Configuration (.env.example)

```env
# Local
WHISPER_MODEL=base

# Deepgram
DEEPGRAM_API_KEY=your_key_here

# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# OpenAI / Grok
OPENAI_API_KEY=your_key_here
```

## Initial Setup Commands

```bash
uv init stt-arena
cd stt-arena
uv add "fastapi[standard]" uvicorn python-multipart pydantic-settings httpx faster-whisper deepgram-sdk google-cloud-speech
uv add --dev ruff basedpyright
uv sync
```

## Non-Functional Requirements

- Privacy-first: audio never stored server-side unless explicitly requested
- Performance: < 3 seconds for 10-second audio on all providers
- Responsive design: works on desktop and mobile
- Error handling: graceful degradation if one provider fails

## Future Roadmap

- Cost tracking per transcription
- Export results (CSV, JSON)
- Audio waveform visualization
- Batch processing
- User accounts & history

---

*This SPEC.md is the single source of truth for the project.*