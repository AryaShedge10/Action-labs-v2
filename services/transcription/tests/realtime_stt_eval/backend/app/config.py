"""
Configuration Module for AssemblyAI Realtime Test Environment
tests/realtime_stt_eval/backend/app/config.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

TEST_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = TEST_ROOT / ".env"

# Load local test .env only (never touch production .env)
if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=True)

class Settings(BaseModel):
    # AssemblyAI Authentication
    assemblyai_api_key: str = Field(default_factory=lambda: os.getenv("ASSEMBLYAI_API_KEY", ""))
    
    # Realtime WebSocket Endpoint
    assemblyai_ws_url: str = Field(default="wss://streaming.assemblyai.com/v3/ws")
    
    # Model Configuration
    speech_model: str = Field(default_factory=lambda: os.getenv("SPEECH_MODEL", "universal-3-6-pro"))
    domain: str = Field(default_factory=lambda: os.getenv("DOMAIN", "medical-v1"))
    speaker_labels: bool = Field(default_factory=lambda: os.getenv("SPEAKER_LABELS", "true").lower() == "true")
    sample_rate: int = Field(default_factory=lambda: int(os.getenv("SAMPLE_RATE", "16000")))
    max_speakers: int = Field(default=2)
    
    # Audio Frame Settings
    audio_frame_ms: int = Field(default=100)  # 100ms frames = 3200 bytes for 16kHz 16-bit mono
    
    # Role Mapping
    first_speaker_role: str = Field(default="Doctor")
    second_speaker_role: str = Field(default="Patient")
    
    # Server Settings
    host: str = Field(default_factory=lambda: os.getenv("HOST", "127.0.0.1"))
    port: int = Field(default_factory=lambda: int(os.getenv("TEST_PORT", "8003")))
    
    # Directories
    recordings_dir: Path = TEST_ROOT / "recordings"
    logs_dir: Path = TEST_ROOT / "logs"
    reports_dir: Path = TEST_ROOT / "reports"
    frontend_dir: Path = TEST_ROOT / "frontend"

settings = Settings()

# Ensure directories exist
settings.recordings_dir.mkdir(parents=True, exist_ok=True)
settings.logs_dir.mkdir(parents=True, exist_ok=True)
settings.reports_dir.mkdir(parents=True, exist_ok=True)
