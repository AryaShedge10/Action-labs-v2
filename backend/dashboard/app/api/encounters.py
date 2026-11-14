from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
import httpx
from datetime import datetime, timezone
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ..auth import Principal, require_physician
from ..config import get_settings
from ..database import get_db
from ..models.orm import AuditEvent, Encounter
from ..schemas.team_b import FinalizeRequest, NotePatch, TeamBPayload
from ..services.demo import demo_payload
from ..services.encounter import ingest_payload, payload_from_row, write_audit
from ..services.fhir import build_fhir_bundle
from ..services.pdf import build_pdf
from ..validators.grounding import validate_encounter

router = APIRouter(prefix="/api")


def _get_encounter(db: Session, encounter_id: str) -> Encounter:
    row = db.query(Encounter).filter_by(encounter_id=encounter_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Unable to load encounter.")
    return row


def _serialize(row: Encounter) -> dict:
    patient, transcript, claims, note = payload_from_row(row)
    validation = validate_encounter(patient, transcript, claims)
    return {
        "encounter_id": row.encounter_id,
        "physician_id": row.physician_id,
        "physician_name": row.physician_name,
        "encounter_at": row.encounter_at.isoformat(),
        "ai_status": row.ai_status,
        "validation_status": row.validation_status,
        "workflow_status": row.workflow_status,
        "reviewed": row.reviewed,
        "finalized_at": row.finalized_at.isoformat() if row.finalized_at else None,
        "patient": row.patient,
        "transcript": row.transcript,
        "clinical_note": row.clinical_note,
        "claims": row.claims,
        "acknowledgements": row.acknowledgements,
        "privacy": {
            "mode": "local_private",
            "label": "Local / Private Processing",
        },
        "validation": validation,
        "handoffs": [
            {
                "status": item.status,
                "summary": item.summary,
                "created_at": item.created_at.isoformat(),
            }
            for item in row.handoffs
        ],
    }


@router.post("/encounters")
def create_encounter(
    payload: dict,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_physician),
):
    try:
        parsed = TeamBPayload.model_validate(payload)
    except ValidationError:
        raise HTTPException(status_code=422, detail="Invalid Team B JSON.") from None
    if not parsed.patient.id:
        raise HTTPException(status_code=422, detail="Missing patient identifier.")
    row = ingest_payload(db, parsed, principal.physician_id, principal.physician_name)
    return _serialize(row)


@router.post("/demo/load")
def load_demo(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_physician),
):
    row = ingest_payload(db, demo_payload(), principal.physician_id, principal.physician_name)
    return _serialize(row)


@router.get("/encounters")
def list_encounters(
    db: Session = Depends(get_db),
    _: Principal = Depends(require_physician),
):
    rows = db.query(Encounter).order_by(Encounter.updated_at.desc()).all()
    return [
        {
            "encounter_id": row.encounter_id,
            "patient_id": row.patient.get("id"),
            "patient_display": "Patient on file",
            "encounter_at": row.encounter_at.isoformat(),
            "workflow_status": row.workflow_status,
            "ai_status": row.ai_status,
            "validation_status": row.validation_status,
            "physician_name": row.physician_name,
        }
        for row in rows
    ]


@router.get("/encounters/{encounter_id}")
def get_encounter(
    encounter_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_physician),
):
    return _serialize(_get_encounter(db, encounter_id))


@router.get("/encounters/{encounter_id}/transcript")
def get_transcript(
    encounter_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_physician),
):
    row = _get_encounter(db, encounter_id)
    if not row.transcript or not row.transcript.get("segments"):
        raise HTTPException(status_code=404, detail="Transcript unavailable.")
    return row.transcript


@router.get("/encounters/{encounter_id}/validation")
def get_validation(
    encounter_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_physician),
):
    row = _get_encounter(db, encounter_id)
    patient, transcript, claims, _ = payload_from_row(row)
    return validate_encounter(patient, transcript, claims)


@router.post("/encounters/{encounter_id}/validate")
def revalidate(
    encounter_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_physician),
):
    row = _get_encounter(db, encounter_id)
    patient, transcript, claims, _ = payload_from_row(row)
    result = validate_encounter(patient, transcript, claims)
    write_audit(db, row, "validation_rerun", "Deterministic validation executed.")
    db.commit()
    return result


