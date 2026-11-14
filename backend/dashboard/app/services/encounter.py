from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models.orm import AuditEvent, Encounter
from ..schemas.team_b import Claim, ClinicalNote, Patient, TeamBPayload, Transcript


def write_audit(
    db: Session,
    encounter: Encounter,
    action: str,
    detail: str = "",
    physician_id: str | None = None,
) -> None:
    db.add(
        AuditEvent(
            encounter_pk=encounter.id,
            encounter_id=encounter.encounter_id,
            physician_id=physician_id or encounter.physician_id,
            action=action,
            detail=detail,
        )
    )


def payload_from_row(row: Encounter) -> tuple[Patient, Transcript, list[Claim], ClinicalNote]:
    patient = Patient.model_validate(row.patient)
    transcript = Transcript.model_validate(row.transcript)
    claims = [Claim.model_validate(item) for item in row.claims]
    note = ClinicalNote.model_validate(row.clinical_note)
    return patient, transcript, claims, note


def ingest_payload(
    db: Session,
    payload: TeamBPayload,
    physician_id: str,
    physician_name: str,
) -> Encounter:
    existing = db.query(Encounter).filter_by(encounter_id=payload.encounter_id).one_or_none()
    encounter_at = payload.encounter_at or datetime.now(timezone.utc)
    data = {
        "physician_id": payload.physician_id or physician_id,
        "physician_name": payload.physician_name or physician_name,
        "encounter_at": encounter_at,
        "ai_status": "draft_ready",
        "validation_status": "required",
        "workflow_status": "draft",
        "patient": payload.patient.model_dump(),
        "transcript": payload.transcript.model_dump(),
        "clinical_note": payload.clinical_note.model_dump(),
        "claims": [claim.model_dump() for claim in payload.claims],
        "original_note": payload.clinical_note.model_dump(),
        "original_claims": [claim.model_dump() for claim in payload.claims],
        "acknowledgements": {},
        "reviewed": False,
        "finalized_at": None,
    }
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        row = existing
        action = "ai_draft_replaced"
    else:
        row = Encounter(encounter_id=payload.encounter_id, **data)
        db.add(row)
        db.flush()
        action = "ai_generated_soap_note"
    write_audit(db, row, action, "Structured Team B payload ingested.")
    db.commit()
    db.refresh(row)
    return row
