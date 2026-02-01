"""OpenAI-compatible models endpoint."""

# pyright: reportMissingImports=false

from fastapi import APIRouter

from app.api.schemas.openai import ModelInfo, ModelsResponse

router = APIRouter()


@router.get("/audio/models", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    """List available TTS models."""

    return ModelsResponse(data=[ModelInfo(id="qwen3-tts-clone", name="Voice Clone")])