@router.patch("/encounters/{encounter_id}/note")
def patch_note(
    encounter_id: str,
    body: NotePatch,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_physician),
):
    row = _get_encounter(db, encounter_id)
    if row.workflow_status == "finalized":
        raise HTTPException(status_code=409, detail="Unable to edit a finalized note.")
    previous = {claim["id"]: claim for claim in row.claims}
    row.clinical_note = body.clinical_note.model_dump()
    row.claims = [claim.model_dump() for claim in body.claims]
    if body.patient:
        row.patient = body.patient.model_dump()
        write_audit(db, row, "patient_information_corrected", "Source patient record updated by physician.")
    for claim in body.claims:
        old = previous.get(claim.id)
        if old and old.get("deleted") is False and claim.deleted:
            write_audit(
                db,
                row,
                "statement_deleted",
                f"Claim {claim.id} deleted. Reason: {body.edit_reason or 'physician edit'}.",
            )
        elif old and old.get("text") != claim.text:
            write_audit(db, row, "statement_edited", f"Claim {claim.id} edited by physician.")
        elif not old:
            write_audit(db, row, "statement_added", f"Claim {claim.id} added by physician.")
    write_audit(db, row, "note_saved", "Physician saved clinical documentation draft.")
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.post("/encounters/{encounter_id}/finalize")
def finalize_note(
    encounter_id: str,
    body: FinalizeRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_physician),
):
    row = _get_encounter(db, encounter_id)
    patient, transcript, claims, _ = payload_from_row(row)
    validation = validate_encounter(patient, transcript, claims)
    settings = get_settings()

    if not principal.physician_id:
        raise HTTPException(status_code=401, detail="Physician authentication required.")
    if validation["critical_conflicts"] > 0:
        raise HTTPException(
            status_code=409,
            detail="Unable to finalize note. Critical validation conflict detected.",
        )
    if not all(
        [
            body.reviewed_documentation,
            body.reviewed_conflicts,
            body.verified_medications_allergies,
            body.approve_for_ehr_export,
        ]
    ):
        raise HTTPException(
            status_code=400,
            detail="Unable to finalize note. All physician acknowledgements are required.",
        )
    if validation["summary"]["unsupported_claims"] >= settings.unsupported_claim_warn_threshold:
        # acknowledgements already required; proceed after explicit approval
        write_audit(
            db,
            row,
            "unsupported_claims_acknowledged",
            "Physician acknowledged remaining unsupported claims.",
        )

    from datetime import datetime, timezone

    row.acknowledgements = body.model_dump()
    row.reviewed = True
    row.workflow_status = "finalized"
    row.validation_status = "complete"
    row.ai_status = "physician_finalized"
    row.finalized_at = datetime.now(timezone.utc)
    write_audit(db, row, "note_finalized", "Physician finalized the clinical note.")
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.get("/encounters/{encounter_id}/audit")
def get_audit(
    encounter_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_physician),
):
    _get_encounter(db, encounter_id)
    events = (
        db.query(AuditEvent)
        .filter_by(encounter_id=encounter_id)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )
    return [
        {
            "time": event.created_at.isoformat(),
            "action": event.action,
            "detail": event.detail,
            "physician_id": event.physician_id,
        }
        for event in events
    ]


@router.get("/encounters/{encounter_id}/export/pdf")
def export_pdf(
    encounter_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_physician),
):
    row = _get_encounter(db, encounter_id)
    pdf = build_pdf(row)
    write_audit(db, row, "pdf_export_generated", "Clinical PDF export generated.")
    db.commit()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{encounter_id}-clinical-note.pdf"'
        },
    )


@router.get("/encounters/{encounter_id}/export/fhir")
def export_fhir(
    encounter_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_physician),
):
    row = _get_encounter(db, encounter_id)
    bundle = build_fhir_bundle(row, row.physician_name)
    write_audit(db, row, "fhir_export_generated", "FHIR bundle export generated.")
    db.commit()
    return bundle


