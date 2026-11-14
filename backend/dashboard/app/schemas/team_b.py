from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


Speaker = Literal["physician", "patient", "unknown", "nurse", "other"]
SoapSection = Literal["subjective", "objective", "assessment", "plan"]
ClaimOrigin = Literal["ai", "physician"]


class TranscriptSegment(BaseModel):
    id: str = ""
    speaker: str
    start: float = 0
    end: float = 0
    start_time: float | None = None
    end_time: float | None = None
    text: str
    confidence: float = Field(ge=0, le=1, default=0.0)
    source_type: str = "transcript"

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

            if not data.get("id"):
                actual_start = data.get("start", 0) or 0
                data["id"] = f"seg_{int(float(actual_start)*1000)}"
        return data


class Transcript(BaseModel):
    segments: list[TranscriptSegment] = Field(min_length=1)


class Patient(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    age: int | None = Field(default=None, ge=0, le=130)
    date_of_birth: str | None = None
    sex: str
    gender: str | None = None
    allergies: list[str] = []
    medications: list[str] = []
    medical_history: list[str] = []
    family_history: list[str] = []
    known_conditions: list[str] = []

    @field_validator("sex")
    @classmethod
    def normalize_sex(cls, value: str) -> str:
        return value.strip().lower()


class SoapStatement(BaseModel):
    id: str
    text: str
    citations: list[str] = []
    origin: ClaimOrigin = "ai"
    deleted: bool = False


class ClinicalNote(BaseModel):
    subjective: list[SoapStatement] = []
    objective: list[SoapStatement] = []
    assessment: list[SoapStatement] = []
    plan: list[SoapStatement] = []


class Claim(BaseModel):
    id: str
    text: str
    section: SoapSection
    citations: list[str] = []
    confidence: float = Field(ge=0, le=1, default=0.0)
    origin: ClaimOrigin = "ai"
    deleted: bool = False


class TeamBPayload(BaseModel):
    encounter_id: str = Field(min_length=1)
    encounter_at: datetime | None = None
    physician_id: str | None = None
    physician_name: str | None = None
    patient: Patient
    transcript: Transcript
    clinical_note: ClinicalNote
    claims: list[Claim] = Field(min_length=1)


class NotePatch(BaseModel):
    clinical_note: ClinicalNote
    claims: list[Claim]
    patient: Patient | None = None
    edit_reason: str | None = None


class FinalizeRequest(BaseModel):
    reviewed_documentation: bool
    reviewed_conflicts: bool
    verified_medications_allergies: bool
    approve_for_ehr_export: bool


class HandoffRequest(BaseModel):
    encounter_id: str
