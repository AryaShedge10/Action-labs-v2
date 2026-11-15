# Unified AI-Powered Clinical Scribe Platform

> **Clinical Documentation Assistance Platform**  
> Speech-to-Text · Diarization · Clinical NLP · Safety & Grounding · Physician Review · FHIR/PDF Export

---

## 1. Project Overview

The **Unified Clinical Scribe Platform** consolidates transcription, clinical natural language processing, safety rule verification, and physician review into a single, cohesive clinical documentation workflow.

```
+-------------------------------------------------------------------------------------------------------+
|                                    Physician Review Workflow                                          |
|                                                                                                       |
| [1. Record / Capture] -> [2. Transcribe & Diarize] -> [3. NLP & Safety Check] -> [4. Physician Gate]  |
| Browser MediaRecorder    Faster-Whisper + Pyannote    Extract Entities, Rules    Edit, Audit, Sign    |
|                          Doctor / Patient roles       Grounding, Citations       Block if Conflict    |
+-------------------------------------------------------------------------------------------------------+
                                                       |
                                           [5. Export & Integration]
                                           FHIR R4 Bundle · PDF · Mock EHR
```

### Core Architecture & Service Responsibilities
1. **Frontend (`frontend/`):** React 18, TypeScript, Tailwind CSS, TanStack Query, Framer Motion. Captures live audio directly via HTML5 `MediaRecorder` or accepts audio uploads; displays real-time transcripts, SOAP notes, grounding evidence, and safety warnings.
2. **Transcription Service (`services/transcription/`):** FastAPI, Faster-Whisper, Pyannote.Audio. On-device acoustic processing, speaker diarization, and content-based lexical role detection (`Doctor` vs `Patient`).
3. **Clinical NLP & Safety Service (`services/clinical_nlp/`):** FastAPI, Pydantic v2. Rule-based & hybrid entity extraction, negation and historical context classification, deterministic allergy/medication safety checks, claim-level grounding verification, and draft SOAP note generation.
4. **Dashboard & Encounter Backend (`backend/dashboard/`):** FastAPI, SQLAlchemy 2.0, PostgreSQL 16. Source of truth for encounter lifecycle, HMAC-SHA256 JWT authentication, immutable audit logging, four-step physician finalization gate, ReportLab PDF export, and FHIR R4 Bundle generation.
5. **Mock EHR Adapter (`mock_ehr/`):** Standalone OpenEMR-style receiver storing physician-finalized FHIR Bundles.

---

## 2. Directory Structure

```
clinical-scribe-unified/
├── frontend/                     # React 18 / TypeScript / Vite UI
├── backend/
│   └── dashboard/                # Encounter API, ORM, PDF/FHIR services
├── services/
│   ├── transcription/            # Faster-Whisper, Pyannote diarization, roles
│   └── clinical_nlp/             # Clinical NLP extraction, safety, grounding
├── mock_ehr/                     # Standalone FHIR mock EHR adapter
├── shared/
│   └── contracts/                # Pydantic contracts (Transcript, Analysis, Encounter)
├── data/
│   ├── samples/                  # Synthetic clinical encounter test fixtures
│   └── evaluation/               # Evaluation datasets and acoustic benchmarks
├── docs/                         # Audit reports, file mappings, API specs
├── infrastructure/
│   └── docker/                   # Dockerfiles, Nginx proxy, and DB init SQL
├── tests/
│   ├── contract/                 # Schema & timestamp compatibility tests
│   ├── unit/                     # Audio, safety, grounding, and auth unit tests
│   └── end_to_end/               # 3 synthetic clinical consultation scenarios
├── docker-compose.yml            # Root multi-container orchestration
├── .env.example                  # Environment configuration template
├── .gitignore
└── README.md
```

---

## 3. Quickstart with Docker Compose (Recommended)

Start the entire system with a single command:

```bash
# 1. Clone the repository and navigate into the project
cd clinical-scribe-unified

# 2. Copy the environment configuration
cp .env.example .env

# 3. Build and launch all services
docker compose up --build -d
```

