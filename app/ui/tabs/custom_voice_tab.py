"""Custom Voice tab for Qwen3-TTS Gradio UI.

Allows generation of speech using 9 premium preset speakers with style control.
"""

import gradio as gr
import soundfile as sf
import numpy as np
from typing import Tuple, Optional, List

from app.core.model_manager import model_manager


# Supported speakers
SPEAKERS = [
    "Vivian",
    "Ryan",
    "Serena",
    "Aiden",
    "Chloe",
    "Eric",
    "Luna",
    "Owen",
    "Zoe",
]

# Supported languages
LANGUAGES = [
    "Auto",
    "English",
    "Chinese",
    "French",
    "Japanese",
    "Korean",
    "German",
    "Russian",
    "Portuguese",
    "Spanish",
    "Italian",
]


def generate_audio(
    text: str,
    speaker: str,
    language: str,
    instruction: str,
) -> Tuple[int, np.ndarray]:
    """Generate audio using the Custom Voice model.

    Returns:
        Tuple of (sample_rate, audio_array) for Gradio Audio component.
    """
    if not text:
        raise gr.Error("Please enter text to generate.")

    try:
        # Ensure correct model is loaded
        if not model_manager.is_loaded("custom_voice"):
            gr.Info("Loading Custom Voice model...")
            model_manager.load_model("custom_voice")

        model = model_manager.get_model()

        # Handle "Auto" language
        lang = None if language == "Auto" else language

        # Generate
        wavs, sr = model.generate_custom_voice(
            text=text,
            speaker=speaker,
            instruct=instruction if instruction else None,
            language=lang,
        )

        # Gradio Audio expects (sample_rate, audio_data) for numpy type
        # wavs[0] is the audio array, sr is sample rate
        audio_data = wavs[0]
        if not isinstance(audio_data, np.ndarray):
            audio_data = np.array(audio_data)

        return (sr, audio_data)

    except Exception as e:
        import traceback

        error_msg = f"Error in generate_audio: {type(e).__name__}: {e}"
        print(error_msg)
        print(traceback.format_exc())
        # Afficher l'erreur complète à l'utilisateur pour debug
        full_error = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()[:500]}"
        raise gr.Error(full_error)


def load_model_on_select():
    """Load the custom voice model when tab is selected."""
    try:
        if not model_manager.is_loaded("custom_voice"):
            gr.Info("Loading Custom Voice model...", duration=2)
            model_manager.load_model("custom_voice")
            return "Model loaded successfully."
        return "Model already loaded."
    except Exception as e:
        return f"Error loading model: {e}"


def create_custom_voice_tab() -> gr.Tab:
    """Create the Custom Voice tab."""
    with gr.Tab("Custom Voice") as tab:
        gr.Markdown("### Custom Voice Generation")
        gr.Markdown(
            "Generate high-quality speech using premium preset speakers. "
            "Supports 10 languages with auto-detection."
        )

        # Status indicator
        status_text = gr.Markdown(value="", visible=False)

        with gr.Row():
            with gr.Column():
                text_input = gr.TextArea(
                    label="Text to Speak",
                    placeholder="Enter text here...",
                    lines=4,
                )

                with gr.Row():
                    speaker_dropdown = gr.Dropdown(
                        choices=SPEAKERS,
                        value="Vivian",
                        label="Speaker",
                        info="Select a preset voice profile.",
                    )
                    language_dropdown = gr.Dropdown(
                        choices=LANGUAGES,
                        value="Auto",
                        label="Language",
                        info="Target language (or Auto).",
                    )

                instruction_input = gr.Textbox(
                    label="Style Instruction (Optional)",
                    placeholder="E.g., 'Speak in a happy tone'",
                    info="Describe the desired emotion or speaking style.",
                )
                generate_btn = gr.Button("Generate", variant="primary")

            with gr.Column():
                audio_output = gr.Audio(
                    label="Generated Audio",
                    type="numpy",
                    interactive=False,
                    autoplay=False,
                )

        # Event handlers
        generate_btn.click(
            fn=generate_audio,
            inputs=[text_input, speaker_dropdown, language_dropdown, instruction_input],
            outputs=[audio_output],
        )

        # Load model when tab is selected and show status
        tab.select(fn=load_model_on_select, inputs=None, outputs=None).then(
            fn=lambda: gr.Markdown(visible=False),  # Hide status after loading
            inputs=None,
            outputs=[status_text],
        )

    return tab
