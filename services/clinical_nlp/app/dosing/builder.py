"""Build a PatientContext from the pipeline result. Only facts actually extracted are filled; everything else stays
None so the dose engine answers NEEDS_INFO instead of guessing. Pure functions - no LLM, no defaults."""

from __future__ import annotations

from ..models.schemas import AFFIRMED_STATUSES, ConsultationAnalysis, EntityStatus, EntityType
from ..safety.rules import NKDA
from .models import PatientContext

_LB_TO_KG = 0.45359237


def _vital(entities, name):
    found = [e for e in entities if e.type == EntityType.VITAL and e.normalized == name and e.value]
    return max(found, key=lambda e: e.confidence) if found else None


def _number(text: str | None) -> float | None:
    try:
        return float(text) if text is not None else None
    except ValueError:
        return None


def patient_context_from_analysis(analysis: ConsultationAnalysis) -> PatientContext:
    entities = analysis.entities
    demo = analysis.patient_info.demographics

    weight = _vital(entities, "weight")
    weight_kg = None
    if weight is not None and _number(weight.value) is not None:
        kg = _number(weight.value) * (_LB_TO_KG if weight.unit == "lb" else 1.0)
        weight_kg = round(kg, 1)

    crcl = _vital(entities, "creatinine clearance")

    pregnancy = next((e for e in entities if e.type == EntityType.DIAGNOSIS and e.normalized == "pregnancy"
                      and e.status != EntityStatus.FAMILY_MEMBER), None)
    pregnant = {EntityStatus.PRESENT: True, EntityStatus.ABSENT: False}.get(pregnancy.status) if pregnancy else None

    hepatic = next((e for e in entities if e.type == EntityType.DIAGNOSIS and e.normalized == "hepatic impairment"
                    and e.status != EntityStatus.FAMILY_MEMBER), None)
    hepatic_impairment = None
    if hepatic is not None:
        hepatic_impairment = True if hepatic.status in AFFIRMED_STATUSES - {EntityStatus.POSSIBLE} else (
            False if hepatic.status == EntityStatus.ABSENT else None)

    diagnoses = [e for e in entities if e.type == EntityType.DIAGNOSIS and e.status != EntityStatus.FAMILY_MEMBER]
    conditions = None
    if diagnoses:
        conditions = sorted({e.normalized for e in diagnoses if e.status in (EntityStatus.PRESENT, EntityStatus.CURRENT,
                                                                             EntityStatus.HISTORICAL)})

    meds = [e for e in entities if e.type == EntityType.MEDICATION]
    current_medications = None
    if meds:
        current_medications = sorted({e.normalized for e in meds if e.status == EntityStatus.CURRENT})

    allergies_all = [e for e in entities if e.type == EntityType.ALLERGY]
    active = [a.normalized for a in allergies_all if a.normalized != NKDA and a.status in
              (EntityStatus.PRESENT, EntityStatus.HISTORICAL, EntityStatus.POSSIBLE, EntityStatus.UNKNOWN)]
    allergies = sorted(set(active)) if active else ([] if any(a.normalized == NKDA for a in allergies_all) else None)

    return PatientContext(
        age_years=demo.age, sex=demo.sex, weight_kg=weight_kg, pregnant=pregnant,
        creatinine_clearance_ml_min=_number(crcl.value) if crcl else None,
        hepatic_impairment=hepatic_impairment, conditions=conditions,
        current_medications=current_medications, allergies=allergies,
    )
