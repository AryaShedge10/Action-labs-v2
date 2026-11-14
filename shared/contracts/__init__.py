"""Shared API Contracts for Clinical Scribe Unified Monorepo."""
from shared.contracts.transcript import TranscriptSegment, TranscriptPayload
from shared.contracts.clinical_analysis import (
    ClinicalEntity,
    SoapStatement,
    ClinicalNoteStructure,
    Claim,
    PrescriptionDraft,
    ConflictItem,
    ConflictSeverity,
    GroundingReport,
    ClinicalAnalysisContract,
)
from shared.contracts.encounter import PatientProfile, EncounterContract

__all__ = [
    "TranscriptSegment",
    "TranscriptPayload",
    "ClinicalEntity",
    "SoapStatement",
    "ClinicalNoteStructure",
    "Claim",
    "PrescriptionDraft",
    "ConflictItem",
    "ConflictSeverity",
    "GroundingReport",
    "ClinicalAnalysisContract",
    "PatientProfile",
    "EncounterContract",
]

