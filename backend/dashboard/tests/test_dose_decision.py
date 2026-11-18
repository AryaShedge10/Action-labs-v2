import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import dose as dose_api
from app.auth import Principal, require_physician
from app.database import Base, get_db
from app.main import app
from app.models.orm import AuditEvent
from app.services.demo import demo_payload
from app.services.encounter import ingest_payload

SUGGESTION = {"status": "SUGGESTED", "drug": "amlodipine", "start_dose": 5, "unit": "mg", "frequency": "once daily",
              "max_daily_dose": 10, "citations": [{"page": 47, "table_or_section": "Annexure 3", "supports": "start dose"}],
              "disclaimer": "Decision support prototype, not for clinical use."}


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    with Session() as db:
        enc = ingest_payload(db, demo_payload(), "dr1", "Dr One")
        enc_id = enc.encounter_id

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[require_physician] = lambda: Principal("dr1", "Dr One")
    c = TestClient(app)
    c.enc_id, c.Session = enc_id, Session
    yield c
    app.dependency_overrides.clear()


def audits(client, prefix="dose_suggestion"):
    with client.Session() as db:
        return [a for a in db.query(AuditEvent).order_by(AuditEvent.id) if a.action.startswith(prefix)]


def post(client, **over):
    body = {"drug": "amlodipine", "decision": "accepted", "suggestion": SUGGESTION, **over}
    return client.post(f"/api/encounters/{client.enc_id}/dose-decision", json=body)


def test_accept_is_audited_with_the_suggestion_shown(client):
    assert post(client).status_code == 200
    (event,) = audits(client)
    detail = json.loads(event.detail)
    assert event.action == "dose_suggestion_accepted" and event.physician_id == "dr1"
    assert detail["suggestion_shown"] == SUGGESTION and len(detail["suggestion_sha256"]) == 64
    assert "not for clinical use" in detail["label"]


def test_edit_records_new_value(client):
    assert post(client, decision="edited", edited_dose=2.5, edited_unit="mg", reason="elderly").status_code == 200
    detail = json.loads(audits(client)[0].detail)
    assert detail["edited"] == {"dose": 2.5, "unit": "mg", "frequency": None} and detail["reason"] == "elderly"


def test_reject_is_audited(client):
    assert post(client, decision="rejected", reason="not appropriate").status_code == 200
    assert audits(client)[0].action == "dose_suggestion_rejected"


def test_edit_requires_new_value(client):
    assert post(client, decision="edited").status_code == 422


def test_edited_values_rejected_on_accept(client):
    assert post(client, edited_dose=3, edited_unit="mg").status_code == 422


def test_cannot_accept_a_non_suggestion(client):
    bad = {**SUGGESTION, "status": "NEEDS_INFO"}
    assert post(client, suggestion=bad).status_code == 422
    assert post(client, suggestion=bad, decision="rejected").status_code == 200


def test_suggestion_must_be_a_real_dose_suggestion(client):
    assert post(client, suggestion={"foo": 1}).status_code == 422


def test_unknown_encounter_404(client):
    r = client.post("/api/encounters/nope/dose-decision",
                    json={"drug": "a", "decision": "rejected", "suggestion": SUGGESTION})
    assert r.status_code == 404


def test_finalized_note_rejected(client):
    with client.Session() as db:
        from app.models.orm import Encounter
        row = db.query(Encounter).filter_by(encounter_id=client.enc_id).one()
        row.workflow_status = "finalized"
        db.commit()
    assert post(client).status_code == 409


def test_audit_log_has_no_mutation_endpoints(client):
    methods = {(r.path, m) for r in app.routes if "audit" in getattr(r, "path", "") for m in getattr(r, "methods", [])}
    assert all(m in ("GET", "HEAD") for _, m in methods)


def test_decisions_appear_in_audit_endpoint_in_order(client):
    post(client)
    post(client, decision="rejected")
    events = client.get(f"/api/encounters/{client.enc_id}/audit").json()
    actions = [e["action"] for e in events if e["action"].startswith("dose_")]
    assert actions == ["dose_suggestion_accepted", "dose_suggestion_rejected"]


def test_suggestion_proxy_passes_consultation_id(client, monkeypatch):
    seen = {}

    async def fake(consultation_id, drug, patient):
        seen.update(c=consultation_id, d=drug, p=patient)
        return SUGGESTION

    monkeypatch.setattr(dose_api, "fetch_dose_suggestion", fake)
    r = client.post(f"/api/encounters/{client.enc_id}/dose-suggestion",
                    json={"drug": "amlodipine", "patient": {"hepatic_impairment": False}})
    assert r.status_code == 200 and r.json()["status"] == "SUGGESTED"
    assert seen == {"c": client.enc_id, "d": "amlodipine", "p": {"hepatic_impairment": False}}


def test_prescribed_drugs_proxy(client, monkeypatch):
    async def fake(consultation_id):
        return [{"medication": "Amlodipine", "intent": "PRESCRIBED", "dose": None, "frequency": None}]

    monkeypatch.setattr(dose_api, "fetch_prescribed_drugs", fake)
    r = client.get(f"/api/encounters/{client.enc_id}/prescribed-drugs")
    assert r.status_code == 200 and r.json()[0]["medication"] == "Amlodipine"
    assert client.get("/api/encounters/nope/prescribed-drugs").status_code == 404
