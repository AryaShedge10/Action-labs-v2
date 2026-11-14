"""
FastAPI Server — NVIDIA NeMo-Speech.cpp Local Realtime POC
tests/realtime_nvidia/backend/app/main.py

Runs on port 8004 (different from production 8000 and AssemblyAI test 8003).
ZERO imports from production app/.
ZERO cloud connectivity.
ZERO API keys required.

Phase 15 Architecture:
  Browser mic (PCM16 16kHz mono)
      ↓ binary WebSocket frames
  This server (port 8004)
      ↓ local WebSocket
  NeMo-Speech.cpp (port 8888/50051)
      ↓ Nemotron-3.5 ASR + Nemotron-3-Diarization
      ↓ streaming events
  This server — transcript state machine
      ↓ RealtimeEvent JSON
  Browser — in-place Doctor/Patient transcript UI
"""

import asyncio
import io
import json
import os
import time
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .session_manager import session_manager, RealtimeSession
from .models import RealtimeEvent


app = FastAPI(
    title="Clinical Scribe — Local Realtime",
    version="1.0.0",
    description=(
        "Isolated NVIDIA NeMo-Speech.cpp realtime test environment. "
        "No cloud. No API keys. All inference local."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_INDEX = settings.frontend_dir / "index.html"


# ============================================================
# UI
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    if FRONTEND_INDEX.exists():
        return FRONTEND_INDEX.read_text(encoding="utf-8")
    return (
        "<h1>tests/realtime_nvidia/frontend/index.html not found</h1>"
        "<p>Run <code>run_nemo_server.bat</code> to start the NVIDIA runtime first.</p>"
    )


# ============================================================
# Session Lifecycle
# ============================================================

@app.post("/test/realtime/start")
async def start_session_endpoint(simulation: bool = Query(default=False)):
    """
    Initialize a new realtime streaming session.
    If NeMo-Speech.cpp is not running, set ?simulation=true for UI testing.
    """
    session = await session_manager.create_session(use_simulation=simulation)
    try:
        connect_res = await session.start()
        return JSONResponse({
            "status": "ready",
            "session_id": session.session_id,
            "provider_info": connect_res,
        })
    except ConnectionError as e:
        await session_manager.remove_session(session.session_id)
        raise HTTPException(
            status_code=503,
            detail=(
                str(e) + "\n\nTip: Start NVIDIA runtime first:\n"
                "  cd tests\\realtime_nvidia && run_nemo_server.bat\n"
                "Or use simulation mode: POST /test/realtime/start?simulation=true"
            ),
        )
    except Exception as e:
        await session_manager.remove_session(session.session_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test/realtime/{session_id}/stop")
async def stop_session_endpoint(session_id: str):
    """Stop session and flush all pending audio (Phase 34)."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    res = await session.stop()
    return JSONResponse(res)


@app.get("/test/realtime/{session_id}/transcript")
async def get_transcript_endpoint(session_id: str):
    """Fetch current structured transcript and metrics."""
    session = session_manager.get_session(session_id)
    if session:
        return JSONResponse({
            "session_id": session.session_id,
            "status": session.status,
            "metrics": session.metrics.model_dump(),
            "segments": [s.model_dump() for s in session.segments.values()],
        })
    # Check saved logs
    saved = settings.logs_dir / f"session_{session_id}.json"
    if saved.exists():
        return JSONResponse(json.loads(saved.read_text(encoding="utf-8")))
    raise HTTPException(status_code=404, detail="Session not found")


# ============================================================
# Bidirectional WebSocket Endpoint (Phase 15)
# ============================================================

@app.websocket("/test/realtime/{session_id}/stream")
async def websocket_stream_endpoint(websocket: WebSocket, session_id: str):
    """
    Bidirectional WebSocket for realtime audio streaming and event delivery.

    Client → Server:
      - Binary frames: PCM16 16kHz mono audio (100ms per frame)
      - JSON: {"action": "stop"} to initiate graceful shutdown

    Server → Client:
      - JSON RealtimeEvent objects:
          segment_update    — LIVE or FINAL transcript segment
          speaker_revision  — speaker identity update
          session_status    — "ready" / "error"
          final_summary     — all segments + metrics on stop
          error             — runtime or connection error
    """
    session = session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    event_queue = session.subscribe()

    async def client_to_server():
        """Receive audio frames and control messages from browser."""
        try:
            while True:
                msg = await websocket.receive()
                if "bytes" in msg and msg["bytes"]:
                    # Binary PCM16 frame — forward to NeMo-Speech.cpp
                    await session.push_audio(msg["bytes"])
                elif "text" in msg and msg["text"]:
                    try:
                        cmd = json.loads(msg["text"])
                        if cmd.get("action") == "stop":
                            # Phase 34: initiate graceful flush
                            await session.stop()
                    except Exception:
                        pass
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    async def server_to_client():
        """Send transcript events to browser."""
        try:
            while True:
                event: RealtimeEvent = await event_queue.get()
                await websocket.send_text(event.model_dump_json())
                if event.type == "final_summary":
                    break
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    try:
        await asyncio.gather(client_to_server(), server_to_client())
    finally:
        session.unsubscribe(event_queue)


# ============================================================
# Recorded Audio Replay (Phase 35)
# ============================================================

@app.post("/test/realtime/replay")
async def replay_audio_endpoint(
    filename: Optional[str] = Query(default=None),
    upload_file: Optional[UploadFile] = File(None),
    simulation: bool = Query(default=False),
):
    """
    Mode B: Recorded Audio Replay (Phase 35).
    Streams audio through the same REALTIME path as live mic — NOT batch transcription.
    Enables reproducible comparison testing.

    Audio → realtime frames (100ms) → NeMo-Speech.cpp → transcript events
    """
    # Load audio
    if upload_file:
        content = await upload_file.read()
        audio_data, sr = sf.read(io.BytesIO(content), dtype="int16")
    elif filename:
        audio_path = settings.recordings_dir / filename
        if not audio_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"File {filename} not found in recordings/"
            )
        audio_data, sr = sf.read(str(audio_path), dtype="int16")
    else:
        default_audio = settings.recordings_dir / "clinical_test_dialogue.wav"
        if not default_audio.exists():
            raise HTTPException(
                status_code=404,
                detail=(
                    "Default test recording not found. "
                    "Run: python tests/realtime_nvidia/scripts/create_test_audio.py"
                ),
            )
        audio_data, sr = sf.read(str(default_audio), dtype="int16")

    # Ensure mono 16kHz int16
    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1).astype(np.int16)
    if sr != 16000:
        # Note: provide audio at native 16kHz for best quality
        pass

    session = await session_manager.create_session(use_simulation=simulation)
    connect_res = await session.start()

    # Stream in 100ms frames at ~1x realtime speed (Phase 35)
    frame_samples = 1600  # 100ms at 16kHz
    frame_bytes_size = frame_samples * 2  # 16-bit = 2 bytes/sample
    raw_bytes = audio_data.tobytes()

    t_start = time.time()
    frames_sent = 0
    for i in range(0, len(raw_bytes), frame_bytes_size):
        chunk = raw_bytes[i: i + frame_bytes_size]
        await session.push_audio(chunk)
        frames_sent += 1
        # Sleep 100ms to maintain ~1x realtime playback
        await asyncio.sleep(0.1)

    # Give NeMo-Speech.cpp time to process remaining audio
    await asyncio.sleep(0.5)

    result = await session.stop()
    elapsed = time.time() - t_start

    return JSONResponse({
        "status": "completed",
        "replay_duration_s": round(elapsed, 2),
        "audio_samples": len(audio_data),
        "frames_sent": frames_sent,
        "provider_info": connect_res,
        "result": result,
    })


# ============================================================
# Status & Health
# ============================================================

@app.get("/test/status")
async def get_status():
    """Server status including NeMo runtime connectivity."""
    nemo_url = (
        f"ws://{settings.nemo_speech_host}:{settings.nemo_speech_ws_port}/stream"
    )
    nemo_reachable = False
    try:
        import websockets as _ws
        async with _ws.connect(nemo_url, open_timeout=2) as probe:
            nemo_reachable = True
    except Exception:
        pass

    return JSONResponse({
        "server": "nvidia_nemo_realtime_test",
        "port": settings.port,
        "nemo_speech_url": nemo_url,
        "nemo_reachable": nemo_reachable,
        "asr_model": settings.nvidia_asr_model,
        "diarization_model": settings.nvidia_diarization_model,
        "latency_mode": settings.asr_latency_mode,
        "max_speakers": settings.max_speakers,
        "active_sessions": len(session_manager.sessions),
        "production_untouched": True,
        "cloud_dependency": False,
        "api_key_required": False,
    })


@app.get("/test/recordings")
async def list_recordings():
    """List available test recordings."""
    recordings = []
    for f in settings.recordings_dir.iterdir():
        if f.suffix.lower() in (".wav", ".mp3", ".flac"):
            recordings.append({
                "name": f.name,
                "size_kb": round(f.stat().st_size / 1024, 1),
            })
    return JSONResponse({"recordings": recordings})


if __name__ == "__main__":
    import uvicorn
    print("=" * 72)
    print("NVIDIA NeMo-Speech.cpp Realtime Test Server")
    print(f"  Port:         http://{settings.host}:{settings.port}")
    print(f"  ASR Model:    {settings.nvidia_asr_model}")
    print(f"  Diarization:  {settings.nvidia_diarization_model}")
    print(f"  Latency Mode: {settings.asr_latency_mode}")
    print(f"  NeMo Runtime: ws://{settings.nemo_speech_host}:{settings.nemo_speech_ws_port}/stream")
    print(f"  Isolation:    tests/realtime_nvidia/ (production UNTOUCHED)")
    print(f"  Cloud:        NONE — all inference local")
    print(f"  API Key:      NOT REQUIRED")
    print("=" * 72)
    print()
    print("NOTE: Start NVIDIA runtime first:")
    print("  run_nemo_server.bat")
    print()
    uvicorn.run(app, host=settings.host, port=settings.port)
