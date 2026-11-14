"""
Failure Mode Tests: Verifies safe degradation and clear error reporting.
"""
import pytest
import sys
from pathlib import Path
from pydantic import ValidationError

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "services" / "clinical_nlp"))
sys.path.insert(0, str(root / "backend" / "dashboard"))

from shared.contracts.transcript import TranscriptSegment, TranscriptPayload
from backend.dashboard.app.auth import decode_and_verify_token, create_access_token
from fastapi import HTTPException


def test_transcript_end_time_before_start_time_raises():
    """Verify that inverted timestamps raise ValidationError."""
    with pytest.raises(ValidationError):
        TranscriptSegment(
            speaker="DOCTOR",
            start_time=10.0,
            end_time=5.0,  # invalid!
            text="Testing inverted time.",
        )


def test_empty_segments_transcript_fails():
    """Verify that an empty transcript raises ValidationError."""
    with pytest.raises(ValidationError):
        TranscriptPayload(
            consultation_id="FAIL-EMPTY",
            segments=[],  # min_length=1 required
        )


def test_invalid_jwt_signature_raises_http_401():
    """Verify that a tampered or invalid JWT signature raises HTTP 401."""
    valid_token = create_access_token("phys-001", "Dr. Test", secret_key="real-secret")
    tampered_token = valid_token[:-4] + "fake"

    with pytest.raises(HTTPException) as exc_info:
        decode_and_verify_token(tampered_token, secret_key="real-secret")

    assert exc_info.value.status_code == 401


def test_expired_jwt_raises_http_401():
    """Verify that an expired token raises HTTP 401."""
    expired_token = create_access_token("phys-001", "Dr. Test", expires_delta_seconds=-10, secret_key="real-secret")

    with pytest.raises(HTTPException) as exc_info:
        decode_and_verify_token(expired_token, secret_key="real-secret")

    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()

