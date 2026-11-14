"""
Contract Tests: Verifies seamless serialization and compatibility across
Transcription (2A) -> Clinical NLP (2B) -> Dashboard & EHR (2C).
"""
import pytest
import sys
from pathlib import Path

# Add unified root to python path
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))

from shared.contracts.transcript import TranscriptSegment, TranscriptPayload
from shared.contracts.clinical_analysis import ClinicalAnalysisContract, ConflictSeverity
from shared.contracts.encounter import EncounterContract, PatientProfile
from backend.dashboard.app.schemas.team_b import TeamBPayload, Patient as DashboardPatient


def test_2a_transcript_accepted_by_contract():
    """Verify 2A output with start_time/end_time is accepted and normalizes start/end."""
    raw_2a = {
        "consultation_id": "TEST-2A-001",
        "language": "en-US",
        "segments": [
            {
                "speaker": "DOCTOR",
                "start_time": 0.0,
                "end_time": 3.45,
                "text": "What symptoms are you experiencing?",
                "confidence": 0.98,
            },
            {
                "speaker": "PATIENT",
                "start_time": 3.8,
                "end_time": 7.2,
                "text": "I have had a sore throat for three days.",
                "confidence": 0.96,
            },
        ],
    }

    transcript = TranscriptPayload.model_validate(raw_2a)
    assert transcript.consultation_id == "TEST-2A-001"
    assert len(transcript.segments) == 2

    # Check that start and end are normalized from start_time and end_time
    s0 = transcript.segments[0]
    assert s0.start_time == 0.0
    assert s0.start == 0.0
    assert s0.end_time == 3.45
    assert s0.end == 3.45

    # Check dashboard dictionary generation
    dash_dict = transcript.to_dashboard_dict()
    assert len(dash_dict["segments"]) == 2
    assert dash_dict["segments"][0]["start"] == 0.0
    assert dash_dict["segments"][0]["end"] == 3.45


def test_nullable_patient_age_contract():
    """Verify that unstated patient age is represented as null, not invented."""
    patient_data_null_age = {
        "id": "PT-UNKNOWN-AGE",
        "name": "Jane Doe",
        "age": None,
        "sex": "female",
        "allergies": ["penicillin"],
        "medications": [],
    }

    # Verify shared contract accepts null age
    patient = PatientProfile.model_validate(patient_data_null_age)
    assert patient.age is None

    # Verify dashboard schema accepts null age
    dash_patient = DashboardPatient.model_validate(patient_data_null_age)
    assert dash_patient.age is None


def test_2b_export_accepted_by_2c_dashboard():
    """Verify that Team B export format validates cleanly into Team C's TeamBPayload."""
    payload = {
        "encounter_id": "ENC-VERIFY-001",
        "patient": {
            "id": "PT-001",
            "name": "Test Patient",
            "age": None,
            "sex": "male",
            "allergies": ["aspirin"],
            "medications": ["lisinopril"],
        },
        "transcript": {
            "segments": [
                {
                    "id": "seg_001",
                    "speaker": "physician",
                    "start": 0.0,
                    "end": 2.5,
                    "text": "How is your blood pressure?",
                    "confidence": 0.99,
                    "source_type": "transcript",
                }
            ]
        },
        "clinical_note": {
            "subjective": [
                {
                    "id": "claim_001",
                    "text": "Patient reports well-controlled blood pressure.",
                    "citations": ["seg_001"],
                    "origin": "ai",
                    "deleted": False,
                }
            ],
            "objective": [],
            "assessment": [],
            "plan": [],
        },
        "claims": [
            {
                "id": "claim_001",
                "text": "Patient reports well-controlled blood pressure.",
                "section": "subjective",
                "citations": ["seg_001"],
                "confidence": 0.95,
                "origin": "ai",
                "deleted": False,
            }
        ],
    }

    team_b_parsed = TeamBPayload.model_validate(payload)
    assert team_b_parsed.encounter_id == "ENC-VERIFY-001"
    assert team_b_parsed.patient.age is None
    assert len(team_b_parsed.transcript.segments) == 1
    assert team_b_parsed.transcript.segments[0].citations if hasattr(team_b_parsed.transcript.segments[0], "citations") else True
    assert team_b_parsed.claims[0].citations == ["seg_001"]


def test_timestamp_field_equivalence():
    """Verify that both {start, end} and {start_time, end_time} are accepted transparently."""
    dash_style_seg = {
        "speaker": "physician",
        "start": 1.25,
        "end": 4.50,
        "text": "Taking deep breaths.",
    }
    seg = TranscriptSegment.model_validate(dash_style_seg)
    assert seg.start == 1.25
    assert seg.start_time == 1.25
    assert seg.end == 4.50
    assert seg.end_time == 4.50

