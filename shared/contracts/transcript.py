"""
Shared Transcript Contract across all services (Transcription 2A, Clinical NLP 2B, Dashboard 2C).
Normalizes start_time/end_time and start/end discrepancies.
"""
from __future__ import annotations

import re
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

CONSULTATION_ID_PATTERN = r"^[A-Za-z0-9_.:\-]{1,128}$"


class TranscriptSegment(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: Optional[str] = None
    speaker: str = Field(description="DOCTOR, PATIENT, physician, patient, nurse, or UNKNOWN")
    start_time: float = Field(default=0.0, ge=0.0, description="Start time in seconds")
    end_time: float = Field(default=0.0, ge=0.0, description="End time in seconds")
    start: float = Field(default=0.0, ge=0.0, description="Dashboard-compatible start time in seconds")
    end: float = Field(default=0.0, ge=0.0, description="Dashboard-compatible end time in seconds")
    text: str = Field(description="Transcribed text utterance")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="ASR confidence score 0..1")
    source_type: str = Field(default="transcript", description="Provenance source type")

    @model_validator(mode="before")
    @classmethod
    def sync_timestamps(cls, data: Any) -> Any:
        if isinstance(data, dict):
            st = data.get("start_time")
            s = data.get("start")
            if s is None and st is not None:
                data["start"] = float(st)
            elif st is None and s is not None:
                data["start_time"] = float(s)

            et = data.get("end_time")
            e = data.get("end")
            if e is None and et is not None:
                data["end"] = float(et)
            elif et is None and e is not None:
                data["end_time"] = float(e)

            # Generate segment ID if missing
            if not data.get("id"):
                idx = data.get("index", 0)
                spk = data.get("speaker", "seg")
                actual_start = data.get("start", 0) or 0
                data["id"] = f"{spk}_{idx}_{int(float(actual_start)*1000)}"

        return data

    @model_validator(mode="after")
    def validate_times(self) -> "TranscriptSegment":
        if self.end_time < self.start_time:
            raise ValueError(f"end_time ({self.end_time}) cannot be before start_time ({self.start_time})")
        # Ensure start/end mirror start_time/end_time
        if self.start != self.start_time:
            self.start = self.start_time
        if self.end != self.end_time:
            self.end = self.end_time
        return self


class TranscriptPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    consultation_id: str = Field(pattern=CONSULTATION_ID_PATTERN)
    language: str = Field(default="en-US")
    segments: list[TranscriptSegment] = Field(min_length=1)
    created_at: Optional[str] = None
    model: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_team_a_dict(self) -> dict[str, Any]:
        """Convert to Team A / Team B transcript format."""
        return {
            "consultation_id": self.consultation_id,
            "language": self.language,
            "segments": [
                {
                    "speaker": s.speaker,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "text": s.text,
                    "confidence": s.confidence,
                }
                for s in self.segments
            ],
            "metadata": self.metadata,
        }

    def to_dashboard_dict(self) -> dict[str, Any]:
        """Convert to Team C / Dashboard transcript format."""
        return {
            "segments": [
                {
                    "id": s.id,
                    "speaker": s.speaker.lower(),
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                    "confidence": s.confidence,
                    "source_type": s.source_type,
                }
                for s in self.segments
            ]
        }

