"""
Shared Clinical Analysis Contract.
Standardizes clinical entities, SOAP claims, prescriptions, conflicts, grounding, and provenance.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from shared.contracts.transcript import TranscriptSegment


class ConflictSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class ClinicalEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    name: str
    category: str = Field(description="symptom, medication, allergy, condition, vital, etc.")
    status: str = Field(default="active", description="active, negated, historical, suspected, resolved")
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    segment_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class SoapStatement(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    text: str
    citations: list[str] = Field(default_factory=list)
    origin: str = Field(default="ai", description="ai or physician")
    deleted: bool = False
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ClinicalNoteStructure(BaseModel):
    model_config = ConfigDict(extra="ignore")

    subjective: list[SoapStatement] = Field(default_factory=list)
    objective: list[SoapStatement] = Field(default_factory=list)
    assessment: list[SoapStatement] = Field(default_factory=list)
    plan: list[SoapStatement] = Field(default_factory=list)


class Claim(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    text: str
    section: str = Field(description="subjective, objective, assessment, or plan")
    citations: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    origin: str = Field(default="ai")
    deleted: bool = False


class PrescriptionDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    medication: str
    dosage: str
    route: Optional[str] = "oral"
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None
    status: str = Field(default="draft", description="draft, approved, rejected")
    warnings: list[str] = Field(default_factory=list)


class ConflictItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    severity: ConflictSeverity = ConflictSeverity.MEDIUM
    category: str = Field(description="allergy, medication, demographic, contradiction, grounding")
    title: str
    message: str
    claim_id: Optional[str] = None
    resolved: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class GroundingReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    grounding_score: float = Field(default=1.0, ge=0.0, le=1.0)
    citation_coverage: float = Field(default=1.0, ge=0.0, le=1.0)
    total_claims: int = 0
    supported_claims: int = 0
    unsupported_claims: int = 0
    contradictory_claims: int = 0
    uncertain_claims: int = 0
    disclaimer: str = "AI-generated clinical draft. Physician must verify all statements."


class ClinicalAnalysisContract(BaseModel):
    model_config = ConfigDict(extra="ignore")

    consultation_id: str
    pipeline_version: str = "2.0.0"
    schema_version: str = "1.0.0"
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    
    transcript: list[TranscriptSegment] = Field(default_factory=list)
    entities: list[ClinicalEntity] = Field(default_factory=list)
    clinical_note: ClinicalNoteStructure = Field(default_factory=ClinicalNoteStructure)
    claims: list[Claim] = Field(default_factory=list)
    prescriptions: list[PrescriptionDraft] = Field(default_factory=list)
    conflicts: list[ConflictItem] = Field(default_factory=list)
    grounding: GroundingReport = Field(default_factory=GroundingReport)
    
    metadata: dict[str, Any] = Field(default_factory=dict)

