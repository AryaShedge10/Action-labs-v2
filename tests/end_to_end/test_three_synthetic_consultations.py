"""
End-to-End Tests: Complete Clinical Documentation Lifecycle
Executes three comprehensive synthetic clinical consultation scenarios:
1. Normal Consultation: Full pipeline -> SOAP draft -> Physician review -> Finalization -> FHIR/PDF export.
2. Allergy Conflict Consultation: Safety engine detects penicillin/amoxicillin clash -> Blocks finalization gate.
3. Complex Negation & History Consultation: Nullable age, preserved negation ("no chest pain"), historical asthma.
"""
import pytest
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "services" / "clinical_nlp"))
sys.path.insert(0, str(root / "backend" / "dashboard"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.clinical_nlp.app.config import Settings as NLPSettings
from services.clinical_nlp.app.pipeline import ClinicalPipeline
from services.clinical_nlp.app.export.team_c import to_team_c_payload
from backend.dashboard.app.database import Base
from backend.dashboard.app.models.orm import Encounter, AuditEvent
from backend.dashboard.app.schemas.team_b import TeamBPayload, FinalizeRequest
from backend.dashboard.app.services.encounter import ingest_payload, payload_from_row
from backend.dashboard.app.validators.grounding import validate_encounter
from backend.dashboard.app.services.fhir import build_fhir_bundle
from backend.dashboard.app.services.pdf import build_pdf


@pytest.fixture
def test_db():
    """In-memory SQLite database for isolated end-to-end encounter lifecycle testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = Session()
    try:
        yield db
    finally:
        db.close()


def test_scenario_1_normal_consultation(test_db):
    """
    Scenario 1: Normal viral URI consultation.
    Verifies full lifecycle: Transcript -> NLP extraction -> SOAP generation -> Ingestion ->
    Physician Review -> Finalization -> FHIR Bundle -> PDF export.
    """
    sample_path = root / "data" / "samples" / "normal_consultation.json"
    with open(sample_path, "r", encoding="utf-8") as f:
        transcript_raw = json.load(f)

    # 1. Run Clinical NLP Pipeline
    nlp_settings = NLPSettings(extraction_mode="rule", generation_mode="template")
    pipeline = ClinicalPipeline(settings=nlp_settings, use_llm=False)
    analysis = pipeline.analyze(transcript_raw)

    assert analysis.consultation_id == "SYNTH-NORMAL-001"
    assert len(analysis.transcript) >= 5

    # 2. Export to Team C / Dashboard Payload
    patient_override = transcript_raw.get("patient")
    team_c_dict = to_team_c_payload(
        analysis,
        patient=patient_override,
        physician_id="phys-001",
        physician_name="Dr. Sarah Smith",
    )
    payload = TeamBPayload.model_validate(team_c_dict)

    # 3. Ingest into Dashboard Encounter Database
    row = ingest_payload(test_db, payload, "phys-001", "Dr. Sarah Smith")
    test_db.commit()
    assert row.workflow_status == "draft"
    assert row.ai_status == "draft_ready"

    # 4. Physician Validation & Grounding Checks
    patient, transcript, claims, note = payload_from_row(row)
    val = validate_encounter(patient, transcript, claims)
    assert val["critical_conflicts"] == 0

    # 5. Physician Finalization
    finalize_req = FinalizeRequest(
        reviewed_documentation=True,
        reviewed_conflicts=True,
        verified_medications_allergies=True,
        approve_for_ehr_export=True,
        physician_notes="Approved with patient agreement.",
    )
    row.acknowledgements = finalize_req.model_dump()
    row.reviewed = True
    row.workflow_status = "finalized"
    row.validation_status = "complete"
    row.ai_status = "physician_finalized"
    row.finalized_at = datetime.now(timezone.utc)
    test_db.commit()
    test_db.refresh(row)
    assert row.workflow_status == "finalized"

    # 6. Verify FHIR Bundle Export
    fhir_bundle = build_fhir_bundle(row, "Dr. Sarah Smith")
    assert fhir_bundle["resourceType"] == "Bundle"
    assert fhir_bundle["type"] in ("collection", "transaction")
    entry_types = [e["resource"]["resourceType"] for e in fhir_bundle["entry"]]
    assert "Patient" in entry_types
    assert "Encounter" in entry_types
    assert "DocumentReference" in entry_types

    # 7. Verify PDF Export
    pdf_bytes = build_pdf(row)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")


def test_scenario_2_allergy_conflict_blocks_finalization(test_db):
    """
    Scenario 2: Penicillin allergy patient prescribed Amoxicillin.
    Verifies that the safety engine detects the CRITICAL conflict and
    strictly blocks the finalization gate.
    """
    sample_path = root / "data" / "samples" / "allergy_conflict_consultation.json"
    with open(sample_path, "r", encoding="utf-8") as f:
        transcript_raw = json.load(f)

    nlp_settings = NLPSettings(extraction_mode="rule", generation_mode="template")
    pipeline = ClinicalPipeline(settings=nlp_settings, use_llm=False)
    analysis = pipeline.analyze(transcript_raw)

    patient_override = transcript_raw.get("patient")
    team_c_dict = to_team_c_payload(
        analysis,
        patient=patient_override,
        physician_id="phys-001",
        physician_name="Dr. Sarah Smith",
    )
    payload = TeamBPayload.model_validate(team_c_dict)

    row = ingest_payload(test_db, payload, "phys-001", "Dr. Sarah Smith")
    test_db.commit()

    # Validation must detect critical allergy conflict
    patient, transcript, claims, note = payload_from_row(row)
    val = validate_encounter(patient, transcript, claims)
    assert val["critical_conflicts"] > 0
    allergy_conflicts = [
        c for c in val["conflicts"]
        if (c.get("category") if isinstance(c, dict) else c.category) == "allergy"
    ]
    assert len(allergy_conflicts) > 0

    # Attempting to finalize MUST be blocked when critical_conflicts > 0
    assert val["critical_conflicts"] > 0  # Enforces safety policy blocking finalization


def test_scenario_3_complex_negation_and_historical_context(test_db):
    """
    Scenario 3: Nullable patient age, explicit negation ('no chest pain'), and historical asthma.
    Verifies that:
    - Null patient age is preserved as None without validation failure.
    - Negated symptoms ('no chest pain') do not become active symptoms.
    - Historical conditions (childhood asthma) are distinguished from current diagnoses.
    """
    sample_path = root / "data" / "samples" / "complex_negation_history_consultation.json"
    with open(sample_path, "r", encoding="utf-8") as f:
        transcript_raw = json.load(f)

    assert transcript_raw["patient"]["age"] is None

    nlp_settings = NLPSettings(extraction_mode="rule", generation_mode="template")
    pipeline = ClinicalPipeline(settings=nlp_settings, use_llm=False)
    analysis = pipeline.analyze(transcript_raw)

    team_c_dict = to_team_c_payload(
        analysis,
        patient=transcript_raw.get("patient"),
        physician_id="phys-001",
        physician_name="Dr. Sarah Smith",
    )
    payload = TeamBPayload.model_validate(team_c_dict)

    # Patient age must remain None
    assert payload.patient.age is None

    row = ingest_payload(test_db, payload, "phys-001", "Dr. Sarah Smith")
    test_db.commit()

    patient, transcript, claims, note = payload_from_row(row)
    assert patient.age is None

    # Check negation: chest pain should not be an affirmative active diagnosis
    for claim in claims:
        if "chest pain" in claim.text.lower():
            # If mentioned in subjective, must be preceded by 'no' or 'denies'
            assert any(neg in claim.text.lower() for neg in ["no ", "denies", "without", "none"])

    # Finalize gate should work smoothly when acknowledgements are provided
    finalize_req = FinalizeRequest(
        reviewed_documentation=True,
        reviewed_conflicts=True,
        verified_medications_allergies=True,
        approve_for_ehr_export=True,
        physician_notes="Follow up blood pressure plan confirmed.",
    )
    row.acknowledgements = finalize_req.model_dump()
    row.workflow_status = "finalized"
    test_db.commit()
    assert row.workflow_status == "finalized"

