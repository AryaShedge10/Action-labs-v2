from pathlib import Path

enc_path = Path("clinical-scribe-unified/backend/dashboard/app/api/encounters.py")
content = enc_path.read_text(encoding="utf-8")

# 1. Update imports
if "UploadFile, File, Form" not in content:
    content = content.replace(
        "from fastapi import APIRouter, Depends, HTTPException",
        "from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form\nimport httpx\nfrom datetime import datetime, timezone"
    )

pipeline_code = '''

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
'''

if "/encounters/pipeline/from-audio" not in content:
    content += pipeline_code

enc_path.write_text(content, encoding="utf-8")
print("encounters.py successfully updated with pipeline coordinator endpoints.")

