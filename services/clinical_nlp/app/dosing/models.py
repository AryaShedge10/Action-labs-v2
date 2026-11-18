"""Public data models of the dose-suggestion feature.

The disclaimer is part of every DoseSuggestion: this is a suggestion for a clinician, never an order.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

DISCLAIMER = ("Decision support prototype, not for clinical use. This is a suggestion for the doctor to consider, "
              "not an order; values come from a guideline extract that has not been clinically reviewed.")


class PatientContext(BaseModel):
    """Patient facts the dose rules need. `None` always means 'unknown' (never a default) and triggers NEEDS_INFO
    when a rule depends on it. Empty lists mean 'documented as none'."""

    age_years: float | None = Field(default=None, ge=0, le=130)
    sex: str | None = None                          # "male" | "female"
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    pregnant: bool | None = None
    creatinine_clearance_ml_min: float | None = Field(default=None, ge=0)
    hepatic_impairment: bool | None = None
    conditions: list[str] | None = None
    current_medications: list[str] | None = None
    allergies: list[str] | None = None


class DoseStatus(str, Enum):
    SUGGESTED = "SUGGESTED"
    NEEDS_INFO = "NEEDS_INFO"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"
    NOT_SUPPORTED = "NOT_SUPPORTED"


class DoseCitation(BaseModel):
    page: int
    table_or_section: str
    quote: str | None = None
    supports: str                                   # what this citation backs, e.g. "start dose"


class DoseSuggestion(BaseModel):
    status: DoseStatus
    drug: str                                       # as requested
    resolved_drug: str | None = None                # canonical generic used for the rules
    start_dose: float | None = None
    unit: str | None = None
    frequency: str | None = None
    max_daily_dose: float | None = None
    titration_interval: str | None = None
    adjustments_applied: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)      # why NOT_RECOMMENDED / NOT_SUPPORTED
    needs_info: list[str] = Field(default_factory=list)
    citations: list[DoseCitation] = Field(default_factory=list)
    knowledge_source: str = ""
    reviewed_by_clinician: bool = False
    patient_context: PatientContext | None = None   # facts the suggestion was computed from (for the audit trail)
    disclaimer: str = DISCLAIMER
