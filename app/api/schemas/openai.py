# pyright: reportMissingImports=false
"""OpenAI-compatible API schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field


class SpeechRequest(BaseModel):
    """Request payload for speech synthesis."""

    model: str = Field(..., description="Model identifier")
    input: str = Field(..., description="Text to synthesize")
    voice: Optional[str] = Field(None, description="Voice identifier")
    response_format: Optional[str] = Field(
        "mp3",
        description="Desired audio format (mp3 or wav)",
    )
    speed: Optional[float] = Field(
        1.0,
        description="Speech speed multiplier",
    )


class VoiceInfo(BaseModel):
    """Voice metadata."""

    id: str
    name: str


class ModelInfo(BaseModel):
    """Model metadata."""

    id: str
    name: str


class VoicesResponse(BaseModel):
    """Response payload for available voices."""

    voices: List[VoiceInfo]


class ModelsResponse(BaseModel):
    """Response payload for available models."""

    data: List[ModelInfo]


class TranscribeRequest(BaseModel):
    """Request payload for transcription."""

    model: Optional[str] = Field(
        "whisper-1",
        description="ASR model identifier",
    )
