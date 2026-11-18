"""
Data Models for NVIDIA NeMo Realtime STT Test Environment
tests/realtime_nvidia/backend/app/models.py

Preserved from AssemblyAI POC — provider-agnostic.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class WordItem(BaseModel):
    text: str
    start: float = 0.0      # seconds
    end: float = 0.0        # seconds
    speaker: str = "UNKNOWN"
    word_is_final: bool = False


class TranscriptSegment(BaseModel):
    segment_id: str
    turn_id: int = 0
    start_time: float = 0.0   # seconds
    end_time: float = 0.0     # seconds
    speaker_id: str = "UNKNOWN"
    role: str = "Unassigned"  # Doctor / Patient
    text: str = ""
    status: Literal["LIVE", "STABLE", "FINAL"] = "LIVE"
    is_final: bool = False
    confidence: Optional[float] = None
    words: List[WordItem] = Field(default_factory=list)
    version: int = 1


class RealtimeEvent(BaseModel):
    type: Literal[
        "segment_update",
        "speaker_revision",
        "session_status",
        "error",
        "final_summary"
    ]
    session_id: str
    segment: Optional[TranscriptSegment] = None
    all_segments: Optional[List[TranscriptSegment]] = None
    status: Optional[str] = None
    message: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    timestamp: float = Field(default_factory=lambda: 0.0)


class SessionMetrics(BaseModel):
    session_id: str
    audio_duration_seconds: float = 0.0
    wall_clock_processing_seconds: float = 0.0
    time_to_first_audio_frame_ms: Optional[float] = None
    time_to_first_partial_ms: Optional[float] = None
    time_to_first_visible_text_ms: Optional[float] = None
    time_to_stable_text_ms: Optional[float] = None
    time_to_final_turn_ms: Optional[float] = None
    time_to_speaker_revision_ms: Optional[float] = None
    stop_to_final_ms: Optional[float] = None
    session_total_latency_ms: Optional[float] = None
    rtf: Optional[float] = None
    total_audio_frames_sent: int = 0
    total_bytes_sent: int = 0
    partial_count: int = 0
    final_count: int = 0
    speaker_revisions_count: int = 0
    duplicate_count: int = 0
    dropped_frames_count: int = 0
    backlog_ms: float = 0.0
    gpu_utilization_pct: Optional[float] = None
    vram_used_mib: Optional[float] = None
