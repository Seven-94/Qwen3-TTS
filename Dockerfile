# Qwen3-TTS Application Image
# Uses pre-built base image with FlashAttention 2 compiled
# Build time: ~30 seconds (vs 20-30 minutes for full build)

FROM qwen3-tts-base:latest

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Application environment
ENV PATH="/opt/venv/bin:/usr/local/bin:$PATH"
ENV PYTHONPATH="/app:/opt/venv/lib/python3.12/site-packages"
ENV VIRTUAL_ENV="/opt/venv"
ENV DEVICE="cuda"
ENV DTYPE="bfloat16"
ENV ATTENTION_IMPLEMENTATION="flash_attention_2"
ENV MODELS_DIR="/data/models"
ENV VOICES_DIR="/data/voices"
ENV CACHE_DIR="/data/cache"
ENV NUMBA_CACHE_DIR="/tmp/numba_cache"
ENV NUMBA_DISABLE_PERFORMANCE_WARNINGS=1

WORKDIR /app

# Copy application code
COPY --chown=qwen3tts:qwen3tts app/ ./app/
COPY --chown=qwen3tts:qwen3tts qwen_tts/ ./qwen_tts/
COPY --chown=qwen3tts:qwen3tts pyproject.toml uv.lock ./
COPY --chown=qwen3tts:qwen3tts install_flash_attn2.sh ./
COPY --chown=qwen3tts:qwen3tts --chmod=755 docker-entrypoint.sh ./

# Create required directories with proper permissions
RUN mkdir -p /data/models /data/voices /data/cache /tmp/numba_cache && \
    chown -R qwen3tts:qwen3tts /data /tmp/numba_cache && \
    chmod -R 755 /tmp/numba_cache

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Use entrypoint to fix permissions before starting
ENTRYPOINT ["/app/docker-entrypoint.sh"]
