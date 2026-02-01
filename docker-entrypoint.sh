#!/bin/bash
set -e

mkdir -p /data/cache /data/voices /tmp/numba_cache
chown -R qwen3tts:qwen3tts /data /tmp/numba_cache 2>/dev/null || true
chmod -R 755 /data /tmp/numba_cache 2>/dev/null || true

cd /app

export PATH="/opt/venv/bin:/usr/local/bin:$PATH"
export PYTHONPATH="/app:/opt/venv/lib/python3.12/site-packages"
export VIRTUAL_ENV="/opt/venv"
export PYTHONUNBUFFERED=1
export NUMBA_CACHE_DIR="/tmp/numba_cache"
export NUMBA_DISABLE_CACHING="1"
export NUMBA_DISABLE_PERFORMANCE_WARNINGS="1"

exec runuser -u qwen3tts --preserve-environment -- /opt/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
