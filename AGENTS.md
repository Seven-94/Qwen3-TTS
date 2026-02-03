This file provides guidance for AI agents working in this repository.

The repo contains:

- The upstream `qwen_tts` Python package.
- A **Unified Interface** application under `app/`:
  - A Gradio UI mounted under FastAPI at `/ui`.
  - An OpenAI-compatible REST API under `/v1` (for Open-WebUI and similar).

---

## Project Status (February 2026)

### Recent Major Changes

**New Files Added**:

- `Dockerfile.base` - Single-stage CUDA 13.0 + FlashAttention 2 image
- `docker-compose.yml` - Container orchestration with GPU support
- `docker-entrypoint.sh` - Startup script with proper permissions and Numba fix
- `.dockerignore` - Excludes build artifacts and sensitive files
- `app/` - Complete Unified Interface application (25 files)
- `test-docker.sh` - Validation script for container testing
- `start.sh` - Local development startup script
- `.env.example` - Configuration template
- Documentation: `README-DOCKER.md`, `AGENTS.md`, `UV_SETUP.md`

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
bash install_flash_attn2.sh
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

## Docker Deployment

### Prerequisites

- Docker Engine 24.0+ with NVIDIA Container Toolkit (for GPU support)
- NVIDIA drivers installed on host
- Model files downloaded to `./modele_tts/` directory

### Quick Start with Docker Compose

```bash
# 1. Copy and configure environment
cp .env.example .env

# 2. Build and start (first time ~20-30 min for FlashAttention compilation)
docker-compose up -d --build

# 3. View logs
docker-compose logs -f qwen3-tts-unified

# 4. Test the deployment
./test-docker.sh
```

### Docker Compose Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Stop and remove volumes (WARNING: clears cache)
docker-compose down -v

# Rebuild after Dockerfile changes
docker-compose build --no-cache

# View logs
docker-compose logs -f qwen3-tts-unified
```

### Manual Docker Build

```bash
# Build image
docker build -f Dockerfile.base -t qwen3-tts:latest .

# Run with GPU support
docker run -d \
  --name qwen3-tts-unified \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/modele_tts:/data/models:ro \
  -v $(pwd)/voices:/data/voices \
  -v $(pwd)/cache:/data/cache \
  -v $(pwd)/.env:/app/.env:ro \
  qwen3-tts:latest
```

### Docker Volume Mounts

The container expects these volume mounts:

| Host Path      | Container Path | Purpose                                    |
| -------------- | -------------- | ------------------------------------------ |
| `./modele_tts` | `/data/models` | TTS model weights (read-only)              |
| `./voices`     | `/data/voices` | Voice reference files for cloning          |
| `./cache`      | `/data/cache`  | Persistent cache (cloned voices, HF cache) |
| `./.env`       | `/app/.env`    | Configuration file (read-only)             |

### GPU Support

Ensure NVIDIA Container Toolkit is installed:

```bash
# Test GPU access
docker run --rm --gpus all nvidia/cuda:13.0.2-runtime-ubuntu24.04 nvidia-smi
```

### Technical Notes

**Container User:** The container runs as non-root user `qwen3tts` with UID 1001 (to avoid conflicts with the default Ubuntu 24.04 user).

**Flash Attention 2:** Automatically installed during the Docker build for optimal GPU performance. The compilation requires the CUDA devel image (includes `nvcc`).

**Numba Cache Fix:** The `docker-entrypoint.sh` sets `NUMBA_CACHE_DIR=/tmp/numba_cache` and `NUMBA_DISABLE_CACHING=1` to prevent librosa/numba cache errors.

**Build Time:** First build takes ~20-30 minutes due to FlashAttention compilation. Subsequent builds are faster.

---

## Repository layout (Unified Interface)

```
app/
├── api/              # OpenAI-compatible REST API (/v1)
│   ├── routes/       # speech, voices, models, transcribe, status
│   └── schemas/      # Pydantic models for OpenAI compatibility
├── core/             # ModelManager and VoiceClone cache
│   ├── model_manager.py      # Smart model loading/switching
│   └── voice_clone_cache.py  # Persistent voice storage
├── ui/               # Gradio UI (3 tabs)
│   ├── tabs/         # custom_voice_tab, voice_design_tab, voice_clone_tab
│   └── components/   # shared UI widgets
├── config.py         # Settings (pydantic-settings)
└── main.py           # FastAPI entry point + mount Gradio
```

Key runtime directories (not meant to be committed):

- `modele_tts/` — local model folders (weights)
- `voices/` — reference audio files for cloning (can upload via UI)
- `cache/` — persistent cache (e.g., last cloned voice)
- `.env` — local configuration

### Voice Upload Feature

Users can upload voice reference files directly from the Gradio UI (Voice Clone tab → "📤 Upload New Voice" accordion). Supported formats: `.mp3`, `.wav`, `.flac`, `.opus`.

**Permissions handling**: The `voices/` folder may have incorrect permissions if created by Docker (owned by UID 1001). The `start.sh` script automatically detects and fixes this at startup (requires sudo if the folder is not writable).

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

1. Clone a voice once via the UI (Voice Clone tab).

2. Configure Open-WebUI (Admin Settings → Audio):

| Setting             | Value                                     |
| ------------------- | ----------------------------------------- |
| TTS Engine          | `OpenAI`                                  |
| OpenAI API Base URL | `http://localhost:8000/v1`                |
| OpenAI API Key      | `dummy-key` (or your `QWEN3_TTS_API_KEY`) |
| Voice               | `active`                                  |
| Model               | `qwen3-tts-clone`                         |

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

## Known Issues & Solutions

### Numba Cache Error

**Symptom:** `RuntimeError: cannot cache function '__o_fold': no locator available`
**Solution:** Fixed in `docker-entrypoint.sh` with `NUMBA_DISABLE_CACHING=1` and writable `/tmp/numba_cache` directory.

### CUDA/nvcc Not Found

**Symptom:** `FileNotFoundError: [Errno 2] No such file or directory: '/usr/local/cuda/bin/nvcc'`
**Solution:** Use `nvidia/cuda:13.0.2-cudnn-devel-ubuntu24.04` (devel image) instead of runtime image.

### UV Path Issues

**Symptom:** `/opt/venv/bin/uv: not found`
**Solution:** Use `/usr/local/bin/uv` (system UV) with `--python /opt/venv/bin/python` flag.

### Container Restart Loop

**Symptom:** Container keeps restarting, only showing CUDA banner
**Solution:** Ensure `docker-entrypoint.sh` is properly copied and executable in the image.

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
- Don't commit secrets or large artifacts:
  - `.env`, `cache/`, `voices/`, `modele_tts/`, `.venv/`, `__pycache__/`, `.sisyphus/`
- Prefer committing `uv.lock` (dependency pinning / reproducibility).
- If you introduce new tooling (ruff/pytest config), update `pyproject.toml`
  and keep it consistent with existing dependencies.

---

## Agent-specific notes

When working on this codebase:

1. **Always check the current branch** - Most work should be on `dev_perso`
2. **Don't modify files outside `.sisyphus/` directly** - Use subagents for implementation
3. **Document blockers immediately** - If you encounter environment limitations (e.g., no Docker access), document extensively
4. **Test Docker changes** - If modifying Docker files, ensure the build actually works
5. **Preserve memory management** - The ModelManager's one-model-at-a-time behavior is critical for VRAM usage
6. **Update AGENTS.md** - When making significant changes, update this file
