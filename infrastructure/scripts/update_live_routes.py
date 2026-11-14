import sys
from pathlib import Path

path = Path("clinical-scribe-unified/services/transcription/app/api/live_routes.py")
content = path.read_text(encoding="utf-8")

# 1. Update imports
if "UploadFile, File, Form" not in content:
    content = content.replace(
        "from fastapi import APIRouter, HTTPException, BackgroundTasks\nfrom fastapi.responses import JSONResponse",
        "from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form\nfrom fastapi.responses import JSONResponse\nimport tempfile\nimport shutil"
    )

# 2. Add microphone guard in start_recording
old_start = """    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    _active_pipeline = LivePipeline(session_id=session_id)"""

new_start = """    if sd is None:
        raise HTTPException(
            status_code=503,
            detail="Server microphone hardware is unavailable. For browser clients, record via MediaRecorder and upload to /api/v1/live/upload-audio."
        )

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    _active_pipeline = LivePipeline(session_id=session_id)"""

if old_start in content:
    content = content.replace(old_start, new_start)

# 3. Add upload_audio_for_session at the bottom
upload_code = '''


@router.post("/upload-audio")
async def upload_audio_for_session(
    file: UploadFile = File(...),
    consultation_id: Optional[str] = Form(None),
    model: Optional[str] = Form("base.en")
):
    """
    Browser audio capture endpoint.
    Accepts consultation audio recorded via client-side MediaRecorder (WAV, WebM, MP3, M4A, OGG),
    transcribes with Faster-Whisper, detects DOCTOR/PATIENT roles via heuristics,
    and saves output to output/session_{consultation_id}.json for Team B and Team C.
    """
    from app.audio.audio_loader import AudioLoader
    from app.audio.preprocessing import AudioPreprocessor
    from app.transcription.transcript_formatter import TranscriptFormatter
    from app.services.roles import detect_speaker_roles

    cid = (consultation_id or "").strip()
    if not cid:
        cid = datetime.now().strftime("%Y%m%d_%H%M%S")

    temp_dir = tempfile.mkdtemp()
    try:
        temp_input = Path(temp_dir) / (file.filename or "recording.wav")
        with open(temp_input, "wb") as f:
            shutil.copyfileobj(file.file, f)

        loader = AudioLoader()
        preprocessor = AudioPreprocessor()
        audio_data, sr = loader.load(str(temp_input))
        proc_audio = preprocessor.preprocess(audio_data, sr)

        temp_proc = Path(temp_dir) / "processed.wav"
        loader.save(proc_audio, str(temp_proc), preprocessor.target_sample_rate)

        whisper = get_whisper_service(model_name=model)
        raw_segments = whisper.transcribe(str(temp_proc))

        merged_for_roles = [
            {"speaker": f"SPEAKER_{i%2:02d}", "text": s.get("text", "")}
            for i, s in enumerate(raw_segments)
        ]
        spk_to_role = detect_speaker_roles(merged_for_roles)

        speaker_labels = {}
        for i, s in enumerate(raw_segments):
            pseudo_spk = f"SPEAKER_{i%2:02d}"
            role = spk_to_role.get(pseudo_spk, "Doctor" if i % 2 == 0 else "Patient")
            speaker_labels[i] = role.upper()

        formatter = TranscriptFormatter()
        transcript = formatter.format(
            segments=raw_segments,
            session_id=cid,
            speaker_labels=speaker_labels
        )
        saved_path = formatter.save(transcript)
        transcript["saved_to"] = saved_path

        return JSONResponse(content=transcript)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio transcription failed: {str(e)}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
'''

if "/upload-audio" not in content:
    content += upload_code

path.write_text(content, encoding="utf-8")
print("live_routes.py successfully patched.")

