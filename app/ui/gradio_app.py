"""Main Gradio Application for Qwen3-TTS.

Combines all tabs and components into a single interface.
"""

import gradio as gr
from app.ui.tabs.custom_voice_tab import create_custom_voice_tab
from app.ui.tabs.voice_design_tab import create_voice_design_tab
from app.ui.tabs.voice_clone_tab import create_voice_clone_tab
from app.ui.components.model_status_bar import create_model_status_bar
from app.config import Settings

settings = Settings()

# Custom CSS for better styling
CSS = """
.container { max-width: 1200px; margin: auto; }
.header { text-align: center; margin-bottom: 20px; }
.header h1 { font-size: 2.5em; color: #333; }
.header p { font-size: 1.2em; color: #666; }
"""


def create_app() -> gr.Blocks:
    """Create the main Gradio Blocks app."""
    with gr.Blocks(title="Qwen3-TTS Unified Interface", css=CSS) as demo:
        # Header
        with gr.Column(elem_classes="container"):
            with gr.Column(elem_classes="header"):
                gr.Markdown(
                    "# 🎙️ Qwen3-TTS Unified Interface\n"
                    "High-fidelity speech generation with voice cloning, "
                    "design, and style control."
                )

            # Model Status Bar
            create_model_status_bar()

            # Main Tabs
            with gr.Tabs():
                create_custom_voice_tab()
                create_voice_design_tab()
                create_voice_clone_tab()

            # Footer
            gr.Markdown(
                "---\n"
                "*Powered by Qwen3-TTS models. "
                "Ensure sufficient VRAM (24GB+ recommended) for full features.*"
            )

    return demo
