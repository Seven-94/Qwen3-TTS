"""OpenAI-compatible transcription endpoint."""

# pyright: reportMissingImports=false

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.dependencies import get_model_manager
from app.core.model_manager import ModelManager

router = APIRouter()


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    model: str = Form("whisper-1"),
    model_manager: ModelManager = Depends(get_model_manager),
) -> dict:
    """Transcribe audio using the ASR model."""

    if not model_manager.is_loaded("voice_clone"):
        model_manager.load_model("voice_clone", with_asr=True)

    status = model_manager.get_status()
    if not status.get("asr_loaded"):
        model_manager.load_model("voice_clone", with_asr=True)

    asr_pipeline = model_manager._asr_model
    if asr_pipeline is None:
        raise HTTPException(status_code=500, detail="ASR model not loaded")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio file")

    suffix = Path(file.filename or "audio.wav").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(data)
        temp_path = temp_file.name

    try:
        result = asr_pipeline(temp_path)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {exc}",
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    text = result.get("text", "").strip() if isinstance(result, dict) else ""
    return {"text": text}
