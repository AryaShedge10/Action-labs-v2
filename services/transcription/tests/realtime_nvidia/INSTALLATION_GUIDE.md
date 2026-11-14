# Installation Guide — NVIDIA NeMo-Speech.cpp Local Realtime POC

> **TEST ONLY — PRODUCTION PIPELINE UNCHANGED**  
> All steps are isolated to `tests/realtime_nvidia/`

---

## Prerequisites

| Requirement | Minimum | Detected |
|-------------|---------|---------|
| GPU | NVIDIA GTX 1050 or better | GTX 1650 ✅ |
| VRAM | 4 GB | 4096 MiB ✅ |
| CUDA | 11.8+ | 13.1 ✅ |
| Driver | 520+ | 592.27 ✅ |
| Python | 3.10+ | 3.11 ✅ |
| OS | Windows 10/11 | Windows 11 ✅ |
| Disk (models) | 2 GB free | — |

---

## Step 1 — Install NeMo-Speech.cpp

NeMo-Speech.cpp is a standalone C++ binary — no Python ML packages needed.

### Option A: Pre-built Windows Binary (recommended)

1. Go to: https://github.com/NVIDIA/NeMo-Speech.cpp/releases
2. Download the latest Windows release (look for `nemo-speech-windows-cuda.zip` or similar)
3. Extract to a folder, e.g. `C:\tools\nemo-speech\`
4. Add that folder to your PATH:
   ```
   setx PATH "%PATH%;C:\tools\nemo-speech"
   ```
5. Verify:
   ```bat
   nemo-speech --version
   ```

### Option B: NGC Container (requires Docker with NVIDIA runtime)

```bat
docker pull nvcr.io/nvidia/nemo-speech.cpp:0.1.0
```

For Windows without Docker, use Option A.

---

## Step 2 — Pull NVIDIA Models (one-time download)

Models are stored in `tests/realtime_nvidia/models/` — NOT in the global HF cache.

```bat
cd a:\VIT-3rd-sem\3rd_sem\EDI_Accion_lab\tests\realtime_nvidia

set NEMO_SPEECH_MODEL_DIR=%CD%\models

nemo-speech --model-dir models pull nemotron-3.5
nemo-speech --model-dir models pull nemotron-3-diarization
```

Expected download sizes:
- `nemotron-3.5`: ~1.2 GB
- `nemotron-3-diarization`: ~0.5 GB

After download, confirm offline operation works (Phase 44):
```bat
REM Disconnect internet, then:
nemo-speech --model-dir models serve --model nemotron-3.5 --ws-port 8888
```
It should start without any network calls.

---

## Step 3 — Create Test Python Environment

```bat
cd a:\VIT-3rd-sem\3rd_sem\EDI_Accion_lab\tests\realtime_nvidia

REM Create isolated venv (NOT the production venv)
python -m venv .venv

REM Install test dependencies
.venv\Scripts\pip install -r backend\requirements.txt
```

Verify isolation:
```bat
.venv\Scripts\python -c "import sys; print(sys.prefix)"
REM Should show: ...tests\realtime_nvidia\.venv
```

---

## Step 4 — Configure Environment

```bat
copy .env.example .env
```

The defaults in `.env` are correct for a first run. No API keys needed.

---

## Step 5 — Run the NVIDIA Runtime Server

Open **Terminal 1**:
```bat
cd a:\VIT-3rd-sem\3rd_sem\EDI_Accion_lab\tests\realtime_nvidia
run_nemo_server.bat
```

Wait for: `NeMo-Speech.cpp server ready on ws://127.0.0.1:8888`

---

## Step 6 — Run the Test Backend

Open **Terminal 2**:
```bat
cd a:\VIT-3rd-sem\3rd_sem\EDI_Accion_lab\tests\realtime_nvidia
run_test_backend.bat
```

Wait for: `Uvicorn running on http://127.0.0.1:8004`

---

## Step 7 — Open the UI

Navigate to: **http://127.0.0.1:8004**

Click **Start Conversation** and speak in a Doctor/Patient pattern.

---

## Step 8 — Generate Test Recordings

```bat
cd a:\VIT-3rd-sem\3rd_sem\EDI_Accion_lab\tests\realtime_nvidia
.venv\Scripts\python scripts\create_test_audio.py
```

Test replay (Mode B):
```bat
curl -X POST "http://127.0.0.1:8004/test/realtime/replay?filename=clinical_test_dialogue.wav"
```

---

## Step 9 — Run Latency Benchmarks (Phase 37/38)

```bat
REM 60-second test
.venv\Scripts\python scripts\benchmark_latency.py --duration 60

REM 5-minute sustained test
.venv\Scripts\python scripts\benchmark_latency.py --duration 300

REM 20-minute sustained test
.venv\Scripts\python scripts\benchmark_latency.py --duration 1200
```

Reports saved to `reports/`.

---

## Step 10 — Verify Isolation

```bat
.venv\Scripts\python verify_isolation.py
```

Expected: all checks pass. Production is untouched.

---

## Simulation Mode (No GPU Required)

To test the UI/state machine without the NVIDIA runtime:

```bat
REM Start backend only (no nemo-speech needed):
run_test_backend.bat

REM Then open: http://127.0.0.1:8004
REM Click Start Conversation — will use ?simulation=true automatically on backend error,
REM OR call directly:
curl -X POST "http://127.0.0.1:8004/test/realtime/start?simulation=true"
```

Simulation emits realistic Doctor/Patient events at human speech timing.  
Used for: UI testing, state machine testing, frontend development.

---

## GTX 1650 Optimization Notes (Phase 40)

Start with defaults, then optimize in order:
1. Verify `ASR_LATENCY_MODE=low_latency` in `.env`
2. Run baseline benchmark
3. Try `very_low_latency` — benchmark
4. Try `ultra_low_latency` — benchmark (may exceed compute budget)
5. Select the lowest latency mode that keeps RTF ≤ 1.0

Do NOT change the latency mode without benchmarking first.  
Do NOT add rolling-window batch inference to compensate for GPU limitations.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `nemo-speech: command not found` | Binary not in PATH | Add NeMo-Speech.cpp bin dir to PATH |
| `Cannot connect to NeMo-Speech.cpp` | Runtime not started | Run `run_nemo_server.bat` first |
| `Session not found` | Backend restarted mid-session | Start a new session |
| VRAM OOM error | Both models exceed 4GB | Try Q8 model: `nemo-speech pull nemotron-3.5-q8` |
| Blank transcript | Tone audio fed (not speech) | Use real microphone or real speech WAV |
| Speaker always "Doctor" | Diarization not enabled | Check `DIARIZATION_ENABLED=true` in `.env` |

---

## What NOT to Do

- Do NOT run `pip install` into the production `venv/`
- Do NOT run `pip install` globally
- Do NOT modify `app/`, `static/`, `requirements.txt`, or `.env` at the project root
- Do NOT change production port 8000
- Do NOT copy models into the global HF cache (`~/.cache/huggingface/`)
