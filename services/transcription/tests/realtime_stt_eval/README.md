# AssemblyAI Universal-3.6 Pro Realtime — Test Environment

## Overview
An isolated, self-contained proof-of-concept for evaluating **AssemblyAI Universal-3.6 Pro Realtime** streaming transcription in a clinical doctor/patient context.

> **TEST ONLY — PRODUCTION UNCHANGED**

---

## Architecture

```
Browser Microphone
       ↓  PCM16 mono 16kHz (100ms binary WebSocket frames)
Test Backend — FastAPI on port 8003 (tests/realtime_stt_eval/.venv)
       ↓  AssemblyAI WebSocket (wss://streaming.assemblyai.com/v3/ws)
AssemblyAI Universal-3.6 Pro Realtime
       ↓  JSON event stream (Turn, Begin, Termination)
Test Backend — Transcript State Machine
       ↓  RealtimeEvent JSON (segment_update, final_summary)
Browser — Live clinical transcript UI (Doctor / Patient bubbles, in-place updates)
```

---

## Quick Start

### 1. Configure API Key
```bash
# Edit the test-only .env file
notepad tests\realtime_stt_eval\.env
```
Set `ASSEMBLYAI_API_KEY=your_actual_api_key_here`

### 2. Run the Test Server
```cmd
cd tests\realtime_stt_eval
run_test_server.bat
```
or in PowerShell:
```powershell
cd tests\realtime_stt_eval
.\run_test_server.ps1
```

### 3. Open the UI
Navigate to: **http://127.0.0.1:8003**

Click **Start Conversation** and speak. Live transcription with Doctor / Patient attribution.

### 4. Mode B — Recorded Replay
```bash
# Generate test audio
.venv\Scripts\python.exe tests\create_test_audio.py

# Replay via API
curl -X POST http://127.0.0.1:8003/test/realtime/replay?filename=clinical_test_dialogue.wav
```

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `ASSEMBLYAI_API_KEY` | _(required)_ | Your AssemblyAI API key |
| `SPEECH_MODEL` | `universal-3-6-pro` | AssemblyAI speech model |
| `DOMAIN` | `medical-v1` | Medical domain optimization |
| `SPEAKER_LABELS` | `true` | Enable real-time speaker diarization |
| `SAMPLE_RATE` | `16000` | Audio sample rate (Hz) |
| `TEST_PORT` | `8003` | Backend HTTP port |

---

## Directory Structure

```
tests/realtime_stt_eval/
├── .venv/                    ← Isolated Python 3.11 virtualenv (NOT production venv)
├── .env                      ← Local API key (git-ignored)
├── .env.example              ← Configuration template
├── backend/
│   ├── requirements.txt      ← Test-only Python dependencies
│   └── app/
│       ├── config.py         ← Settings loaded from test .env only
│       ├── models.py         ← Pydantic data models (segments, events, metrics)
│       ├── provider.py       ← AssemblyAI v3 WebSocket client + abstract interface
│       ├── session_manager.py← Transcript state machine & session lifecycle
│       └── main.py           ← FastAPI server (port 8003)
├── frontend/
│   └── index.html            ← Clinical Scribe UI (Doctor/Patient bubbles, live updates)
├── tests/
│   └── create_test_audio.py  ← Generates synthetic clinical dialogue WAV
├── recordings/               ← Test audio files
├── logs/                     ← Per-session JSON + TXT transcripts
├── reports/                  ← Evaluation reports
├── run_test_server.bat        ← Launch (CMD)
├── run_test_server.ps1        ← Launch (PowerShell)
├── verify_isolation.py        ← Verifies test env is isolated from production
├── CLEANUP_BEFORE.md          ← Phase 0 inventory
└── CLEANUP_AFTER.md           ← Phase 1 cleanup report
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Test UI (Clinical Scribe) |
| `POST` | `/test/realtime/start` | Start new streaming session |
| `WS` | `/test/realtime/{id}/stream` | Bidirectional audio/events WebSocket |
| `POST` | `/test/realtime/{id}/stop` | Stop and flush session |
| `GET` | `/test/realtime/{id}/transcript` | Fetch current transcript |
| `POST` | `/test/realtime/replay` | Mode B: file replay |

---

## Safety Guarantees

- Production virtual environment (`venv/`) is **never touched**
- Production backend (`app/`) is **never imported**  
- Production `.env` is **never read** by the test backend
- AssemblyAI API key is **only in test .env** and never exposed to the browser
- `verify_isolation.py` fails loudly if any isolation is broken
- No global pip installs were performed
