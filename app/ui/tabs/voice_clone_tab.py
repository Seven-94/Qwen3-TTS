"""Voice Clone tab for Qwen3-TTS Gradio UI.

Allows voice cloning from audio files with optional ASR transcription.
"""

import os
import shutil
import gradio as gr
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Any, List

from app.core.model_manager import model_manager
from app.core.voice_clone_cache import voice_cache
from app.config import Settings

settings = Settings()

# Supported audio formats for voice cloning
ALLOWED_AUDIO_EXTENSIONS = [".wav", ".mp3", ".flac", ".opus"]


def get_voice_files() -> List[str]:
    """Get list of audio files in voices directory."""
    voices_dir = Path(settings.VOICES_DIR)
    voices_dir.mkdir(exist_ok=True)
    files = sorted(
        [
            str(f)
            for f in voices_dir.glob("*")
            if f.suffix.lower() in ALLOWED_AUDIO_EXTENSIONS
        ]
    )
    return files


def upload_voice_file(file) -> Tuple[gr.Dropdown, str]:
    """Upload a voice file to the voices directory.

    Args:
        file: Uploaded file from Gradio File component.

    Returns:
        Tuple of (updated dropdown choices, status message).
    """
    if file is None:
        return gr.Dropdown(choices=get_voice_files()), "❌ No file selected."

    # Get file path (Gradio provides a temp file path)
    src_path = Path(file.name if hasattr(file, "name") else file)
    filename = src_path.name
    extension = src_path.suffix.lower()

    # Validate extension
    if extension not in ALLOWED_AUDIO_EXTENSIONS:
        allowed = ", ".join(ALLOWED_AUDIO_EXTENSIONS)
        return (
            gr.Dropdown(choices=get_voice_files()),
            f"❌ Invalid format '{extension}'. Allowed: {allowed}",
        )

    # Destination path
    voices_dir = Path(settings.VOICES_DIR)
    voices_dir.mkdir(exist_ok=True)
    dest_path = voices_dir / filename

    # Handle duplicates: add suffix if file exists
    if dest_path.exists():
        base = src_path.stem
        counter = 1
        while dest_path.exists():
            dest_path = voices_dir / f"{base}_{counter}{extension}"
            counter += 1

    try:
        shutil.copy2(src_path, dest_path)
        return (
            gr.Dropdown(choices=get_voice_files(), value=str(dest_path)),
            f"✅ Uploaded: {dest_path.name}",
        )
    except Exception as e:
        return (
            gr.Dropdown(choices=get_voice_files()),
            f"❌ Upload failed: {e}",
        )


