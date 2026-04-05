"""FastAPI application entry point with Gradio mounted.

This module creates the main FastAPI application and mounts a Gradio
interface at the /ui path.
"""

# pyright: reportMissingImports=false

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr

from app.api.routes import (
    models_router,
    speech_router,
    status_router,
    transcribe_router,
    voices_router,
)
from app.config import Settings

settings = Settings()


def get_gradio_app() -> gr.Blocks:
    """Import and create the real Gradio application."""
    from app.ui.gradio_app import create_app

    return create_app()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown."""
    print(f"Starting Qwen3-TTS Unified on {settings.API_HOST}:{settings.API_PORT}")
    yield
    print("Shutting down Qwen3-TTS Unified")


app = FastAPI(
    title="Qwen3-TTS Unified API",
    description="OpenAI-compatible TTS API with Gradio UI",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(speech_router, prefix="/v1", tags=["audio"])
app.include_router(voices_router, prefix="/v1", tags=["audio"])
app.include_router(models_router, prefix="/v1", tags=["models"])
app.include_router(transcribe_router, prefix="/v1", tags=["audio"])
app.include_router(status_router, prefix="/v1", tags=["status"])


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


gradio_interface = get_gradio_app()
app = gr.mount_gradio_app(app, gradio_interface, path="/ui")
