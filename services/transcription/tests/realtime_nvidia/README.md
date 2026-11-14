# NVIDIA NeMo-Speech.cpp Local Realtime POC

> **TEST ONLY — PRODUCTION PIPELINE UNCHANGED**  
> No cloud. No API keys. All inference local on GTX 1650.

---

## Overview

This is an isolated proof-of-concept converting the previous AssemblyAI streaming test
into a fully local NVIDIA implementation using:

- **ASR**: `nvidia/nemotron-3.5-asr-streaming-0.6b` (cache-aware FastConformer-RNNT)
- **Diarization**: `nvidia/Nemotron-3-Diarization` (Streaming Sortformer)
- **Runtime**: NVIDIA NeMo-Speech.cpp v0.1.0

The session architecture, transcript state machine, frontend UI, and all reusable
infrastructure are preserved from the AssemblyAI POC. Only the speech provider is replaced.

---

## Architecture

```
Browser Microphone
    ↓  PCM16 16kHz mono (100ms binary WebSocket frames)
Test Backend — FastAPI port 8004 (tests/realtime_nvidia/.venv)
    ↓  local WebSocket ws://127.0.0.1:8888/stream
NeMo-Speech.cpp server — GTX 1650 CUDA 13.1
    ↓  Nemotron-3.5 ASR (cache-aware streaming)
    ↓  Nemotron-3-Diarization (Streaming Sortformer, Arrival-Order cache)
    ↓  events: partial / final / diarization
Test Backend — RealtimeSession transcript state machine
    ↓  RealtimeEvent JSON: segment_update / speaker_revision / final_summary
Browser — Clinical Scribe UI (Doctor/Patient bubbles, in-place updates)
```

---

## Quick Start

### Prerequisites
- NVIDIA GTX 1650 with CUDA 13.1 driver (592.27)
- Python 3.11
- NeMo-Speech.cpp binary in PATH (see INSTALLATION_GUIDE.md)

### First Time
```bat
cd tests\realtime_nvidia

REM Pull models (~1.7 GB, stored locally)
nemo-speech --model-dir models pull nemotron-3.5
nemo-speech --model-dir models pull nemotron-3-diarization

REM Create isolated Python env
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt
```

### Every Run

**Terminal 1 — NVIDIA Runtime:**
```bat
cd tests\realtime_nvidia
run_nemo_server.bat
```

**Terminal 2 — Test Backend:**
```bat
cd tests\realtime_nvidia
run_test_backend.bat
```

**Browser:** http://127.0.0.1:8004

---

## Simulation Mode (No GPU Required)

Test the UI and state machine without NeMo-Speech.cpp:
```bat
run_test_backend.bat
REM Then POST /test/realtime/start?simulation=true from the UI on backend error
```

---

## Directory Structure

```
tests/realtime_nvidia/
├── .venv/                       ← Isolated Python venv (NOT production venv)
├── .env                         ← Local config (no API keys)
├── .env.example                 ← Template
├── backend/
│   ├── requirements.txt         ← Minimal: fastapi, uvicorn, websockets, numpy
│   └── app/
│       ├── config.py            ← NVIDIA runtime settings (reads test .env only)
│       ├── models.py            ← TranscriptSegment, RealtimeEvent, SessionMetrics
│       ├── provider.py          ← NVIDIARealtimeProvider + OfflineSimulationProvider
│       ├── session_manager.py   ← Transcript state machine (LIVE→FINAL)
│       └── main.py              ← FastAPI server port 8004
├── frontend/
│   └── index.html               ← Clinical Scribe UI (Doctor/Patient, in-place updates)
├── models/                      ← NVIDIA model storage (populated by nemo-speech pull)
├── model_cache/                 ← NeMo-Speech.cpp runtime cache
├── recordings/                  ← Test audio files
├── logs/                        ← Per-session JSON + TXT transcripts
├── reports/
│   ├── NVIDIA_RUNTIME_VERSION.md
│   └── NVIDIA_REALTIME_REPORT.md
├── scripts/
│   ├── create_test_audio.py     ← Generates synthetic test WAVs
│   └── benchmark_latency.py    ← Latency/sustained/GPU benchmark
├── run_nemo_server.bat          ← Start NVIDIA runtime
├── run_test_backend.bat         ← Start FastAPI backend
├── run_test_backend.ps1         ← PowerShell alternative
├── verify_isolation.py          ← Confirms test env isolated from production
├── README.md                    ← This file
├── INSTALLATION_GUIDE.md
├── MIGRATION_FROM_ASSEMBLYAI.md
├── MOSS_REMAINING_ARTIFACTS.md  ← MOSS confirmed absent
├── ASSEMBLYAI_CLEANUP_REPORT.md ← AssemblyAI provider removed
├── ISOLATION_REPORT.md          ← Phase 50 isolation confirmation
└── DISK_USAGE_REPORT.md         ← Phase 49 disk usage
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Clinical Scribe UI |
| `POST` | `/test/realtime/start` | Initialize session (add `?simulation=true` for offline mode) |
| `WS` | `/test/realtime/{id}/stream` | Bidirectional audio/events WebSocket |
| `POST` | `/test/realtime/{id}/stop` | Stop and flush session (Phase 34) |
| `GET` | `/test/realtime/{id}/transcript` | Fetch current transcript |
| `POST` | `/test/realtime/replay` | Mode B: recorded audio replay |
| `GET` | `/test/status` | Runtime health check |
| `GET` | `/test/recordings` | List available test recordings |

---

## Safety Guarantees

- Production virtual environment `venv/` is **never touched**
- Production backend `app/` is **never imported** by any test file
- Production `.env` is **never read** by the test backend
- Test `.env` contains **zero API keys**
- NeMo-Speech.cpp models stored in **`tests/realtime_nvidia/models/`** — not global cache
- `verify_isolation.py` fails loudly if any boundary is broken
- No global pip installs
- Port 8000 (production) remains unchanged

---

## Key Design Decisions

**Why NeMo-Speech.cpp over Python NeMo?**  
The native C++ runtime loads models once at server startup and serves all sessions.  
No per-request model load. No Python inference overhead. CPU fallback supported.

**Why cache-aware streaming (Phase 10)?**  
Nemotron-3.5 maintains ASR state across frames — previous context informs the next.  
This eliminates the 20-second rolling window latency problem that MOSS had.

**Why Arrival-Order Speaker Cache (Phase 23)?**  
Speaker identities persist for the entire session. The diarizer does not reassign  
`speaker_0` and `speaker_1` per chunk — solving the MOSS speaker-swap failure.

**Why 100ms audio frames (Phase 14)?**  
Continuous streaming. No 5/10/20-second WAV accumulation before transcription starts.

---

## Comparison: MOSS vs. AssemblyAI vs. NVIDIA

| Issue | MOSS | AssemblyAI | NVIDIA NeMo (this POC) |
|-------|------|-----------|------------------------|
| First text latency | 30s+ | < 1s | < 1s (target) |
| Speaker swap | Random | Session-stable | Session-stable (Arrival-Order) |
| Cloud dependency | No | Yes (API key) | No |
| Disk usage | 23.8 GB | ~28 MB | ~1.75 GB |
| Rolling windows | 20s | None | None (cache-aware) |
| Offline capable | Yes (broken) | No | Yes |

---

> **TEST ONLY — PRODUCTION PIPELINE (Whisper + Pyannote + Groq) UNCHANGED**
