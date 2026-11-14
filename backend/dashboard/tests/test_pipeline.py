from app.services.demo import demo_payload
from app.validators.grounding import validate_encounter


def test_team_b_to_validation_pipeline():
    payload = demo_payload()
    result = validate_encounter(payload.patient, payload.transcript, payload.claims)
    assert result["critical_conflicts"] >= 1
    assert any(item["claim_id"] == "CLM006" for item in result["claims"])
    assert result["banner"] == "Physician Review Required"
