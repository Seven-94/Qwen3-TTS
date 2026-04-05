"""Model status bar component for Gradio UI.

This component displays the currently loaded model and VRAM usage.
"""

import gradio as gr
from app.core.model_manager import model_manager


def get_status_markdown() -> str:
    """Get status markdown string."""
    status = model_manager.get_status()
    model = status.get("current_model") or "None"
    vram_alloc = status.get("gpu_memory_allocated_gb", 0.0)
    vram_total = status.get("gpu_memory_total_gb", 0.0)
    device = status.get("device", "cpu")
    asr = "Loaded" if status.get("asr_loaded") else "Not Loaded"

    return (
        f"### System Status\n"
        f"- **Model:** `{model}`\n"
        f"- **ASR:** `{asr}`\n"
        f"- **Device:** `{device}`\n"
        f"- **VRAM:** `{vram_alloc:.2f} / {vram_total:.2f} GB`"
    )


def create_model_status_bar() -> gr.Markdown:
    """Create the status bar component."""
    return gr.Markdown(value=get_status_markdown, every=2.0)
