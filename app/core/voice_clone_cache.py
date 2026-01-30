"""Voice clone cache for persistent voice storage.

This module provides a singleton cache that stores exactly one cloned voice
persistently on disk using pickle. The cached voice survives server restarts.
"""

import pickle
from pathlib import Path
from typing import Optional, Any

from app.config import Settings

settings = Settings()


class VoiceCloneCache:
    """Singleton cache for one cloned voice.

    Stores a VoiceClonePromptItem persistently on disk so it survives
    server restarts. Only one voice is stored at a time - new clones
    overwrite the previous one.

    Example:
        cache = VoiceCloneCache()
        cache.save_voice(prompt_item)  # Saves to disk
        # Later...
        prompt = cache.get_voice()  # Loads from disk
    """

    _instance: Optional["VoiceCloneCache"] = None

    def __new__(cls) -> "VoiceCloneCache":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.cache_file = Path(settings.CACHE_DIR) / "last_voice_clone.pkl"
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._current_prompt: Optional[Any] = None

        # Load existing voice on startup
        self._load_from_disk()

    def _load_from_disk(self):
        """Load voice from disk if exists."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "rb") as f:
                    self._current_prompt = pickle.load(f)
                print(f"Loaded cached voice from {self.cache_file}")
            except Exception as e:
                print(f"Could not load cached voice: {e}")
                self._current_prompt = None

    def save_voice(self, prompt_item: Any):
        """Save a voice clone prompt to disk.

        Args:
            prompt_item: VoiceClonePromptItem to save.
        """
        self._current_prompt = prompt_item

        try:
            with open(self.cache_file, "wb") as f:
                pickle.dump(prompt_item, f)
            print(f"Voice saved to {self.cache_file}")
        except Exception as e:
            print(f"Failed to save voice: {e}")
            raise

    def get_voice(self) -> Any:
        """Get the cached voice.

        Returns:
            The cached VoiceClonePromptItem.

        Raises:
            RuntimeError: If no voice is cached.
        """
        if self._current_prompt is None:
            raise RuntimeError(
                "No cloned voice available. "
                "Please clone a voice via the Gradio interface first."
            )
        return self._current_prompt

    def has_voice(self) -> bool:
        """Check if a voice is cached."""
        return self._current_prompt is not None

    def clear(self):
        """Clear the cached voice."""
        self._current_prompt = None
        if self.cache_file.exists():
            self.cache_file.unlink()
        print("Voice cache cleared")


# Global instance
voice_cache = VoiceCloneCache()
