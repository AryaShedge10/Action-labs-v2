import httpx

from ..config import get_settings
from ..models.orm import Encounter, EhrHandoff
from ..services.fhir import build_fhir_bundle
from sqlalchemy.orm import Session


def handoff_to_mock_ehr(db: Session, encounter: Encounter) -> dict:
    if encounter.workflow_status != "finalized":
        raise ValueError("Note must be physician-finalized before EHR handoff.")
    settings = get_settings()
    bundle = build_fhir_bundle(encounter, encounter.physician_name)
    payload = {
        "encounter_id": encounter.encounter_id,
        "physician_id": encounter.physician_id,
        "bundle": bundle,
        "patient": encounter.patient,
    }
    try:
        response = httpx.post(
            f"{settings.mock_ehr_url.rstrip('/')}/api/handoff",
            json=payload,
            timeout=10.0,
        )
        response.raise_for_status()
        summary = response.json()
        status = summary.get("status", "SUCCESS")
    except httpx.HTTPError as exc:
        summary = {
            "status": "FAILED",
            "error": "EHR handoff failed.",
            "detail": "The mock EHR did not accept the bundle.",
        }
        status = "FAILED"
        _ = str(exc)
    row = EhrHandoff(
        encounter_pk=encounter.id,
        encounter_id=encounter.encounter_id,
        status=status,
        summary=summary,
    )
    db.add(row)
    db.commit()
    return summary
