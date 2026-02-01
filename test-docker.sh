#!/bin/bash
# Test script for Qwen3-TTS Docker setup
# Run this after: docker-compose up -d --build

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[TEST]${NC} $1"; }
error() { echo -e "${RED}[FAIL]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

log "═══════════════════════════════════════════════════════════"
log "Qwen3-TTS Docker Test Script"
log "═══════════════════════════════════════════════════════════"

# Test 1: Container is running
log "Test 1: Checking if container is running..."
if docker ps | grep -q qwen3-tts-unified; then
    log "✓ Container is running"
else
    error "✗ Container is not running"
    exit 1
fi

# Test 2: No FlashAttention error in logs
log "Test 2: Checking for FlashAttention errors..."
if docker logs qwen3-tts-unified 2>&1 | grep -i "flashattention not found"; then
    error "✗ FlashAttention error found in logs"
    exit 1
else
    log "✓ No FlashAttention errors"
fi

# Test 3: Health endpoint
log "Test 3: Testing /health endpoint..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log "✓ Health endpoint responding"
        break
    fi
    if [ $i -eq 30 ]; then
        error "✗ Health endpoint not responding after 30 attempts"
        exit 1
    fi
    sleep 2
done

# Test 4: API endpoints
log "Test 4: Testing API endpoints..."
if curl -s http://localhost:8000/v1/audio/models > /dev/null 2>&1; then
    log "✓ /v1/audio/models endpoint working"
else
    warn "⚠ /v1/audio/models endpoint not responding (may need model load)"
fi

# Test 5: Check voice files
log "Test 5: Checking voice files in container..."
VOICE_COUNT=$(docker exec qwen3-tts-unified ls -1 /data/voices/ 2>/dev/null | wc -l)
if [ "$VOICE_COUNT" -gt 0 ]; then
    log "✓ Found $VOICE_COUNT voice file(s) in /data/voices/"
else
    warn "⚠ No voice files found in /data/voices/"
fi

# Test 6: Check models
log "Test 6: Checking model files in container..."
MODEL_COUNT=$(docker exec qwen3-tts-unified ls -1 /data/models/ 2>/dev/null | wc -l)
if [ "$MODEL_COUNT" -gt 0 ]; then
    log "✓ Found $MODEL_COUNT model directory(ies) in /data/models/"
else
    warn "⚠ No model files found in /data/models/"
fi

log ""
log "═══════════════════════════════════════════════════════════"
log "Basic tests passed! ✓"
log "═══════════════════════════════════════════════════════════"
log ""
log "Next steps:"
log "  1. Open http://localhost:8000/ui in your browser"
log "  2. Go to 'Voice Clone' tab"
log "  3. Verify voice files are visible"
log "  4. Test model loading"
log ""
log "To view logs: docker-compose logs -f qwen3-tts-unified"
log "To stop: docker-compose down"
log "═══════════════════════════════════════════════════════════"