def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio using loaded ASR model."""
    if not audio_path:
        raise gr.Error("No audio selected.")

    try:
        if not model_manager.is_loaded("voice_clone"):
            # Load with ASR enabled
            model_manager.load_model("voice_clone", with_asr=True)

        # Check if ASR is loaded, if not reload with ASR
        status = model_manager.get_status()
        if not status.get("asr_loaded"):
            model_manager.load_model("voice_clone", with_asr=True)

        # Access the private ASR model directly (since there's no public getter)
        # Note: In a stricter design, we'd add get_asr_model() to ModelManager
        asr_pipeline = model_manager._asr_model

        if asr_pipeline is None:
            raise RuntimeError("ASR model not loaded.")

        result = asr_pipeline(audio_path, return_timestamps=True)
        return result["text"].strip()

    except Exception as e:
        import traceback

        error_msg = f"Transcription error: {type(e).__name__}: {e}"
        print(error_msg)
        print(traceback.format_exc())
        full_error = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()[:500]}"
        raise gr.Error(full_error)


def clone_and_generate(
    ref_audio: str,
    ref_text: str,
    text: str,
) -> Tuple[int, np.ndarray]:
    """Clone voice and generate speech.

    Returns:
        Tuple of (sample_rate, audio_array) for Gradio Audio component.
    """
    if not ref_audio:
        raise gr.Error("Please select reference audio.")
    if not ref_text:
        raise gr.Error("Reference text is required.")
    if not text:
        raise gr.Error("Please enter text to generate.")

    try:
        # Ensure model is loaded (no ASR needed for generation)
        if not model_manager.is_loaded("voice_clone"):
            model_manager.load_model("voice_clone")

        model = model_manager.get_model()

        # Create prompt
        prompt = model.create_voice_clone_prompt(
            ref_audio=ref_audio,
            ref_text=ref_text,
        )

        # Cache the prompt for persistence
        voice_cache.save_voice(prompt)

        # Generate
        wavs, sr = model.generate_voice_clone(
            text=text,
            voice_clone_prompt=prompt,
            language=None,  # Auto-detect
        )

        # Gradio Audio expects (sample_rate, audio_data)
        audio_data = wavs[0]
        if not isinstance(audio_data, np.ndarray):
            audio_data = np.array(audio_data)

        return (sr, audio_data)

    except Exception as e:
        raise gr.Error(f"Cloning failed: {str(e)}")


def load_model_on_select():
    """Load the voice clone model when tab is selected."""
    try:
        # Pre-load with ASR since user will likely need it
        model_manager.load_model("voice_clone", with_asr=True)
    except Exception as e:
        print(f"Error loading model: {e}")


def create_voice_clone_tab() -> gr.Tab:
    """Create the Voice Clone tab."""
    with gr.Tab("Voice Clone") as tab:
        gr.Markdown("### Voice Cloning")
        gr.Markdown(
            "Clone a voice from a short audio sample. "
            "Requires transcription of the reference audio."
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("#### 1. Reference Audio")

                # File selector
                file_dropdown = gr.Dropdown(
                    label="Select Audio File",
                    choices=get_voice_files(),
                    interactive=True,
                    info="Select a voice file or upload a new one below",
                )
                refresh_btn = gr.Button("🔄 Refresh File List", size="sm")

                # Upload section
                with gr.Accordion("📤 Upload New Voice", open=False):
                    upload_file = gr.File(
                        label="Upload Audio File",
                        file_types=[".wav", ".mp3", ".flac", ".opus"],
                        type="filepath",
                    )
                    upload_status = gr.Textbox(
                        label="Status",
                        interactive=False,
                        placeholder="Upload a file to see status...",
                    )

                audio_player = gr.Audio(
                    label="Preview Reference",
                    type="filepath",
                    interactive=False,
                )

                transcribe_btn = gr.Button("Transcribe Audio")

                ref_text_input = gr.TextArea(
                    label="Reference Text",
                    placeholder="Transcription will appear here...",
                    lines=3,
                    info="Verify and correct the transcription if needed.",
                )

            with gr.Column(scale=1):
                gr.Markdown("#### 2. Generation")
                text_input = gr.TextArea(
                    label="Text to Speak",
                    placeholder="Enter text to generate with cloned voice...",
                    lines=4,
                )
                generate_btn = gr.Button("Clone & Generate", variant="primary")

                audio_output = gr.Audio(
                    label="Generated Audio",
                    type="numpy",
                    interactive=False,
                )

        # Event handlers
        def update_files():
            return gr.Dropdown(choices=get_voice_files())

        refresh_btn.click(fn=update_files, outputs=[file_dropdown])

        # Upload handler
        upload_file.change(
            fn=upload_voice_file,
            inputs=[upload_file],
            outputs=[file_dropdown, upload_status],
        )

        file_dropdown.change(
            fn=lambda x: x, inputs=[file_dropdown], outputs=[audio_player]
        )

        transcribe_btn.click(
            fn=transcribe_audio,
            inputs=[file_dropdown],
            outputs=[ref_text_input],
        )

        generate_btn.click(
            fn=clone_and_generate,
            inputs=[file_dropdown, ref_text_input, text_input],
            outputs=[audio_output],
        )

        # Load model when tab is selected
        tab.select(fn=load_model_on_select, outputs=None)

    return tab