@router.post("/encounters/pipeline/from-audio")
async def create_encounter_from_audio(
    file: UploadFile = File(...),
    encounter_id: str | None = Form(None),
    patient_id: str | None = Form(None),
    patient_name: str | None = Form(None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_physician),
):
    """
    Unified Pipeline Step 1 & 2:
    Takes consultation audio (from browser MediaRecorder or upload),
    sends to Transcription service (2A), forwards transcript to Clinical NLP (2B),
    persists encounter in Dashboard database (2C), and returns enriched encounter.
    """
    settings = get_settings()
    enc_id = (encounter_id or "").strip()
    if not enc_id:
        enc_id = f"ENC-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    audio_bytes = await file.read()
    files = {"file": (file.filename or "recording.wav", audio_bytes, file.content_type or "audio/wav")}
    data = {"consultation_id": enc_id}

    async with httpx.AsyncClient(timeout=180.0) as client:
        # 1. Transcription service call
        try:
            trans_resp = await client.post(
                f"{settings.transcription_url}/api/v1/live/upload-audio",
                files=files,
                data=data
            )
            if trans_resp.status_code != 200:
                trans_resp = await client.post(
                    f"{settings.transcription_url}/api/v1/transcribe",
                    files=files,
                    data={"session_id": enc_id}
                )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Transcription service unavailable at {settings.transcription_url}: {str(exc)}"
            )

        if trans_resp.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Transcription failed ({trans_resp.status_code}): {trans_resp.text}"
            )

        transcript_data = trans_resp.json()
        segments = transcript_data.get("segments", [])
        if not segments:
            raise HTTPException(status_code=422, detail="Transcription service produced no segments.")

        # 2. Clinical NLP service call
        nlp_payload = {
            "consultation_id": enc_id,
            "language": "en-US",
            "segments": segments
        }
        try:
            nlp_resp = await client.post(
                f"{settings.clinical_nlp_url}/v1/analyze",
                json=nlp_payload
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Clinical NLP service unavailable at {settings.clinical_nlp_url}: {str(exc)}"
            )

        if nlp_resp.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Clinical NLP failed ({nlp_resp.status_code}): {nlp_resp.text}"
            )

        # 3. Retrieve formatted Team C payload
        try:
            team_c_resp = await client.get(
                f"{settings.clinical_nlp_url}/v1/consultations/{enc_id}/team-c"
            )
            if team_c_resp.status_code == 200:
                payload_data = team_c_resp.json()
            else:
                payload_data = None
        except Exception:
            payload_data = None

        if not payload_data:
            # Fallback direct build if team-c get route was not available
            analysis = nlp_resp.json()
            payload_data = {
                "encounter_id": enc_id,
                "encounter_at": datetime.now(timezone.utc).isoformat(),
                "physician_id": principal.physician_id,
                "physician_name": principal.physician_name,
                "patient": {
                    "id": patient_id or f"PT-{enc_id}",
                    "name": patient_name or "Unknown Patient",
                    "age": None,
                    "sex": "unknown",
                    "allergies": [],
                    "medications": []
                },
                "transcript": {"segments": segments},
                "clinical_note": {"subjective": [], "objective": [], "assessment": [], "plan": []},
                "claims": []
            }

    # Apply any patient overrides
    if patient_id:
        payload_data.setdefault("patient", {})["id"] = patient_id
    if patient_name:
        payload_data.setdefault("patient", {})["name"] = patient_name

    try:
        parsed = TeamBPayload.model_validate(payload_data)
    except ValidationError as err:
        raise HTTPException(status_code=422, detail=f"Invalid Team B schema: {str(err)}")

    row = ingest_payload(db, parsed, principal.physician_id, principal.physician_name)
    write_audit(db, row, "pipeline_audio_ingested", f"Audio processed via unified pipeline for {enc_id}.")
    db.commit()
    return _serialize(row)


@router.post("/encounters/pipeline/from-transcript")
async def create_encounter_from_transcript(
    payload: dict,
    patient_id: str | None = None,
    patient_name: str | None = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_physician),
):
    """
    Unified Pipeline Step 2:
    Takes structured transcript JSON, executes Clinical NLP (2B),
    and creates new Encounter in Dashboard (2C).
    """
    settings = get_settings()
    enc_id = payload.get("consultation_id") or payload.get("encounter_id") or f"ENC-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    segments = payload.get("segments", [])
    if not segments:
        raise HTTPException(status_code=422, detail="Transcript must contain non-empty segments list.")

    nlp_payload = {
        "consultation_id": enc_id,
        "language": payload.get("language", "en-US"),
        "segments": segments
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            nlp_resp = await client.post(
                f"{settings.clinical_nlp_url}/v1/analyze",
                json=nlp_payload
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Clinical NLP service unreachable at {settings.clinical_nlp_url}: {str(exc)}"
            )

        if nlp_resp.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Clinical NLP analysis error ({nlp_resp.status_code}): {nlp_resp.text}"
            )

        try:
            team_c_resp = await client.get(
                f"{settings.clinical_nlp_url}/v1/consultations/{enc_id}/team-c"
            )
            payload_data = team_c_resp.json() if team_c_resp.status_code == 200 else None
        except Exception:
            payload_data = None

        if not payload_data:
            payload_data = {
                "encounter_id": enc_id,
                "encounter_at": datetime.now(timezone.utc).isoformat(),
                "physician_id": principal.physician_id,
                "physician_name": principal.physician_name,
                "patient": {
                    "id": patient_id or f"PT-{enc_id}",
                    "name": patient_name or "Unknown Patient",
                    "age": None,
                    "sex": "unknown",
                    "allergies": [],
                    "medications": []
                },
                "transcript": {"segments": segments},
                "clinical_note": {"subjective": [], "objective": [], "assessment": [], "plan": []},
                "claims": []
            }

    if patient_id:
        payload_data.setdefault("patient", {})["id"] = patient_id
    if patient_name:
        payload_data.setdefault("patient", {})["name"] = patient_name

    try:
        parsed = TeamBPayload.model_validate(payload_data)
    except ValidationError as err:
        raise HTTPException(status_code=422, detail=f"Invalid Team B schema: {str(err)}")

    row = ingest_payload(db, parsed, principal.physician_id, principal.physician_name)
    write_audit(db, row, "pipeline_transcript_ingested", f"Transcript processed via NLP pipeline for {enc_id}.")
    db.commit()
    return _serialize(row)
