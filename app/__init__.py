"""App package initialization.

This module makes the ``app`` directory a proper Python package and
re-exports lightweight configuration helpers for convenience.

Keep the top-level import surface minimal to avoid importing heavy
dependencies at package import time.

Example:
    from app import Settings
    settings = Settings()

"""

# Standard library imports
from importlib import metadata
from typing import Any

# Local imports (keep lightweight to avoid side-effects)
from .config import Settings  # re-export Settings for convenience


try:
    __version__ = metadata.version("qwen3-tts")  # type: ignore[name-defined]
except Exception:
    __version__ = "0.0.0"


__all__ = ["Settings", "__version__"]
