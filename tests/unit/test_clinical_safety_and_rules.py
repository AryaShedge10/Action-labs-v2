"""
Unit Tests: Clinical Safety Engine, Negation, Historical Attribution, and Conflict Detection.
"""
import pytest
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "services" / "clinical_nlp"))
sys.path.insert(0, str(root / "backend" / "dashboard"))

from services.clinical_nlp.app.safety.allergy_rules import AllergyMedicationRule
from services.clinical_nlp.app.safety.engine import SafetyEngine
from services.clinical_nlp.app.nlp.context import analyze
from backend.dashboard.app.validators.conflicts import run_conflict_engine
from backend.dashboard.app.schemas.team_b import Patient, Claim, Transcript, TranscriptSegment


def test_penicillin_amoxicillin_allergy_conflict():
    """Verify that prescribing Amoxicillin to a patient allergic to Penicillin produces CRITICAL conflict."""
    patient = Patient(
        id="PT-ALLERGY-01",
        name="John Doe",
        age=45,
        sex="male",
        allergies=["penicillin"],
        medications=[],
    )

    claims = [
        Claim(
            id="c1",
            text="Prescribed amoxicillin 500mg PO TID for 10 days.",
            section="plan",
            citations=["s1"],
            origin="ai",
        )
    ]

    transcript = Transcript(
        segments=[
            TranscriptSegment(
                id="s1",
                speaker="physician",
                start=0.0,
                end=3.0,
                text="I will give you amoxicillin for the infection.",
            )
        ]
    )

    conflicts = run_conflict_engine(patient, transcript, claims)
    allergy_conflicts = [c for c in conflicts if c.category == "allergy"]
    
    assert len(allergy_conflicts) > 0
    assert any(c.severity in ("CRITICAL", "HIGH") for c in allergy_conflicts)
    assert any("penicillin" in c.message.lower() or "amoxicillin" in c.message.lower() for c in allergy_conflicts)


def test_negation_detection_prevents_false_symptom():
    """Verify that 'no chest pain' is correctly recognized as negated."""
    text_negated = "Patient reports no chest pain and denies any shortness of breath."
    idx = text_negated.find("chest pain")
    ctx_chest = analyze(text_negated, idx, idx + len("chest pain"))
    assert ctx_chest.negated is True

    text_positive = "Patient reports sharp central chest pain radiating to the jaw."
    idx_pos = text_positive.find("chest pain")
    ctx_positive = analyze(text_positive, idx_pos, idx_pos + len("chest pain"))
    assert ctx_positive.negated is False


def test_historical_context_classification():
    """Verify that childhood medical events are recognized as historical."""
    text_history = "I had childhood asthma twenty years ago, but it has completely resolved."
    idx = text_history.find("asthma")
    ctx = analyze(text_history, idx, idx + len("asthma"))
    assert ctx.historical is True or ctx.resolved is True


def test_unknown_patient_age_does_not_trigger_spurious_conflict():
    """Verify that unstated/null patient age does not falsely trigger age discrepancy conflicts."""
    patient = Patient(
        id="PT-NO-AGE",
        name="Jane Doe",
        age=None,
        sex="female",
        allergies=[],
        medications=[],
    )

    claims = [
        Claim(
            id="c1",
            text="The 42-year-old female presents for follow up.",
            section="subjective",
            citations=["s1"],
            origin="ai",
        )
    ]

    transcript = Transcript(
        segments=[
            TranscriptSegment(
                id="s1",
                speaker="patient",
                start=0.0,
                end=2.0,
                text="I am here for follow up.",
            )
        ]
    )

    conflicts = run_conflict_engine(patient, transcript, claims)
    # When patient age is unknown (None), no age conflict should be generated
    age_conflicts = [c for c in conflicts if c.category == "demographic" and "age" in c.title.lower()]
    assert len(age_conflicts) == 0

