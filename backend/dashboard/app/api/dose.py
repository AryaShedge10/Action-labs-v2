"""Dose-suggestion decision support (prototype, not for clinical use).

* POST /api/encounters/{id}/dose-suggestion - asks the Clinical NLP service for a rule-based suggestion
  (the suggestion is computed there from the guideline extract; this service never computes doses).
* POST /api/encounters/{id}/dose-decision   - records the physician's accept / edit / reject in the audit log,
  together with the exact suggestion that was shown. Audit rows are append-only: nothing here updates or deletes one.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from ..auth import Principal, require_physician
from ..config import get_settings
from ..database import get_db
from ..models.orm import Encounter
from ..services.encounter import write_audit

router = APIRouter(prefix="/api")

Decision = Literal["accepted", "edited", "rejected"]


class DoseSuggestionRequest(BaseModel):
    drug: str = Field(min_length=1, max_length=120)
    patient: dict[str, Any] | None = None     # facts the physician supplies to fill NEEDS_INFO gaps


class DoseDecisionRequest(BaseModel):
    drug: str = Field(min_length=1, max_length=120)
    decision: Decision
    suggestion: dict[str, Any]                # exactly what the physician was shown
    edited_dose: float | None = Field(default=None, gt=0)
    edited_unit: str | None = None
    edited_frequency: str | None = None
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _check(self) -> "DoseDecisionRequest":
        status = self.suggestion.get("status")
        if not status or "disclaimer" not in self.suggestion:
            raise ValueError("suggestion must be the DoseSuggestion object that was shown")
        if self.decision == "edited" and (self.edited_dose is None or not self.edited_unit):
            raise ValueError("an edited decision needs edited_dose and edited_unit")
        if self.decision != "edited" and (self.edited_dose is not None or self.edited_unit or self.edited_frequency):
            raise ValueError("edited values are only allowed with decision 'edited'")
        if self.decision == "accepted" and status != "SUGGESTED":
            raise ValueError("only a SUGGESTED dose can be accepted")
        return self


def _encounter(db: Session, encounter_id: str) -> Encounter:
    row = db.query(Encounter).filter_by(encounter_id=encounter_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Unable to load encounter.")
    return row


async def _post_dose(body: dict) -> httpx.Response:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await client.post(f"{settings.clinical_nlp_url}/dose/suggest", json=body)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Clinical NLP service unreachable: {type(exc).__name__}") from exc


async def fetch_dose_suggestion(consultation_id: str, drug: str, patient: dict | None) -> dict:
    """Use the NLP analysis stored for this encounter when there is one; encounters that never went through the NLP
    service (e.g. the demo encounter) fall back to the patient-record facts the physician sees. Missing facts still
    produce NEEDS_INFO."""
    body: dict[str, Any] = {"drug": drug, "consultation_id": consultation_id}
    if patient:
        body["patient"] = patient
    resp = await _post_dose(body)
    if resp.status_code == 404 and "No analysis stored" in resp.text:
        resp = await _post_dose({"drug": drug, "patient": patient or {}})
    if resp.status_code >= 400:
        raise HTTPException(status_code=502 if resp.status_code >= 500 else resp.status_code,
                            detail=f"Dose service error ({resp.status_code}): {resp.text[:300]}")
    return resp.json()


async def fetch_prescribed_drugs(consultation_id: str) -> list[dict]:
    """Drugs the clinician prescribed/recommended, from the NLP analysis stored for this encounter (may be none)."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{settings.clinical_nlp_url}/v1/consultations/{consultation_id}")
    except httpx.HTTPError:
        return []
    if resp.status_code != 200:
        return []
    return [{"medication": d["medication"], "intent": d["intent"], "dose": d.get("dose"),
             "frequency": d.get("frequency")} for d in resp.json().get("draft_prescriptions", [])]


@router.get("/encounters/{encounter_id}/prescribed-drugs")
async def prescribed_drugs(
    encounter_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_physician),
):
    _encounter(db, encounter_id)
    return await fetch_prescribed_drugs(encounter_id)


@router.post("/encounters/{encounter_id}/dose-suggestion")
async def dose_suggestion(
    encounter_id: str,
    body: DoseSuggestionRequest,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_physician),
):
    _encounter(db, encounter_id)
    return await fetch_dose_suggestion(encounter_id, body.drug, body.patient)


@router.post("/encounters/{encounter_id}/dose-decision")
def dose_decision(
    encounter_id: str,
    body: DoseDecisionRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_physician),
):
    row = _encounter(db, encounter_id)
    if row.workflow_status == "finalized":
        raise HTTPException(status_code=409, detail="Unable to record a dose decision on a finalized note.")
    shown = json.dumps(body.suggestion, sort_keys=True, separators=(",", ":"))
    record = {
        "drug": body.drug,
        "decision": body.decision,
        "edited": ({"dose": body.edited_dose, "unit": body.edited_unit, "frequency": body.edited_frequency}
                   if body.decision == "edited" else None),
        "reason": body.reason,
        "suggestion_sha256": hashlib.sha256(shown.encode()).hexdigest(),
        "suggestion_shown": body.suggestion,
        "label": "decision support prototype, not for clinical use",
    }
    write_audit(db, row, f"dose_suggestion_{body.decision}", json.dumps(record, sort_keys=True),
                physician_id=principal.physician_id)
    db.commit()
    return {"recorded": True, "action": f"dose_suggestion_{body.decision}",
            "suggestion_sha256": record["suggestion_sha256"]}
