"""API routes module."""

from app.api.routes.models import router as models_router
from app.api.routes.speech import router as speech_router
from app.api.routes.status import router as status_router
from app.api.routes.transcribe import router as transcribe_router
from app.api.routes.voices import router as voices_router

__all__ = [
    "models_router",
    "speech_router",
    "status_router",
    "transcribe_router",
    "voices_router",
]
