# Migration from AssemblyAI → NVIDIA Local Realtime

> **TEST ONLY — PRODUCTION PIPELINE UNCHANGED**

---

## 1. Existing AssemblyAI Test Files

All under `tests/realtime_stt_eval/`:

| File | Role |
|------|------|
| `backend/app/provider.py` | `AssemblyAIRealtimeProvider` + abstract `RealtimeSTTProvider` base |
| `backend/app/session_manager.py` | `RealtimeSession`, `SessionManager` — transcript state machine |
| `backend/app/models.py` | `TranscriptSegment`, `RealtimeEvent`, `SessionMetrics`, `WordItem` |
| `backend/app/config.py` | Settings loaded from test-only `.env` |
| `backend/app/main.py` | FastAPI server port 8003, `/test/realtime/*` routes |
| `backend/requirements.txt` | Minimal test deps (fastapi, uvicorn, websockets, numpy, soundfile) |
| `frontend/index.html` | Clinical Scribe UI — Doctor/Patient bubbles, in-place updates |
| `.env` | `ASSEMBLYAI_API_KEY`, `SPEECH_MODEL`, `DOMAIN`, `SPEAKER_LABELS`, `SAMPLE_RATE`, `TEST_PORT` |
| `.env.example` | Config template |
| `recordings/clinical_test_dialogue.wav` | Synthetic test audio (tone-based) |
| `reports/ASSEMBLYAI_REALTIME_REPORT.md` | Full evaluation report |
| `run_test_server.bat` / `.ps1` | Launch scripts |
| `verify_isolation.py` | Isolation verifier |
| `tests/create_test_audio.py` | Synthetic audio generator |

---

## 2. Reusable Architecture

The following design patterns and infrastructure from the AssemblyAI POC are preserved and reused in the NVIDIA POC:

### Provider Abstraction (`RealtimeSTTProvider`)
```python
class RealtimeSTTProvider(abc.ABC):
    async def start_session(self, session_id: str) -> Dict
    async def send_audio(self, pcm_bytes: bytes) -> None
    async def receive_events(self) -> AsyncGenerator[Dict, None]
    async def stop_session(self) -> Dict
    async def close(self) -> None
```
**Reused as-is.** The NVIDIA POC implements `NVIDIARealtimeProvider(RealtimeSTTProvider)` instead of `AssemblyAIRealtimeProvider`.

### Data Models (`models.py`)
- `TranscriptSegment` — stable `segment_id`, `LIVE/STABLE/FINAL` status, `speaker_id`, `role`, `words`
- `RealtimeEvent` — typed event envelope for WebSocket streaming
- `SessionMetrics` — latency measurements
- `WordItem` — word-level attribution

**Reused without changes.**

### Session State Machine (`RealtimeSession` / `SessionManager`)
- Canonical segment store keyed by `segment_id`
- In-place partial → final state transitions
- Speaker role mapping (deterministic first-speaker-as-Doctor)
- Subscriber/event-queue broadcast pattern
- Stop/flush lifecycle

**Reused; only the provider import changes.**

### FastAPI WebSocket Routes (`main.py`)
- `POST /test/realtime/start`
- `WS /test/realtime/{id}/stream`
- `POST /test/realtime/{id}/stop`
- `GET /test/realtime/{id}/transcript`
- `POST /test/realtime/replay`

**Routes reused unchanged. The word "AssemblyAI" is removed from title/descriptions.**

### Frontend UI (`frontend/index.html`)
- Doctor/Patient bubble layout
- In-place `segment_id`-keyed DOM updates
- LIVE → FINAL transition animations
- Stop Conversation button
- Mic capture → Float32 → PCM16 conversion
- Binary WebSocket audio streaming

**Reused with only provider branding removed.**

### Recording Replay Mode
- Reads WAV at 16kHz mono
- Streams as 100ms binary frames at ~1x realtime
- Same latency measurement path as live mic

**Reused without changes.**

---

## 3. AssemblyAI-specific Files (replaced)

