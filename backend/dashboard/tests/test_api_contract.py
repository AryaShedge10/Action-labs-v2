from pydantic import ValidationError

from app.schemas.team_b import TeamBPayload
from app.services.demo import demo_payload


def test_health_disclaimer_in_payload_contract():
    payload = demo_payload()
    dumped = payload.model_dump()
    parsed = TeamBPayload.model_validate(dumped)
    assert parsed.patient.id == "P001"


def test_rejects_malformed_payload():
    try:
        TeamBPayload.model_validate({"encounter_id": "x"})
        raise AssertionError("should reject")
    except ValidationError:
        pass


def test_missing_patient_identifier_invalid():
    payload = demo_payload().model_dump()
    payload["patient"]["id"] = ""
    try:
        TeamBPayload.model_validate(payload)
        raise AssertionError("should reject empty patient id")
    except ValidationError:
        pass