### Service Access Endpoints:
- **Web Dashboard:** [http://localhost:8080](http://localhost:8080)
- **Dashboard API Docs:** [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- **Transcription Service Docs:** [http://localhost:8003/docs](http://localhost:8003/docs)
- **Clinical NLP Service Docs:** [http://localhost:8002/docs](http://localhost:8002/docs)
- **Mock EHR Adapter Docs:** [http://localhost:8001/docs](http://localhost:8001/docs)

---

## 4. Local Development Setup (Without Docker)

### Prerequisites:
- Python 3.10+ (Python 3.10 or 3.11 recommended)
- Node.js 18+ & npm
- FFmpeg (for audio format conversions)

### Helper Automation Scripts (Windows PowerShell):
```powershell
# Automated setup (installs Python packages, npm dependencies, creates .env)
.\scripts\setup_windows.ps1

# Run all test suites (Root, Dashboard, Clinical NLP, Transcription, Frontend build)
.\scripts\run_all_tests.ps1

# Check live health status of all running services
python .\scripts\check_health.py

# Launch local development environment guide
.\scripts\run_local.ps1

# Clean temporary test files and pycache without deleting databases
.\scripts\cleanup.ps1
```

### Windows Manual Setup Commands:
```powershell
# 1. Install dashboard dependencies
cd backend\dashboard
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 --reload

# 2. In a second terminal: Start Clinical NLP service
cd services\clinical_nlp
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8002 --reload

# 3. In a third terminal: Start Transcription service
cd services\transcription
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8003 --reload

# 4. In a fourth terminal: Start Mock EHR
cd mock_ehr
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --port 8001 --reload

# 5. In a fifth terminal: Start Frontend
cd frontend
npm install
npm run dev
```

### Linux / macOS Setup Commands:
```bash
# Frontend
cd frontend && npm install && npm run dev &

# Dashboard
cd backend/dashboard && pip install -r requirements.txt && uvicorn app.main:app --port 8000 &

# Clinical NLP
cd services/clinical_nlp && pip install -r requirements.txt && uvicorn app.main:app --port 8002 &

# Transcription
cd services/transcription && pip install -r requirements.txt && uvicorn app.main:app --port 8003 &

# Mock EHR
cd mock_ehr && pip install -r requirements.txt && uvicorn api.main:app --port 8001 &
```

---

## 5. Running the Automated Test Suite

The test suite covers contract compatibility, unit logic, clinical safety gates, and 3 synthetic consultation lifecycles:

```bash
# Run all tests across contract, unit, and end-to-end layers
python -m pytest tests -v -o "pythonpath=."
```

### Verified Test Layers:
- **Contract Compatibility (`tests/contract/`):** Verifies 2A `start_time` ↔ 2C `start` dual timestamp normalization, nullable patient age, and serialization.
- **Clinical Safety & Negation (`tests/unit/`):** Verifies negation preservation ("no chest pain"), historical asthma detection, and penicillin/amoxicillin conflict detection.
- **Acoustic Preprocessing (`tests/unit/`):** Verifies 16 kHz resampling, stereo-to-mono conversion, and lexical heuristic role classification.
- **End-to-End Scenarios (`tests/end_to_end/`):**
  1. *Scenario 1 (Normal):* Viral URI encounter → SOAP draft → Physician review → Electronic signoff → FHIR R4 Bundle + signed PDF export.
  2. *Scenario 2 (Allergy Conflict):* Penicillin-allergic patient prescribed Amoxicillin → Safety engine flags CRITICAL conflict → Blocks finalization gate.
  3. *Scenario 3 (Complex Negation/History):* Unstated patient age (`null`), negated chest pain, and childhood asthma (historical).
- **Failure Modes (`tests/unit/`):** Verifies invalid timestamps, expired/tampered JWT tokens, and malformed inputs.

---

## 6. Clinical Safety & Human-in-the-Loop Policies

1. **AI Never Finalizes:** An AI service cannot finalize or publish a clinical note. Only an authenticated physician can authorize the record.
2. **Conflict Gating:** Any `CRITICAL` safety finding (e.g., prescribing a drug that triggers a documented allergy) strictly blocks finalization with HTTP 409 until resolved.
3. **Four Acknowledgements Required:** Finalization requires explicit physician signoff:
   - Documentation reviewed.
   - Conflicts reviewed.
   - Medications and allergies verified.
   - Approved for EHR export.
4. **Preserve Negation & History:** Negated symptoms ("no chest pain") are never converted into active conditions. Historical diagnoses are clearly segregated.
5. **Immutable Audit Trail:** All physician edits, note revisions, conflict acknowledgements, PDF exports, and EHR handoffs generate permanent audit log entries.
6. **No Phantom Demographics:** If patient age is unstated in the encounter, it is preserved as `null`. It is never fabricated or guessed.

---

## 7. Troubleshooting Guide

### A. Docker & Container Startup
- If containers report database connection errors on first start, ensure the `postgres` healthcheck has completed (`retries: 10`).
- If port `5432` or `8000` is already in use by host software, change `POSTGRES_PORT` or `DASHBOARD_PORT` in your `.env` file.

### B. Python Dependencies & Virtual Environments
- If running locally without PostgreSQL installed, the system automatically falls back to SQLite (`sqlite:///clinical_scribe.db`), allowing full functionality without installing `psycopg` on the host.

### C. Microphone Permissions & Browser Capture
- Browser recording requires HTTPS or `http://localhost`. Ensure your browser permissions allow microphone access for `localhost:8080`.
- If using an unprivileged browser environment, use the built-in "Choose Audio File" button to upload a pre-recorded WAV/MP3/M4A/WebM file.

### D. Whisper & Pyannote Execution (CPU vs. GPU)
- Default configuration uses CPU mode (`WHISPER_DEVICE=cpu`, `compute_type=float32`).
- To enable NVIDIA CUDA GPU acceleration, set `WHISPER_DEVICE=cuda` and `compute_type=float16` in `.env` and verify CUDA toolkit installation.
- Pyannote speaker diarization includes an automated fallback to heuristic content-based role classification if HuggingFace credentials are not configured.

### E. Ollama & Local LLM Setup
- Local LLM generation uses Ollama (`qwen3:8b`). If Ollama is not running, the system automatically falls back to deterministic template generation with zero external network dependencies.
- To use Ollama:
  ```bash
  ollama run qwen3:8b
  ```
  And set `OLLAMA_BASE_URL=http://localhost:11434` in `.env`.

---

## 8. License & Medical Disclaimer

This software is an engineering assistance tool for clinical documentation workflow automation. It is designed to assist physicians by generating structured draft notes from consultation audio. **This system does not independently diagnose, treat, prescribe, or substitute for professional medical judgment.**

