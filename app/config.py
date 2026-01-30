"""Application configuration using pydantic-settings.

This module defines the Settings data class which centralizes all
configuration for the application. Values are loaded from environment
variables and a local .env file by default. Use the Settings class to
access typed configuration values across the codebase.

Example:
    from app.config import Settings
    settings = Settings()
    print(settings.api_port)

"""

from typing import Literal, Optional, Any, TYPE_CHECKING
import importlib

# Silence pyright missing import errors for optional runtime deps
# when they are not installed in the current environment.
# pyright: reportMissingImports=false

# Try to import real pydantic / pydantic_settings at runtime. If the
# packages are not available, provide minimal stubs so the module can
# still be imported and LSP remains clean.
try:
    _pydantic = importlib.import_module("pydantic")
    _pyd_settings = importlib.import_module("pydantic_settings")
except Exception:
    _pydantic = None  # type: ignore[assignment]
    _pyd_settings = None  # type: ignore[assignment]

if _pydantic is not None:
    Field = getattr(_pydantic, "Field")
    validator = getattr(_pydantic, "validator")
    BaseSettings = getattr(_pydantic, "BaseModel")
else:
    # Minimal stubs for environments without pydantic installed.
    def Field(default: Any = None, **_: Any) -> Any:  # type: ignore[override]
        return default

    def validator(*_args: Any, **_kw: Any) -> Any:  # type: ignore[override]
        def _dec(func: Any) -> Any:
            return func

        return _dec

    class BaseSettings:  # type: ignore[misc]
        pass


if _pyd_settings is not None:
    try:
        BaseSettings = getattr(_pyd_settings, "BaseSettings")
    except Exception:
        # keep previous BaseSettings
        pass


class Settings(BaseSettings):
    """Application settings loaded from environment and .env file.

    Attributes:
        qwen3_tts_api_key: API key for external Qwen3 TTS service.
        api_host: Host address for the API server.
        api_port: Port for the API server.

        ui_port: Port for the UI server (gradio/streamlit/etc.).
        ui_share: Whether to enable UI public sharing.

        device: Compute device to use for ML workloads.
        dtype: Floating-point data type for model weights/compute.
        attention_implementation: Attention implementation backend.

        models_dir: Directory where models are stored.
        voices_dir: Directory where voice assets are stored.
        cache_dir: Directory used for caching downloads and artifacts.

        asr_model: Automatic speech recognition model id.
        asr_device: Device for running ASR.

        output_format: Audio output file format.
        output_sample_rate: Output sample rate in Hz.
    """

    # API Configuration
    QWEN3_TTS_API_KEY: str = Field(
        "dummy-key",
        description="API key for QWEN3 TTS service",
    )
    API_HOST: str = Field("0.0.0.0", description="API host address")
    API_PORT: int = Field(8000, description="API port number")

    # UI Configuration
    UI_PORT: int = Field(7860, description="UI port number")
    UI_SHARE: bool = Field(False, description="Enable UI sharing")

    # GPU / compute configuration
    DEVICE: str = Field("cuda", description="Compute device")
    DTYPE: Literal["bfloat16", "float16", "float32"] = Field(
        "bfloat16",
        description=(
            "Floating point precision for models. One of: bfloat16, float16, float32"
        ),
    )
    ATTENTION_IMPLEMENTATION: str = Field(
        "flash_attention_2", description="Attention implementation to use"
    )

    # Paths
    MODELS_DIR: str = Field("modele_tts", description="Models directory")
    VOICES_DIR: str = Field("voices", description="Voices directory")
    CACHE_DIR: str = Field("cache", description="Cache directory")

    # ASR
    ASR_MODEL: str = Field(
        "openai/whisper-large-v3", description="ASR model identifier"
    )
    ASR_DEVICE: str = Field("cuda", description="Device for ASR")

    # Audio output
    OUTPUT_FORMAT: str = Field("mp3", description="Audio output format")
    OUTPUT_SAMPLE_RATE: int = Field(24000, description="Output sample rate in Hz")

    class Config:
        """Pydantic settings configuration.

        env_file tells pydantic to read a .env file located at the
        project root.  Environment variable names are expected to be
        UPPER_SNAKE_CASE matching attribute names.
        """

        env_file = ".env"
        env_prefix = ""
        case_sensitive = False

    @validator("API_PORT", "UI_PORT", "OUTPUT_SAMPLE_RATE")
    def _validate_positive(cls, v: int) -> int:  # type: ignore[override]
        """Validate that numeric ports and sample rate are positive.

        Args:
            v: Value to validate.

        Returns:
            The same value if valid.

        Raises:
            ValueError: If value is not a positive integer.
        """

        if not isinstance(v, int) or v <= 0:
            raise ValueError("must be a positive integer")
        return v

    @validator("DEVICE")
    def _validate_device(cls, v: str) -> str:
        """Ensure device is a non-empty string and normalized.

        Accepts values such as 'cuda', 'cpu', or 'mps'.
        """

        v = v.strip().lower()
        if v == "":
            raise ValueError("device must be a non-empty string")
        return v

    @validator("DTYPE")
    def _validate_dtype(cls, v: str) -> str:
        """Ensure dtype is one of the allowed literals."""

        allowed = {"bfloat16", "float16", "float32"}
        if v not in allowed:
            raise ValueError(f"DTYPE must be one of {sorted(allowed)}, got {v}")
        return v


__all__ = ["Settings"]
