"""Voice Design tab for Qwen3-TTS Gradio UI.

Allows generation of speech by describing the desired voice.
"""

import gradio as gr
import numpy as np
from typing import Tuple, Optional

from app.core.model_manager import model_manager
from app.ui.components.model_status_bar import create_model_status_bar


def generate_audio(
    text: str,
    description: str,
    language: str,
) -> Tuple[int, np.ndarray]:
    """Generate audio using the Voice Design model.

    Returns:
        Tuple of (sample_rate, audio_array) for Gradio Audio component.
    """
    if not text:
        raise gr.Error("Please enter text to generate.")
    if not description:
        raise gr.Error("Please provide a voice description.")

    try:
        # Ensure correct model is loaded
        if not model_manager.is_loaded("voice_design"):
            model_manager.load_model("voice_design")

        model = model_manager.get_model()

        # Handle 'Auto' language selection
        lang_arg = None if language == "Auto" else language

        # Generate
        wavs, sr = model.generate_voice_design(
            text=text,
            instruct=description,
            language=lang_arg,
        )

        # Gradio Audio expects (sample_rate, audio_data)
        audio_data = wavs[0]
        if not isinstance(audio_data, np.ndarray):
            audio_data = np.array(audio_data)

        return (sr, audio_data)

    except Exception as e:
        import traceback

        print(f"Error in generate_audio: {e}")
        print(traceback.format_exc())
        raise gr.Error(f"Generation failed: {str(e)}")


def load_model_on_select():
    """Load the voice design model when tab is selected."""
    try:
        model_manager.load_model("voice_design")
    except Exception as e:
        print(f"Error loading model: {e}")


def create_voice_design_tab() -> gr.Tab:
    """Create the Voice Design tab."""
    with gr.Tab("Voice Design") as tab:
        # Status bar to show model loading state
        create_model_status_bar()

        gr.Markdown("### Voice Design")
        gr.Markdown(
            "Create a new voice by describing it in natural language. "
            "Describe gender, age, tone, emotion, and speaking style."
        )

        with gr.Row():
            with gr.Column():
                text_input = gr.TextArea(
                    label="Text to Speak",
                    placeholder="Enter text here...",
                    lines=4,
                )

                language_input = gr.Dropdown(
                    choices=[
                        "Auto",
                        "Chinese",
                        "English",
                        "Japanese",
                        "Korean",
                        "German",
                        "French",
                        "Russian",
                        "Portuguese",
                        "Spanish",
                        "Italian",
                    ],
                    value="Auto",
                    label="Language",
                    info="Select target language or use Auto for detection.",
                )

                description_input = gr.TextArea(
                    label="Voice Description",
                    placeholder=(
                        "E.g., 'A young female voice, energetic and happy, "
                        "high pitch, speaking quickly.'"
                    ),
                    lines=3,
                    info="Describe the voice characteristics in detail.",
                )
                generate_btn = gr.Button("Generate", variant="primary")

            with gr.Column():
                audio_output = gr.Audio(
                    label="Generated Audio",
                    type="numpy",
                    interactive=False,
                )

        # Event handlers
        generate_btn.click(
            fn=generate_audio,
            inputs=[text_input, description_input, language_input],
            outputs=[audio_output],
        )

        # Load model when tab is selected
        tab.select(fn=load_model_on_select, outputs=None)

    return tab
