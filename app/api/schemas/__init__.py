"""API schemas module."""

from app.api.schemas.openai import (
    ModelInfo,
    ModelsResponse,
    SpeechRequest,
    TranscribeRequest,
    VoiceInfo,
    VoicesResponse,
)

__all__ = [
    "ModelInfo",
    "ModelsResponse",
    "SpeechRequest",
    "TranscribeRequest",
    "VoiceInfo",
    "VoicesResponse",
]
