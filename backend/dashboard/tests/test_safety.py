from app.schemas.team_b import Claim, Patient, Transcript, TranscriptSegment
from app.services.demo import demo_payload
from app.services.fhir import build_fhir_bundle
from app.validators.conflicts import (
    detect_allergy_conflicts,
    detect_demographic_conflicts,
    detect_transcript_contradictions,
)
from app.validators.grounding import claim_is_grounded, validate_encounter
from app.models.orm import Encounter
from datetime import datetime, timezone


def _patient(**kwargs) -> Patient:
    base = dict(
        id="P001",
        name="Test Patient",
        age=42,
        sex="male",
        allergies=["penicillin"],
        medications=["metformin"],
    )
    base.update(kwargs)
    return Patient(**base)


def _seg(id_: str, text: str) -> TranscriptSegment:
    return TranscriptSegment(id=id_, speaker="patient", start=0, end=1, text=text, confidence=0.9)


def test_team_b_json_valid():
    payload = demo_payload()
    assert payload.encounter_id == "ENC-2026-00124"
    assert payload.patient.id == "P001"


def test_citation_grounding_supported():
    transcript = Transcript(segments=[_seg("SEG001", "I have a headache.")])
    claim = Claim(id="C1", text="Patient reports headache.", section="subjective", citations=["SEG001"])
    assert claim_is_grounded(claim, transcript)


def test_citation_missing_is_ungrounded():
    transcript = Transcript(segments=[_seg("SEG001", "I have a headache.")])
    claim = Claim(id="C1", text="Patient has asthma.", section="assessment", citations=[])
    assert not claim_is_grounded(claim, transcript)


def test_penicillin_amoxicillin_critical():
    patient = _patient()
    claims = [
        Claim(id="C1", text="Amoxicillin prescribed.", section="plan", citations=[]),
    ]
    conflicts = detect_allergy_conflicts(patient, claims)
    assert any(item.severity == "CRITICAL" for item in conflicts)


def test_male_pregnancy_demographic():
    patient = _patient(sex="male")
    claims = [Claim(id="C1", text="Patient is currently pregnant.", section="assessment")]
    conflicts = detect_demographic_conflicts(patient, claims)
    assert any(item.category == "demographic" for item in conflicts)


def test_incorrect_age():
    patient = _patient(age=12)
    claims = [Claim(id="C1", text="Patient is a 65-year-old male.", section="subjective")]
    conflicts = detect_demographic_conflicts(patient, claims)
    assert any(item.category == "age" for item in conflicts)


def test_denies_chest_pain_contradiction():
    transcript = Transcript(segments=[_seg("SEG003", "Patient denies chest pain.")])
    claims = [Claim(id="C1", text="Patient reports chest pain.", section="subjective")]
    conflicts = detect_transcript_contradictions(transcript, claims)
    assert conflicts


def test_unsupported_diagnosis_asthma():
    payload = demo_payload()
    result = validate_encounter(payload.patient, payload.transcript, payload.claims)
    asthma = next(item for item in result["claims"] if item["claim_id"] == "CLM006")
    assert asthma["status"] in {"unsupported", "conflict"}


def test_unsupported_medication_amoxicillin():
    payload = demo_payload()
    result = validate_encounter(payload.patient, payload.transcript, payload.claims)
    amox = next(item for item in result["claims"] if item["claim_id"] == "CLM008")
    assert amox["status"] == "conflict"
    assert result["critical_conflicts"] >= 1


def test_grounding_score_not_perfect_on_demo():
    payload = demo_payload()
    result = validate_encounter(payload.patient, payload.transcript, payload.claims)
    assert result["summary"]["grounding_score"] < 100
    assert result["summary"]["unsupported_claims"] >= 1


def test_fhir_bundle_structure():
    payload = demo_payload()
    encounter = Encounter(
        encounter_id=payload.encounter_id,
        physician_id="phys-001",
        physician_name="Dr. Smith",
        encounter_at=datetime.now(timezone.utc),
        patient=payload.patient.model_dump(),
        transcript=payload.transcript.model_dump(),
        clinical_note=payload.clinical_note.model_dump(),
        claims=[c.model_dump() for c in payload.claims],
        original_note=payload.clinical_note.model_dump(),
        original_claims=[c.model_dump() for c in payload.claims],
        acknowledgements={},
        workflow_status="draft",
    )
    bundle = build_fhir_bundle(encounter, "Dr. Smith")
    assert bundle["resourceType"] == "Bundle"
    types = {entry["resource"]["resourceType"] for entry in bundle["entry"]}
    assert "Patient" in types
    assert "Encounter" in types
    assert "AllergyIntolerance" in types
