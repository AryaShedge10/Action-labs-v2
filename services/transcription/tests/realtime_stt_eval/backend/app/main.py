"""
FastAPI Server for AssemblyAI Universal-3.6 Pro Realtime POC
tests/realtime_stt_eval/backend/app/main.py
"""

import asyncio
import io
import json
import time
import wave
from pathlib import Path
from typing import Optional
import soundfile as sf
import numpy as np

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .session_manager import session_manager, RealtimeSession
from .models import RealtimeEvent

app = FastAPI(
    title="AssemblyAI Universal-3.6 Pro Realtime POC",
    version="1.0.0",
    description="Isolated clinical speech-to-text realtime test environment"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_INDEX = settings.frontend_dir / "index.html"

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    if FRONTEND_INDEX.exists():
        return FRONTEND_INDEX.read_text(encoding="utf-8")
    return "<h1>tests/realtime_stt_eval/frontend/index.html not found</h1>"


@app.post("/test/realtime/start")
async def start_session_endpoint():
    """Initializes a new realtime streaming session."""
    session = await session_manager.create_session()
    try:
        connect_res = await session.start()
        return JSONResponse({
            "status": "ready",
            "session_id": session.session_id,
            "provider_info": connect_res
        })
    except Exception as e:
        await session_manager.remove_session(session.session_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/test/realtime/{session_id}/stream")
async def websocket_stream_endpoint(websocket: WebSocket, session_id: str):
    """
    Bidirectional WebSocket for realtime audio streaming and event delivery.
    Client sends:
      - Binary frames: PCM16 16kHz mono audio (50-100ms)
      - JSON messages: {"action": "stop"} to finalize
    Server sends:
      - JSON RealtimeEvents (segment updates, speaker revisions, status)
    """
    session = session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    event_queue = session.subscribe()

    async def client_to_server():
        try:
            while True:
                msg = await websocket.receive()
                if "bytes" in msg and msg["bytes"]:
                    await session.push_audio(msg["bytes"])
                elif "text" in msg and msg["text"]:
                    try:
                        cmd = json.loads(msg["text"])
                        if cmd.get("action") == "stop":
                            await session.stop()
                    except Exception:
                        pass
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    async def server_to_client():
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


@app.post("/test/realtime/{session_id}/stop")
async def stop_session_endpoint(session_id: str):
    """Stops the session and flushes all pending audio."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    res = await session.stop()
    return JSONResponse(res)


@app.get("/test/realtime/{session_id}/transcript")
async def get_transcript_endpoint(session_id: str):
    """Fetches the current structured transcript and metrics."""
    session = session_manager.get_session(session_id)
    if not session:
        # Check logs directory for saved session
        saved_file = settings.logs_dir / f"session_{session_id}.json"
        if saved_file.exists():
            return JSONResponse(json.loads(saved_file.read_text(encoding="utf-8")))
        raise HTTPException(status_code=404, detail="Session not found")

    return JSONResponse({
        "session_id": session.session_id,
        "status": session.status,
        "metrics": session.metrics.model_dump(),
        "segments": [s.model_dump() for s in session.segments.values()]
    })


@app.post("/test/realtime/replay")
async def replay_audio_endpoint(
    filename: Optional[str] = Query(default=None),
    upload_file: Optional[UploadFile] = File(None)
):
    """
    Mode B: Recorded Audio Replay.
    Streams audio to AssemblyAI at ~1x realtime speed in small frames (100ms)
    to measure realistic streaming performance without microphone variations.
    """
    if upload_file:
        content = await upload_file.read()
        audio_data, sr = sf.read(io.BytesIO(content), dtype="int16")
    elif filename:
        audio_path = settings.recordings_dir / filename
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail=f"File {filename} not found in recordings/")
        audio_data, sr = sf.read(str(audio_path), dtype="int16")
    else:
        # Default test recording
        audio_path = settings.recordings_dir / "clinical_test_dialogue.wav"
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Default test recording not found. Run create_test_audio.py first.")
        audio_data, sr = sf.read(str(audio_path), dtype="int16")

    # Ensure mono 16kHz
    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1).astype(np.int16)
    if sr != 16000:
        # Note: best to provide native 16kHz
        pass

    session = await session_manager.create_session()
    await session.start()

    # Stream in 100ms frames (1600 samples = 3200 bytes)
    frame_samples = 1600
    frame_bytes = frame_samples * 2
    raw_bytes = audio_data.tobytes()

    async def stream_frames():
        for i in range(0, len(raw_bytes), frame_bytes):
            chunk = raw_bytes[i:i + frame_bytes]
            await session.push_audio(chunk)
            await asyncio.sleep(0.1)  # 1x Realtime replay

        await asyncio.sleep(0.5)
        return await session.stop()

    result = await stream_frames()
    return JSONResponse({
        "status": "completed",
        "replay_result": result
    })


if __name__ == "__main__":
    import uvicorn
    print("=" * 72)
    print(f"AssemblyAI Universal-3.6 Pro Realtime Test Server")
    print(f"Listening on http://{settings.host}:{settings.port}")
    print(f"Isolated Test Environment: tests/realtime_stt_eval/")
    print(f"Production pipeline (port 8000) is UNTOUCHED.")
    print("=" * 72)
    uvicorn.run(app, host=settings.host, port=settings.port)
