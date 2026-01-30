"""Model manager for Qwen3-TTS.

This module provides a singleton thread-safe model manager that ensures
only one TTS model is loaded in memory at a time.
"""

import gc
import threading
from typing import Optional, Literal, Dict, Any

# Guarded imports for optional dependencies
try:
    import torch
except ImportError:
    torch = None  # type: ignore

try:
    from qwen_tts import Qwen3TTSModel
except ImportError:
    Qwen3TTSModel = None  # type: ignore

from app.config import Settings

settings = Settings()


class ModelManager:
    """Singleton thread-safe manager for Qwen3-TTS models.

    Ensures only one TTS model is loaded in GPU memory at a time.
    Supports loading ASR (Whisper) only with voice_clone model.

    Example:
        manager = ModelManager()
        model = manager.load_model("voice_clone", with_asr=True)
        # Use model...
        manager.switch_to("custom_voice")  # Unloads previous, loads new
    """

    _instance: Optional["ModelManager"] = None
    _lock = threading.Lock()

    MODEL_PATHS: Dict[str, str] = {
        "custom_voice": "modele_tts/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        "voice_design": "modele_tts/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        "voice_clone": "modele_tts/Qwen3-TTS-12Hz-1.7B-Base",
    }

    ASR_MODEL_NAME = "openai/whisper-large-v3"

    def __new__(cls) -> "ModelManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._tts_model: Optional[Any] = None
        self._tts_type: Optional[str] = None
        self._asr_model: Optional[Any] = None

        self._device = settings.DEVICE
        self._dtype = self._get_dtype()

    def _get_dtype(self):
        """Get torch dtype from settings."""
        if torch is None:
            return None
        dtype_map = {
            "bfloat16": torch.bfloat16,
            "float16": torch.float16,
            "float32": torch.float32,
        }
        return dtype_map.get(settings.DTYPE, torch.bfloat16)

    def load_model(
        self,
        model_type: Literal["custom_voice", "voice_design", "voice_clone"],
        with_asr: bool = False,
    ) -> Any:
        """Load a TTS model, unloading any existing model first.

        Args:
            model_type: Type of model to load.
            with_asr: If True, also load ASR (only for voice_clone).

        Returns:
            The loaded Qwen3TTSModel instance.

        Raises:
            ValueError: If model_type is invalid or ASR requested with
                non-voice_clone model.
            RuntimeError: If model loading fails.
        """
        if with_asr and model_type != "voice_clone":
            raise ValueError("ASR only available with voice_clone model")

        # Return cached if same model
        if self._tts_type == model_type:
            if with_asr and self._asr_model is None:
                self._load_asr()
            return self._tts_model

        # Unload existing
        self.unload_all()

        # Load new model
        model_path = self.MODEL_PATHS.get(model_type)
        if not model_path:
            raise ValueError(f"Unknown model type: {model_type}")

        print(f"Loading {model_type} from {model_path}...")

        try:
            if Qwen3TTSModel is None:
                raise RuntimeError("qwen_tts not installed")

            self._tts_model = Qwen3TTSModel.from_pretrained(
                model_path,
                device_map=self._device,
                dtype=self._dtype,
                attn_implementation=settings.ATTENTION_IMPLEMENTATION,
                local_files_only=True,
            )
            self._tts_type = model_type

            if torch and torch.cuda.is_available():
                vram = torch.cuda.memory_allocated() / 1024**3
                print(f"  Loaded. VRAM: {vram:.2f} GB")

        except Exception as e:
            self._tts_model = None
            self._tts_type = None
            raise RuntimeError(f"Failed to load {model_type}: {e}")

        if with_asr:
            self._load_asr()

        return self._tts_model

    def _load_asr(self):
        """Load ASR model (Whisper)."""
        if self._asr_model is not None:
            return

        print(f"Loading ASR model ({self.ASR_MODEL_NAME})...")

        try:
            from transformers import pipeline

            self._asr_model = pipeline(
                "automatic-speech-recognition",
                model=self.ASR_MODEL_NAME,
                device=self._device,
                torch_dtype=self._dtype,
            )

            if torch and torch.cuda.is_available():
                vram = torch.cuda.memory_allocated() / 1024**3
                print(f"  ASR loaded. Total VRAM: {vram:.2f} GB")

        except Exception as e:
            raise RuntimeError(f"Failed to load ASR: {e}")

    def unload_all(self):
        """Unload all models and free GPU memory."""
        if self._tts_model is not None:
            print(f"Unloading {self._tts_type}...")
            self._tts_model = None
            self._tts_type = None

        if self._asr_model is not None:
            print("Unloading ASR...")
            self._asr_model = None

        # Clear GPU memory
        gc.collect()
        if torch and torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            vram = torch.cuda.memory_allocated() / 1024**3
            print(f"  VRAM freed. Remaining: {vram:.2f} GB")

    def switch_to(self, model_type: str) -> Any:
        """Switch to a different model (alias for load_model)."""
        return self.load_model(model_type, with_asr=False)

    def get_model(self) -> Any:
        """Get currently loaded TTS model."""
        if self._tts_model is None:
            raise RuntimeError("No model loaded")
        return self._tts_model

    def get_status(self) -> Dict[str, Any]:
        """Get current status including GPU memory."""
        status = {
            "current_model": self._tts_type,
            "asr_loaded": self._asr_model is not None,
            "device": self._device,
        }

        if torch and torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            status.update(
                {
                    "gpu_name": props.name,
                    "gpu_memory_total_gb": props.total_memory / 1024**3,
                    "gpu_memory_allocated_gb": (
                        torch.cuda.memory_allocated() / 1024**3
                    ),
                }
            )

        return status

    def is_loaded(self, model_type: str) -> bool:
        """Check if specific model type is loaded."""
        return self._tts_type == model_type


# Global instance
model_manager = ModelManager()
