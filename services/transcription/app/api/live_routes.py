"""
API routes for live audio recording, real-time transcription, and speaker diarization.

PIPELINE:
  During recording  → Whisper processes every 5s chunk (<1s fast-path transcript)
                    → Pyannote diarizes chunk with context asynchronously on GPU
                    → Alignment pairs words and speaker turns without requiring pause
                    → 3-chunk window contextual refinement via Groq / local fallback
  On End click      → Flushes remaining tail, finishes in-flight jobs, outputs final transcript
  Live updates      → /live-feed returns canonical utterances with stable IDs and metrics
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import JSONResponse
import tempfile
import shutil
try:
    import sounddevice as sd
except Exception as e:
    sd = None
import soundfile as sf
import numpy as np
from datetime import datetime
import os
import json
import time
import threading
from pathlib import Path
import queue
from typing import List, Dict, Optional

from app.audio.preprocessing import AudioPreprocessor
from app.transcription.whisper_service import WhisperService, is_whisper_model_ready, get_whisper_service
from app.services.pipeline import LivePipeline


router = APIRouter()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SAMPLE_RATE   = 48000
TARGET_SR     = 16000
CHUNK_SECONDS = 5
CHANNELS      = 2

# ---------------------------------------------------------------------------
# Module-level State
# ---------------------------------------------------------------------------
_preprocessor = AudioPreprocessor()
_active_pipeline: Optional[LivePipeline] = None

recording_state = {
    "is_recording":            False,
    "session_id":              None,
    "audio_queue":             None,
    "stream":                  None,
    "all_audio_chunks":        [],       # raw mic chunks (48kHz stereo)
    "processed_audio":         None,     # full resampled audio (16kHz mono)
    "chunk_lock":              threading.Lock(),
    "total_processed_samples": 0,
}


def _process_new_audio_chunk():
    """Incrementally process only NEW audio since last chunk — send to LivePipeline."""
    global _active_pipeline
    with recording_state["chunk_lock"]:
        new_raw = []
        q = recording_state["audio_queue"]
        while q and not q.empty():
            new_raw.append(q.get_nowait())
        if not new_raw:
            return

        new_chunk_raw = np.concatenate(new_raw, axis=0)
        new_chunk_processed = _preprocessor.preprocess(new_chunk_raw, SAMPLE_RATE, fast_mode=True)

        recording_state["all_audio_chunks"].extend(new_raw)
        if recording_state["processed_audio"] is None:
            recording_state["processed_audio"] = new_chunk_processed
        else:
            recording_state["processed_audio"] = np.concatenate(
                [recording_state["processed_audio"], new_chunk_processed]
            )

        already = recording_state["total_processed_samples"]
        new_audio = recording_state["processed_audio"][already:]
        if len(new_audio) < TARGET_SR * 0.8:  # Skip if < 0.8 second
            return

        recording_state["total_processed_samples"] = len(recording_state["processed_audio"])

        # Feed to LivePipeline
        if _active_pipeline and _active_pipeline.is_active:
            _active_pipeline.feed_chunk(new_audio, is_last=False)


def _chunk_scheduler():
    while recording_state["is_recording"]:
        time.sleep(CHUNK_SECONDS)
        if recording_state["is_recording"]:
            try:
                _process_new_audio_chunk()
            except Exception as e:
                print(f"[Pipeline Scheduler] Error: {e}")


def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"[Mic] {status}")
    if recording_state["audio_queue"] is not None:
        recording_state["audio_queue"].put(indata.copy())


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@router.post("/start-recording")
async def start_recording():
    global recording_state, _active_pipeline
    if recording_state["is_recording"]:
        raise HTTPException(status_code=400, detail="Recording already in progress")

    if not is_whisper_model_ready("small.en"):
        # Warmup or check
        try:
            get_whisper_service()
        except Exception:
            pass

    if sd is None:
        raise HTTPException(
            status_code=503,
            detail="Server microphone hardware is unavailable. For browser clients, record via MediaRecorder and upload to /api/v1/live/upload-audio."
        )

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    _active_pipeline = LivePipeline(session_id=session_id)

    recording_state.update({
        "is_recording":            True,
        "session_id":              session_id,
        "audio_queue":             queue.Queue(),
        "all_audio_chunks":        [],
        "processed_audio":         None,
        "total_processed_samples": 0,
    })

    device_info = sd.query_devices(kind='input')
    print(f"[Mic] Using device: {device_info['name']}")

    recording_state["stream"] = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        callback=audio_callback,
        blocksize=1024,
    )
    recording_state["stream"].start()
    threading.Thread(target=_chunk_scheduler, daemon=True).start()

    return JSONResponse(content={
        "status":          "recording_started",
        "message":         "Live pipeline started with real-time transcription and asynchronous diarization.",
        "session_id":      session_id,
        "consultation_id": session_id,
        "device":          device_info["name"],
        "sample_rate":     SAMPLE_RATE,
    })


@router.post("/stop-recording")
async def stop_recording(background_tasks: BackgroundTasks):
    global recording_state, _active_pipeline
    if not recording_state["is_recording"]:
        raise HTTPException(status_code=400, detail="No recording in progress")

    recording_state["is_recording"] = False
    try:
        recording_state["stream"].stop()
        recording_state["stream"].close()
    except Exception as e:
        print(f"[Mic] Stream close note: {e}")

    # Synchronize remaining audio
    with recording_state["chunk_lock"]:
        remaining = []
        q = recording_state["audio_queue"]
        while q and not q.empty():
            remaining.append(q.get_nowait())
        if remaining:
            recording_state["all_audio_chunks"].extend(remaining)

        if not recording_state["all_audio_chunks"]:
            raise HTTPException(status_code=400, detail="No audio data recorded")

        full_raw = np.concatenate(recording_state["all_audio_chunks"], axis=0)

        # Preprocess remaining tail
        already_buf = recording_state.get("processed_audio")
        already_samples = recording_state["total_processed_samples"]

        if already_buf is not None and len(already_buf) > 0:
            remaining_raw = full_raw[int(already_samples * (SAMPLE_RATE / TARGET_SR)):]
            if len(remaining_raw) > 0:
                remaining_proc = _preprocessor.preprocess(remaining_raw, SAMPLE_RATE, fast_mode=True)
                full_processed = np.concatenate([already_buf, remaining_proc])
            else:
                full_processed = already_buf
        else:
            full_processed = _preprocessor.preprocess(full_raw, SAMPLE_RATE, fast_mode=True)

        recording_state["processed_audio"] = full_processed

        tail = full_processed[already_samples:]
        if len(tail) >= int(TARGET_SR * 0.3) and _active_pipeline:
            _active_pipeline.feed_chunk(tail, is_last=True)
            recording_state["total_processed_samples"] = len(full_processed)

    session_id = recording_state["session_id"]
    Path("sample_audio").mkdir(exist_ok=True)
    audio_path = Path("sample_audio") / f"live_recording_{session_id}.wav"
    sf.write(str(audio_path), full_raw, SAMPLE_RATE)

    # Gracefully stop the LivePipeline and get complete final transcript
    if _active_pipeline:
        final_result = _active_pipeline.stop()
    else:
        final_result = {}

    return JSONResponse(content={
        "status":     "recording_stopped",
        "message":    "Recording stopped and conversation finalized",
        "audio_file": str(audio_path),
        "duration":   len(full_raw) / SAMPLE_RATE,
        "transcript": final_result,
    })


@router.get("/live-feed")
async def get_live_feed():
    """
    Returns real-time session state:
    - Canonical utterances with stable utterance_ids
    - Status for each utterance: provisional (<1s), diarized, refined, or final
    - Real-time latency metrics (Whisper, Pyannote, Alignment, Groq, queue depths)
    """
    global _active_pipeline
    if _active_pipeline is not None:
        state = _active_pipeline.get_live_state()
        return JSONResponse(content={
            "is_recording":     recording_state["is_recording"],
            "session_id":       state["session_id"],
            "duration":         state["duration"],
            "total_segments":   state["total_utterances"],
            "utterances":       state["utterances"],
            # Legacy segments array for backward compatibility
            "segments": [
                {
                    "start": u["start"],
                    "end":   u["end"],
                    "text":  u["text"],
                    "speaker": u["speaker"],
                    "status":  u["status"],
                    "utterance_id": u["utterance_id"],
                    "overlap": u.get("overlap", False)
                }
                for u in state["utterances"]
            ],
            "metrics":          state["metrics"],
        })

    return JSONResponse(content={
        "is_recording":   False,
        "duration":       0.0,
        "total_segments": 0,
        "utterances":     [],
        "segments":       [],
        "metrics":        {},
    })


@router.get("/transcript/{session_id}")
async def get_transcript(session_id: str):
    p = Path("output") / f"session_{session_id}.json"
    if not p.exists():
        raise HTTPException(404, f"Session not found: {session_id}")
    with open(p, encoding="utf-8") as f:
        return JSONResponse(content=json.load(f))


@router.get("/diarization-status/{session_id}")
async def get_diarization_status(session_id: str):
    """Status endpoint for polling."""
    global _active_pipeline
    if _active_pipeline and _active_pipeline.session_id == session_id:
        if _active_pipeline.is_completed:
            status = "done"
            msg = "Diarization and conversational refinement complete"
        elif _active_pipeline.is_finalizing:
            status = "running"
            msg = "Finalizing consultation..."
        else:
            status = "running"
            msg = "Live pipeline active: transcribing and diarizing asynchronously"
    else:
        p = Path("output") / f"session_{session_id}.json"
        if p.exists():
            status = "done"
            msg = "Diarization complete"
        else:
            status = "unknown"
            msg = "Session not found"

    return JSONResponse(content={
        "session_id": session_id,
        "status":     status,
        "message":    msg,
    })


@router.get("/metrics/{session_id}")
async def get_session_metrics(session_id: str):
    """Returns detailed latency and queue metrics for the session."""
    global _active_pipeline
    if _active_pipeline and _active_pipeline.session_id == session_id:
        return JSONResponse(content={
            "session_id": session_id,
            "metrics": _active_pipeline.metrics
        })

    p = Path("output") / f"session_{session_id}.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content={
            "session_id": session_id,
            "metrics": data.get("metadata", {}).get("metrics", {})
        })

    raise HTTPException(404, f"Session {session_id} not found")


@router.post("/swap-roles/{session_id}")
async def swap_roles(session_id: str):
    global _active_pipeline
    p = Path("output") / f"session_{session_id}.json"
    if not p.exists():
        raise HTTPException(404, f"Session not found: {session_id}")

    with open(p, encoding="utf-8") as f:
        data = json.load(f)

    for seg in data.get("segments", []):
        if "role" in seg:
            r = str(seg["role"]).strip().lower()
            if r == "doctor":
                seg["role"] = "Patient"
            elif r == "patient":
                seg["role"] = "Doctor"

        spk = str(seg.get("speaker", "")).strip().upper()
        if spk == "DOCTOR":
            seg["speaker"] = "PATIENT"
        elif spk == "PATIENT":
            seg["speaker"] = "DOCTOR"

    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    if _active_pipeline and _active_pipeline.session_id == session_id:
        # Swap in active pipeline
        current_map = _active_pipeline.utterance_manager.get_role_mapping()
        new_map = {}
        for k, v in current_map.items():
            new_map[k] = "PATIENT" if v.upper() == "DOCTOR" else "DOCTOR"
        _active_pipeline.utterance_manager.set_role_mapping(new_map)

    print(f"[OK] Roles swapped: {session_id}")
    return JSONResponse(content=data)


@router.get("/recording-status")
async def get_recording_status():
    return JSONResponse(content={
        "is_recording": recording_state["is_recording"],
        "model_ready":  is_whisper_model_ready("small.en"),
    })


@router.get("/team-b/consultation/{consultation_id}")
async def get_consultation_for_team_b(consultation_id: str):
    p = Path("output") / f"session_{consultation_id}.json"
    if not p.exists():
        raise HTTPException(404, f"Consultation not found: {consultation_id}")
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(content={
        "consultation_id": data.get("consultation_id", consultation_id),
        "segments":        data["segments"],
    })
