import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.pipeline import ClinicalPipeline
from tests.conftest import make_payload

FULL = dict(age_years=40, sex="male", weight_kg=70, creatinine_clearance_ml_min=90, hepatic_impairment=False,
            conditions=[], current_medications=[], allergies=[])


@pytest.fixture
def client(tmp_path):
    settings = Settings(store_path=str(tmp_path / "t.db"), extraction_mode="rule", generation_mode="template")
    app = create_app(settings, pipeline=ClinicalPipeline(settings, use_llm=False))
    with TestClient(app) as c:
        yield c


def test_explicit_patient(client):
    r = client.post("/dose/suggest", json={"drug": "amlodipine", "patient": FULL})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "SUGGESTED" and body["start_dose"] == 5 and body["unit"] == "mg"
    assert body["max_daily_dose"] == 10
    assert "not for clinical use" in body["disclaimer"].lower()
    assert body["citations"] and body["citations"][0]["page"] >= 1


def test_unknown_drug_not_supported(client):
    body = client.post("/dose/suggest", json={"drug": "ibuprofen", "patient": FULL}).json()
    assert body["status"] == "NOT_SUPPORTED"


def test_empty_patient_needs_info(client):
    body = client.post("/dose/suggest", json={"drug": "enalapril", "patient": {}}).json()
    assert body["status"] == "NEEDS_INFO" and "age_years" in body["needs_info"]


def test_consultation_id_uses_stored_analysis_and_overrides(client):
    payload = make_payload(("DOCTOR", "This is a 70-year-old man. Any allergies?"), ("PATIENT", "No known drug allergies."),
                           consultation_id="dose_c1")
    assert client.post("/v1/analyze", json=payload).status_code == 200
    first = client.post("/dose/suggest", json={"drug": "amlodipine", "consultation_id": "dose_c1"}).json()
    assert first["status"] == "NEEDS_INFO" and "age_years" not in first["needs_info"]
    assert "allergies" not in first["needs_info"]
    filled = client.post("/dose/suggest", json={
        "drug": "amlodipine", "consultation_id": "dose_c1",
        "patient": {"hepatic_impairment": False, "current_medications": [], "conditions": []}}).json()
    assert filled["status"] == "SUGGESTED" and filled["start_dose"] == 2.5   # age 70 > 60


def test_unknown_consultation_404(client):
    assert client.post("/dose/suggest", json={"drug": "amlodipine", "consultation_id": "nope"}).status_code == 404


def test_requires_consultation_or_patient(client):
    assert client.post("/dose/suggest", json={"drug": "amlodipine"}).status_code == 422


def test_rejects_implausible_values(client):
    assert client.post("/dose/suggest", json={"drug": "amlodipine", "patient": {"age_years": -5}}).status_code == 422
