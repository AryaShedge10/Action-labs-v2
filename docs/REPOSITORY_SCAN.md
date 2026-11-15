# Complete Repository Scan & Architectural Dependency Map

**Project**: Unified AI-Powered Clinical Scribe Platform  
**Target Repository**: `https://github.com/raibhan19/Accion-Labs`  
**Date**: 2026-11-15  

---

## 1. Monorepo Services & Architectural Topology

```
                       ┌──────────────────────────────┐
                       │       React 18 Frontend      │
                       │    (Port 3000 / Vite Dev)    │
                       └──────────────┬───────────────┘
                                      │ REST / JSON (JWT Auth)
                                      ▼
                       ┌──────────────────────────────┐
                       │   Dashboard Backend (FastAPI)│
                       │    (Internal 8000 / Host 8000)│
                       └──┬───────────┬──────────────┬┘
                          │           │              │
      Coordinator Call    │           │ REST         │ FHIR Bundle
            ┌─────────────┘           ▼              └─────────────┐
            │             ┌───────────────────────┐                │
            ▼             │ Clinical NLP & Safety │                ▼
┌───────────────────────┐ │       (FastAPI)       │     ┌─────────────────────┐
│ Transcription Service │ │(Internal 8001 / 8002) │     │      Mock EHR       │
│       (FastAPI)       │ └───────────────────────┘     │(Internal 8001 /8003)│
│(Internal 8000 / 8002) │                               └─────────────────────┘
└───────────────────────┘
```

---

## 2. Service Specifications

### 2.1 Frontend (`frontend/`)
- **Technology Stack**: React 18.2, TypeScript 5.2, Vite 5.4, Tailwind CSS, TanStack Query, Framer Motion, Lucide React.
- **Entrypoints**: `frontend/index.html` → `frontend/src/main.tsx` → `frontend/src/App.tsx`.
- **Pages**:
  - `HomePage.tsx`: Patient directory, quick consultation launch, direct audio recorder component.
  - `EncounterPage.tsx`: Full clinical workflow with dual-pane layout (left: Patient Panel & Transcript Viewer; right: SOAP Editor, Validation Panel, and Finalize Dialog).
- **API Client**: `frontend/src/services/api.ts` configured with `VITE_API_URL` (defaults to `/api` or `http://localhost:8000/api`).
- **Internal Port**: 3000 (Vite preview/dev), 80 via Nginx in container.

### 2.2 Dashboard Backend (`backend/dashboard/`)
- **Technology Stack**: Python 3.10+, FastAPI, SQLAlchemy 2, Pydantic v2, PostgreSQL (with SQLite fallback for zero-dependency local runs), ReportLab, PyJWT.
- **Entrypoint**: `backend/dashboard/app/main.py` (`uvicorn app.main:app`).
- **Key Modules**:
  - `app/api/encounters.py`: CRUD for encounters, audio upload coordinator, transcript processor, note updates, validation, physician finalization, PDF and FHIR exports.
  - `app/api/ehr.py`: Mock EHR integration proxy endpoints.
  - `app/auth.py`: HMAC-SHA256 JWT generation and validation; role-based access control (`physician` vs `scribe`); local demo bypass toggle `AUTH_DISABLED=true`.
  - `app/validators/conflicts.py`: Deterministic conflict detection (Penicillin-Amoxicillin, Male pregnancy, ungrounded medications, dosage errors).
  - `app/validators/grounding.py`: Claim-to-transcript verbatim alignment verification.
  - `app/services/pdf.py`: Clinical PDF note generator using ReportLab.
  - `app/services/fhir.py`: HL7 FHIR R4 Bundle generator (DocumentReference, Encounter, Patient, Condition).
- **Internal Port**: 8000. Host Port: 8000.
- **Health Endpoint**: `GET /api/health`
- **Documentation**: `GET /api/docs`

### 2.3 Clinical NLP Service (`services/clinical_nlp/`)
- **Technology Stack**: Python 3.10+, FastAPI, Pydantic v2, Ollama integration (Qwen3 8B), hybrid deterministic rule engine.
- **Entrypoint**: `services/clinical_nlp/app/main.py` (`uvicorn app.main:app`).
- **Key Modules**:
  - `app/pipeline.py`: Clinical NLP orchestration pipeline (Ingestion → Entity Extraction → Negation → Historical Context → Safety Engine → Grounding → SOAP Note Generation).
  - `app/extraction/extractor.py`: Rule-based deterministic clinical entity extractor.
  - `app/safety/rules.py`: Deterministic clinical safety rules (Allergies, Drug Interactions, Contraindications, Vital Signs, Demographics).
  - `app/grounding/verifier.py`: Grounding and citation validator ensuring every generated SOAP statement is backed by transcript timestamps.
  - `app/export/team_c.py`: Team C export adapter mapping NLP analysis into the authoritative encounter schema.
- **Internal Port**: 8001. Host Port: 8001 (or 8002 via Docker mapping).
- **Health Endpoint**: `GET /v1/health`

### 2.4 Transcription Service (`services/transcription/`)
- **Technology Stack**: Python 3.10+, FastAPI, Faster-Whisper, Pyannote Audio, Scipy, SoundFile, SoundDevice.
- **Entrypoint**: `services/transcription/app/main.py` (`uvicorn app.main:app`).
- **Key Modules**:
  - `app/api/routes.py`: File upload transcription (`POST /api/v1/transcribe`), model discovery (`GET /api/v1/models`), health check (`GET /api/v1/health`).
  - `app/api/live_routes.py`: Browser audio upload endpoint (`POST /api/v1/live/upload-audio`), live recording session management, role swapping (`POST /api/v1/live/swap-roles`), consultation export for Team B (`GET /api/v1/live/team-b/consultation/{consultation_id}`).
  - `app/services/alignment.py`: 4-rule alignment algorithm pairing Whisper segments with Pyannote speaker turns.
  - `app/services/utterance_manager.py`: Streaming utterance tracker providing stable IDs and merging consecutive turns.
  - `app/audio/preprocessing.py`: Audio normalization, mono conversion, 16kHz resampling with scipy fallback.
