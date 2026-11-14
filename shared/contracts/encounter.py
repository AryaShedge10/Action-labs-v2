"""
Shared Encounter Contract.
Source of truth contract between Clinical NLP, Dashboard, Database, and Mock EHR.
Guarantees nullable patient demographic fields and immutable audit tracking.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from shared.contracts.transcript import TranscriptPayload
from shared.contracts.clinical_analysis import (
    Claim,
    ClinicalNoteStructure,
    ConflictItem,
    GroundingReport,
)


class PatientProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, description="Patient medical record number / identifier")
    name: str = Field(min_length=1, default="Unknown Patient")
    age: Optional[int] = Field(default=None, ge=0, le=130, description="Patient age in years; null if unstated")
    date_of_birth: Optional[str] = None
    sex: str = Field(default="unknown")
    gender: Optional[str] = None
    allergies: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    medical_history: list[str] = Field(default_factory=list)
    family_history: list[str] = Field(default_factory=list)
    known_conditions: list[str] = Field(default_factory=list)

    @field_validator("sex", mode="before")
    @classmethod
    def normalize_sex(cls, value: Any) -> str:
        if not value:
            return "unknown"
        return str(value).strip().lower()


class EncounterContract(BaseModel):
    model_config = ConfigDict(extra="ignore")

    encounter_id: str = Field(min_length=1, description="Canonical consultation identifier")
    encounter_at: datetime = Field(default_factory=datetime.utcnow)
    physician_id: str = Field(default="phys-001")
    physician_name: str = Field(default="Dr. Smith")
    
    patient: PatientProfile
    transcript: TranscriptPayload
    clinical_note: ClinicalNoteStructure
    claims: list[Claim] = Field(default_factory=list)
    conflicts: list[ConflictItem] = Field(default_factory=list)
    grounding: GroundingReport = Field(default_factory=GroundingReport)
    
    ai_status: str = Field(default="draft_ready")
    validation_status: str = Field(default="required")
    workflow_status: str = Field(default="draft")
    reviewed: bool = False
    finalized_at: Optional[datetime] = None
    
    acknowledgements: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

