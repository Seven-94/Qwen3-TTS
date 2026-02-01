"""OpenAI-compatible status endpoint."""

# pyright: reportMissingImports=false

from fastapi import APIRouter, Depends

from app.api.dependencies import get_model_manager
from app.core.model_manager import ModelManager

router = APIRouter()


@router.get("/status")
async def get_status(
    model_manager: ModelManager = Depends(get_model_manager),
) -> dict:
    """Return model status and GPU information."""

    return model_manager.get_status()