- **Internal Port**: 8000. Host Port: 8002.
- **Health Endpoint**: `GET /api/v1/health`

### 2.5 Mock EHR Service (`mock_ehr/`)
- **Technology Stack**: Python 3.10+, FastAPI, SQLAlchemy, PostgreSQL/SQLite.
- **Entrypoint**: `mock_ehr/api/main.py`.
- **Key Modules**: FHIR bundle ingestion (`POST /api/v1/fhir/Bundle`), patient directory (`GET /api/v1/patients`), encounter history.
- **Internal Port**: 8001. Host Port: 8003.
- **Health Endpoint**: `GET /health`

---

## 3. Detailed Issue Catalog & Proposed Remediation

### Issue ISS-01: TypeScript `TS18046: 'data' is of type 'unknown'`
- **File**: `frontend/src/pages/EncounterPage.tsx` (Line 83)
- **Severity**: Medium
- **Reproduction**: Run `npx tsc --noEmit` in `frontend/`.
- **Root Cause**: The TanStack Query `useMutation` hook for uploading audio or processing transcripts infers the returned payload as `unknown` when strict mode is active.
- **Proposed Solution**: Type the mutation or cast `(data as { encounter_id?: string; id?: string })` before reading properties.
- **Verification Test**: `npx tsc --noEmit` must return 0 errors.

### Issue ISS-02: Motion Button Type Mismatch on `onAnimationStart`
- **File**: `frontend/src/components/layout/ActionBar.tsx` (Lines 112, 127)
- **Severity**: Medium
- **Reproduction**: Run `npx tsc --noEmit` in `frontend/`.
- **Root Cause**: Spreading standard HTML button attributes into `motion.button` causes TypeScript compiler to flag conflicting signatures between React's `AnimationEventHandler<HTMLButtonElement>` and Framer Motion's `(definition: AnimationDefinition) => void`.
- **Proposed Solution**: Separate motion animation properties (`whileHover`, `whileTap`) and avoid passing incompatible `onAnimationStart` event props.
- **Verification Test**: `npx tsc --noEmit` passes without errors.

### Issue ISS-03: Integration Test Path Error in `test_team_c_export.py`
- **File**: `services/clinical_nlp/tests/integration/test_team_c_export.py`
- **Severity**: Medium
- **Reproduction**: Run `python -m pytest tests/integration/test_team_c_export.py` from `services/clinical_nlp`.
- **Root Cause**: The test referenced `ROOT / "backend/app/schemas/team_b.py"`, which existed when Repo B contained duplicate copies of the backend. In the monorepo, the canonical schema is in `backend/dashboard/app/schemas/team_b.py` or `shared/contracts/`.
- **Proposed Solution**: Update the path resolution to check `ROOT.parents[1] / "backend/dashboard/app/schemas/team_b.py"` with fallback to `shared/contracts/`.
- **Verification Test**: Both integration tests pass.

### Issue ISS-04: Model Warmup Startup Threads Hanging in Offline Mode
- **File**: `services/transcription/app/main.py`
- **Severity**: High
- **Reproduction**: Start FastAPI test client against `services/transcription/app/main.py` without network access or HuggingFace tokens.
- **Root Cause**: `@app.on_event("startup")` unconditionally spawns background threads that attempt to download Whisper and Pyannote models.
- **Proposed Solution**: Honor `DISABLE_MODEL_WARMUP=true` or `TESTING=true` environment variable to skip background warmup when executing unit and integration test suites.
- **Verification Test**: `test_swap_endpoint.py` executes and passes in <2 seconds.

### Issue ISS-05: Non-Test Script Collected by Pytest
- **File**: `services/transcription/tests/realtime_nvidia/scripts/test_3min_session.py`
- **Severity**: Low
- **Reproduction**: Run `python -m pytest services/transcription/tests`.
- **Root Cause**: File starts with `test_` but contains top-level hardware audio capture script with `sys.exit(1)`.
- **Proposed Solution**: Rename file to `run_3min_session.py` or configure `pytest.ini` with `testpaths` and `norecursedirs` to ignore `tests/realtime_nvidia/scripts`.
- **Verification Test**: Pytest discovers only valid test files without collection failure.

---

## 4. Contract Compatibility Matrix

| Producer | Consumer | Contract Type | Schema & Fields Checked | Status |
| :--- | :--- | :--- | :--- | :--- |
| Transcription Service (2A) | Clinical NLP (2B) | JSON Transcript | `TranscriptPayload` with `segments` (`speaker`, `text`, `start_time`/`start`, `end_time`/`end`) | **Normalized & Verified** |
| Clinical NLP (2B) | Dashboard Backend (2C) | Analysis Payload | `TeamBPayload` (`patient`, `transcript`, `soap`, `conflicts`, `grounding`) | **Normalized & Verified** |
| Dashboard Backend (2C) | Mock EHR | HL7 FHIR Bundle | FHIR R4 Bundle (`type: document`, `DocumentReference`, `Encounter`, `Patient`) | **Standardized & Verified** |
| Frontend | Dashboard Backend | REST API | JSON with Bearer Token, nullable patient demographics | **Standardized & Verified** |