| File / Element | Reason for Replacement |
|----------------|------------------------|
| `backend/app/provider.py` → `AssemblyAIRealtimeProvider` | Cloud WebSocket; requires API key; replaced with `NVIDIARealtimeProvider` connecting to local NeMo-Speech.cpp |
| `.env` key `ASSEMBLYAI_API_KEY` | No API key needed for local NVIDIA inference |
| `.env` key `DOMAIN=medical-v1` | AssemblyAI-specific; replaced with NeMo model config |
| `.env` key `SPEECH_MODEL=universal-3-6-pro` | AssemblyAI model name; replaced with `nemotron-3.5` |
| `config.py` `assemblyai_api_key`, `assemblyai_ws_url` | AssemblyAI-specific fields; replaced with NVIDIA runtime URL |
| `session_manager.py` message parsing: `"Begin"`, `"Turn"`, `"SpeechStarted"`, `"Termination"` | AssemblyAI event schema; replaced with NeMo-Speech.cpp event schema |
| `backend/requirements.txt` `websockets` (outbound cloud WS) | NeMo-Speech.cpp provides its own gRPC/WS server; local only |

---

## 4. AssemblyAI-specific Dependencies

| Package | Used by | Status |
|---------|---------|--------|
| `websockets>=12.0` | `AssemblyAIRealtimeProvider` outbound WS to `wss://streaming.assemblyai.com` | **Retained** (still needed for NeMo-Speech.cpp WebSocket server communication on localhost) |
| _(no assemblyai SDK was used)_ | — | — |

No `assemblyai` Python package was ever installed in the test venv. The integration used raw WebSocket. The `websockets` library remains because the NVIDIA POC also uses WebSocket for local NeMo-Speech.cpp communication.

---

## 5. AssemblyAI-specific Environment Variables

Removed from NVIDIA `.env`:
- `ASSEMBLYAI_API_KEY`
- `SPEECH_MODEL=universal-3-6-pro`  
- `DOMAIN=medical-v1`

Replaced with:
- `NEMO_SPEECH_HOST=127.0.0.1`
- `NEMO_SPEECH_PORT=50051` (gRPC) or `8888` (WebSocket)
- `NVIDIA_ASR_MODEL=nemotron-3.5`
- `NVIDIA_DIARIZATION_MODEL=nemotron-3-diarization`
- `MAX_SPEAKERS=2`
- `FIRST_SPEAKER_ROLE=Doctor`
- `TEST_PORT=8004`

---

## 6. AssemblyAI-specific WebSocket Code

In `provider.py`, `AssemblyAIRealtimeProvider.start_session()`:
```python
url = f"wss://streaming.assemblyai.com/v3/ws?speech_model=..."
headers = {"Authorization": self.api_key}
self.ws = await websockets.connect(url, additional_headers=headers, ...)
```
This is the cloud connection. Replaced with local connection to NeMo-Speech.cpp.

In `_read_messages_loop()`, event types mapped:
- `"Begin"` → session ready
- `"Turn"` → partial/final transcript with speaker_label and words
- `"SpeechStarted"` → activity hint
- `"Termination"` → flush complete

The NVIDIA provider maps NeMo-Speech.cpp streaming events to the same internal event envelope.

---

## 7. Code That Can Be Reused

Everything except `AssemblyAIRealtimeProvider` internals:
- `RealtimeSTTProvider` ABC
- `RealtimeSession` (swap provider import only)
- `SessionManager`
- All Pydantic models
- All config fields except the 3 AssemblyAI-specific ones
- FastAPI routes
- Frontend HTML/JS/CSS
- Replay endpoint
- Logging / artifact saving
- Metrics collection

---

## 8. Code That Must Be Replaced

- `AssemblyAIRealtimeProvider` → `NVIDIARealtimeProvider`
- `.env` AssemblyAI keys → NVIDIA runtime keys
- `config.py` AssemblyAI fields → NVIDIA runtime fields
- Session manager event type parsing: `"Begin"/"Turn"/"Termination"` → NeMo event schema
- App title string: "AssemblyAI Universal-3.6 Pro" → "Clinical Scribe"

---

## 9. Frontend Components That Can Be Preserved

All of them:
- Full CSS/layout (dark theme, Doctor/Patient color scheme)
- `updateSegment()` in-place DOM update logic (keyed by `segment_id`)
- `initAudioCapture()` mic capture + PCM16 conversion
- `startSession()` / `stopSession()` lifecycle
- Only change: remove `"Universal-3.6 Pro"` badge text

---

> Architecture migration: **replace the cloud speech backend, keep everything else.**
