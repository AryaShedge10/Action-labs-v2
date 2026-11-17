"""
Configuration for NVIDIA NeMo-Speech.cpp Clinical Scribe (Production)
app/config.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Project root: EDI_Accion_lab/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=True)


class Settings(BaseModel):
    # ------------------------------------------------------------
    # NVIDIA NeMo-Speech.cpp Runtime Connection
    # ------------------------------------------------------------
    # NeMo-Speech.cpp exposes a gRPC server (port 50051 default) or
    # optionally a WebSocket endpoint. The backend bridges browser
    # WebSocket <-> NeMo-Speech.cpp gRPC/WS.
    nemo_speech_host: str = Field(
        default_factory=lambda: os.getenv("NEMO_SPEECH_HOST", "127.0.0.1")
    )
    nemo_speech_grpc_port: int = Field(
        default_factory=lambda: int(os.getenv("NEMO_SPEECH_GRPC_PORT", "50051"))
    )
    nemo_speech_ws_port: int = Field(
        default_factory=lambda: int(os.getenv("NEMO_SPEECH_WS_PORT", "8080"))
    )
    # Protocol preference: "grpc" or "ws"
    nemo_speech_protocol: str = Field(
        default_factory=lambda: os.getenv("NEMO_SPEECH_PROTOCOL", "ws")
    )

    # ------------------------------------------------------------
    # NVIDIA ASR Model
    # ------------------------------------------------------------
    # nvidia/nemotron-3.5-asr-streaming-0.6b
    # Cache-aware FastConformer-RNNT streaming model.
    # Loaded ONCE at NeMo-Speech.cpp server startup.
    nvidia_asr_model: str = Field(
        default_factory=lambda: os.getenv("NVIDIA_ASR_MODEL", "nemotron-3.5")
    )
    # Language: en-US for English clinical speech
    asr_language: str = Field(
        default_factory=lambda: os.getenv("ASR_LANGUAGE", "en-US")
    )
    # Streaming latency mode (NeMo-Speech.cpp option):
    # low_latency (~1.04s buffer), very_low_latency (~0.64s), ultra_low_latency (~0.32s)
    # Note: buffer delay only â€” real latency = buffer + compute + event propagation.
    # Start with low_latency for GTX 1650; benchmark before changing.
    asr_latency_mode: str = Field(
        default_factory=lambda: os.getenv("ASR_LATENCY_MODE", "low_latency")
    )

    # ------------------------------------------------------------
    # NVIDIA Diarization Model
    # ------------------------------------------------------------
    # nvidia/Nemotron-3-Diarization
    # Streaming Sortformer with Arrival-Order Speaker Cache.
    # Maintains speaker identity across the entire session.
    nvidia_diarization_model: str = Field(
        default_factory=lambda: os.getenv(
            "NVIDIA_DIARIZATION_MODEL", "nemotron-3-diarization"
        )
    )
    # Two-speaker clinical consultation. Lower speaker count reduces compute.
    max_speakers: int = Field(
        default_factory=lambda: int(os.getenv("MAX_SPEAKERS", "2"))
    )
    # Enable streaming diarization alongside ASR
    diarization_enabled: bool = Field(
        default_factory=lambda: os.getenv("DIARIZATION_ENABLED", "true").lower() == "true"
    )

    # ------------------------------------------------------------
    # Audio Format (16 kHz PCM16 mono â€” required by Nemotron ASR)
    # ------------------------------------------------------------
    sample_rate: int = Field(
        default_factory=lambda: int(os.getenv("SAMPLE_RATE", "16000"))
    )
    # 100ms audio frames â€” continuous streaming, not batched windows
    audio_frame_ms: int = Field(default=100)

    # ------------------------------------------------------------
    # Role Mapping (deterministic session-level)
    # ------------------------------------------------------------
    first_speaker_role: str = Field(
        default_factory=lambda: os.getenv("FIRST_SPEAKER_ROLE", "Doctor")
    )
    second_speaker_role: str = Field(
        default_factory=lambda: os.getenv("SECOND_SPEAKER_ROLE", "Patient")
    )

    # ------------------------------------------------------------
    # Server â€” runs on port 8000 as production
    # ------------------------------------------------------------
    host: str = Field(
        default_factory=lambda: os.getenv("HOST", "127.0.0.1")
    )
    port: int = Field(
        default_factory=lambda: int(os.getenv("PORT", "8003"))
    )

    # ------------------------------------------------------------
    # Directory Layout â€” project root
    # ------------------------------------------------------------
    models_dir: Path = PROJECT_ROOT / "models"
    model_cache_dir: Path = PROJECT_ROOT / "model_cache"
    recordings_dir: Path = PROJECT_ROOT / "recordings"
    logs_dir: Path = PROJECT_ROOT / "logs"
    reports_dir: Path = PROJECT_ROOT / "reports"
    frontend_dir: Path = PROJECT_ROOT / "static"


settings = Settings()

# Create required directories
for _d in [
    settings.models_dir,
    settings.model_cache_dir,
    settings.recordings_dir,
    settings.logs_dir,
    settings.reports_dir,
]:
    _d.mkdir(parents=True, exist_ok=True)


