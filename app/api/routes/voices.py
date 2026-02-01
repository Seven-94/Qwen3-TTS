"""OpenAI-compatible voices endpoint."""

# pyright: reportMissingImports=false

from fastapi import APIRouter, Depends

from app.api.dependencies import get_voice_cache
from app.api.schemas.openai import VoiceInfo, VoicesResponse
from app.core.voice_clone_cache import VoiceCloneCache

router = APIRouter()


@router.get("/audio/voices", response_model=VoicesResponse)
async def list_voices(
    voice_cache: VoiceCloneCache = Depends(get_voice_cache),
) -> VoicesResponse:
    """List available cloned voices."""

    if voice_cache.has_voice():
        return VoicesResponse(voices=[VoiceInfo(id="active", name="Voix clonée")])
    return VoicesResponse(voices=[])
