This file provides guidance for AI agents working in this repository.

The repo contains:
- The upstream `qwen_tts` Python package.
- A **Unified Interface** application under `app/`:
  - A Gradio UI mounted under FastAPI at `/ui`.
  - An OpenAI-compatible REST API under `/v1` (for Open-WebUI and similar).

---

## Environment setup (UV)

Use **uv** to manage the virtual environment and dependencies.

```bash
uv sync
```

Run commands inside the environment via:

```bash
uv run <command>
```

### FlashAttention

To install FlashAttention with the proper CUDA configuration, use:

```bash
bash install_flash_attn.sh
```

This script installs PyTorch (CUDA 13.0 wheel index) and compiles
FlashAttention inside the UV environment.

---

## Unified Interface: how to run

### Option A (recommended)

```bash
./start.sh
```

### Option B (manual)

```bash
uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Default endpoints:
- UI: `http://localhost:8000/ui`
- API: `http://localhost:8000/v1`
- Health: `http://localhost:8000/health`
- Docs: `http://localhost:8000/docs`

---

## Repository layout (Unified Interface)

```
app/
├── api/              # OpenAI-compatible REST API (/v1)
│   ├── routes/       # speech, voices, models, transcribe, status
│   └── schemas/      # Pydantic models for OpenAI compatibility
├── core/             # ModelManager and VoiceClone cache
├── ui/               # Gradio UI (3 tabs)
│   ├── tabs/         # custom_voice_tab, voice_design_tab, voice_clone_tab
│   └── components/   # shared UI widgets
├── config.py         # Settings (pydantic-settings)
└── main.py           # FastAPI entry point + mount Gradio
```

Key runtime directories (not meant to be committed):
- `modele_tts/` — local model folders (weights)
- `voices/` — reference audio files for cloning
- `cache/` — persistent cache (e.g., last cloned voice)
- `.env` — local configuration

---

## OpenAI-compatible API (for Open-WebUI)

Primary endpoints:
- `POST /v1/audio/speech` — synthesize speech (MP3)
- `GET /v1/audio/voices` — list available voices (`active` when a clone is ready)
- `GET /v1/audio/models` — list available models
- `POST /v1/transcribe` — ASR transcription (Whisper)
- `GET /v1/status` — server + GPU status

Authentication:
- Simple API key via `QWEN3_TTS_API_KEY`.

---

## Open-WebUI configuration

1) Clone a voice once via the UI (Voice Clone tab).

2) Configure Open-WebUI (Admin Settings → Audio):

| Setting | Value |
|---|---|
| TTS Engine | `OpenAI` |
| OpenAI API Base URL | `http://localhost:8000/v1` |
| OpenAI API Key | `dummy-key` (or your `QWEN3_TTS_API_KEY`) |
| Voice | `active` |
| Model | `qwen3-tts-clone` |

---

## Configuration (.env)

Use `.env.example` as a template.

Important variables:
- `QWEN3_TTS_API_KEY`
- `API_HOST`, `API_PORT`
- `DEVICE`, `DTYPE`, `ATTENTION_IMPLEMENTATION`
- `MODELS_DIR`, `VOICES_DIR`, `CACHE_DIR`
- `ASR_MODEL`, `ASR_DEVICE`
- `OUTPUT_FORMAT` (expected: `mp3`), `OUTPUT_SAMPLE_RATE`

---

## Memory / model-loading rules

The Unified Interface is designed to reduce VRAM usage:
- Only **one TTS model** should be loaded at a time.
- The Voice Clone flow may additionally load an ASR model.
- The last cloned voice is cached on disk to survive restarts.

When modifying the ModelManager or tab switching logic, preserve this behavior.

---

## Coding conventions

### Project structure

This codebase is not strictly `src/`-layout; follow existing structure.

### Style

- Keep functions short and focused.
- Prefer snake_case for functions/variables and PascalCase for classes.
- Keep lines reasonably short (target 79–100 chars).

### Imports

- Standard library first, then third-party, then local imports.
- Group imports with blank lines.
- Avoid wildcard imports (`from x import *`).

### Type hints

- Add type hints for all public functions/methods.
- Prefer explicit types over `Any`.
- Use `Optional[T]` instead of `Union[T, None]`.

### Docstrings

Use Google-style docstrings for public functions and classes.

### Data validation

Use Pydantic models for API schemas and validate inputs early.

### Error handling

- Raise specific exception types (`ValueError`, `TypeError`, `RuntimeError`).
- Provide clear error messages.
- Never silence errors with bare `except:`.

---

## Development workflow

- Prefer minimal, focused changes (avoid drive-by refactors in bug fixes).
- Don’t commit secrets or large artifacts:
  - `.env`, `cache/`, `voices/`, `modele_tts/`, `.venv/`, `__pycache__/`, `.sisyphus/`
- Prefer committing `uv.lock` (dependency pinning / reproducibility).
- If you introduce new tooling (ruff/pytest config), update `pyproject.toml`
  and keep it consistent with existing dependencies.
