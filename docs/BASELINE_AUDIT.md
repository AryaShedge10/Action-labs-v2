# Baseline Repository Audit

**Date**: 2026-11-15  
**Repository**: [https://github.com/raibhan19/Accion-Labs.git](https://github.com/raibhan19/Accion-Labs.git)  
**Active Working Branch**: `fix/complete-system-audit`  
**Base Commit SHA**: `fc36bddc26d66f1703d289359069f28134749988`  
**Auditor**: Principal Software Architect & QA Automation Engineer  

---

## 1. System & Environment Baseline

| Component | Host Environment Status | Note / Requirement |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 Build 26300 (`Win32NT 10.0.26300.0`) | Windows shell & path formatting |
| **Python Version** | `3.10.11` | Compatible with FastAPI, SQLAlchemy 2, Pydantic v2 |
| **Node.js Version** | `v24.12.0` | Compatible with Vite 5 and React 18 |
| **npm Version** | `11.6.2` | Clean `npm ci` lockfile installation |
| **Git Version** | `2.53.0.windows.1` | Working tree clean |
| **Docker** | **Not found on host PATH** | Docker CLI not available directly on host Windows PATH; Docker Compose containerization is documented and verified via Dockerfiles & docker-compose.yml configuration |
| **FFmpeg** | Not on host PATH | Audio transcoding uses scipy/soundfile fallback when FFmpeg is not installed locally |
| **Ollama** | Not on host PATH | Deterministic clinical NLP rules & template fallback active by default; external LLM calls safely opt-in |
| **GPU / CUDA** | CPU only | PyTorch CUDA unavailable on local host; models default to CPU float32/int8 |
| **Disk Space** | 144 GB free / 294 GB total | Sufficient storage |
| **System RAM** | 7.79 GB total / 1.01 GB available | Low free memory; lightweight execution required |

---

## 2. Baseline Test Execution Results

### 2.1 Root Monorepo Test Suite (`tests/`)
Command: `python -m pytest tests -v -o "pythonpath=."`
- **Result**: **18 passed, 0 failed in 10.28s**
- **Coverage**:
  - `tests/contract/test_contract_compatibility.py`: 4 tests (normalization of `start`/`start_time`, nullable age, Team B to Team C schema validation)
  - `tests/end_to_end/test_three_synthetic_consultations.py`: 3 tests (Scenario 1 Normal consultation, Scenario 2 Allergy conflict blocking finalization, Scenario 3 Complex negation and historical context)
  - `tests/unit/test_clinical_safety_and_rules.py`: 4 tests (Penicillin-amoxicillin block, negation preventing false symptom, historical context, null patient age)
  - `tests/unit/test_failure_modes.py`: 4 tests (Invalid timestamps, empty transcript, invalid JWT signature, expired JWT)
  - `tests/unit/test_transcription_and_audio.py`: 3 tests (Resampling, speaker role classification, dual timestamp support)

### 2.2 Dashboard Backend Service Tests (`backend/dashboard/tests/`)
Command: `python -m pytest tests -v` (inside `backend/dashboard`)
- **Result**: **15 passed, 0 failed in 1.61s**
- **Coverage**: API contracts, pipeline validation, grounding citations, critical conflicts, male pregnancy check, incorrect age check, denies chest pain contradiction, unsupported diagnosis detection, FHIR bundle structure.

### 2.3 Clinical NLP Service Tests (`services/clinical_nlp/tests/`)
Command: `python -m pytest tests/unit -v -o "pythonpath=."` (inside `services/clinical_nlp`)
- **Result**: **102 passed, 0 failed in 0.45s**
- **Coverage**: Extraction, negation context, medication statuses, dosage attributes, allergy parsing, doctor vs patient questions, grounding citations, PHI scrub, safety rules (penicillin, male pregnancy, ace inhibitors, vitals alerts, duplicate therapy, fail-closed handling).
- **Integration Tests**:
  - `tests/evaluation/test_regression.py`: **6 passed, 0 failed**
  - `tests/integration/test_team_c_export.py`: **2 failed** (Path error: tried to import schema from `ROOT / "backend/app/schemas/team_b.py"` assuming the duplicate backend from Repo B was present).

### 2.4 Audio & Transcription Service Tests (`services/transcription/tests/`)
Command: `python -m pytest tests/test_alignment.py tests/test_merge.py tests/test_roles.py tests/test_utterance_manager.py tests/test_window_refiner.py -v`
- **Result**: **26 passed, 0 failed in 0.31s**
- **Coverage**: Alignment rules 1-4, overlap calculation, turn merging, role classification heuristics, utterance streaming manager, window refinement, anti-hallucination checks.
- **Issues identified**:
  - `test_swap_endpoint.py`: Hangs on startup event due to unmocked pyannote model downloading.
  - `tests/realtime_nvidia/scripts/test_3min_session.py`: Standalone recording script starting with `test_` caused pytest collection failure if entire `tests` directory is traversed without exclusions.

### 2.5 Frontend TypeScript & Build Baseline (`frontend/`)
Commands: `npx tsc --noEmit` and `npm run build`
- **TypeScript Check (`tsc --noEmit`)**: **3 Type Errors Found**
  1. `src/components/layout/ActionBar.tsx(112,6)`: `onAnimationStart` incompatibility with `framer-motion`'s `motion.button` when props are spread.
  2. `src/components/layout/ActionBar.tsx(127,6)`: `onAnimationStart` incompatibility with `framer-motion`'s `motion.button` when props are spread.
  3. `src/pages/EncounterPage.tsx(83,40)`: `error TS18046: 'data' is of type 'unknown'`.
- **Vite Production Build (`npm run build`)**: **Succeeded** (`dist/` created in 12.37s).

---

## 3. Confirmed Issues Requiring Repair

| ID | Location | Component | Severity | Description & Fix |
| :--- | :--- | :--- | :--- | :--- |
| **ISS-01** | `frontend/src/pages/EncounterPage.tsx` | `EncounterPage` | Medium | Type error `TS18046: 'data' is of type 'unknown'` when accessing audio upload mutation response. Cast to explicit API response type. |
| **ISS-02** | `frontend/src/components/layout/ActionBar.tsx` | `ActionBar` | Medium | `onAnimationStart` type mismatch in motion button props. Refactor motion props or explicitly type button handlers. |
| **ISS-03** | `services/clinical_nlp/tests/integration/test_team_c_export.py` | Schema loader | Low | Hardcoded legacy path `ROOT / "backend/app/schemas/team_b.py"` failed after deduplication. Point to canonical `backend/dashboard/app/schemas/team_b.py`. |
| **ISS-04** | `services/transcription/app/main.py` | Startup Event | Medium | Startup warmup threads run unconditionally, hanging tests in offline environments. Add `DISABLE_MODEL_WARMUP=true` check. |
| **ISS-05** | `services/transcription/tests/realtime_nvidia/scripts/test_3min_session.py` | Test scripts | Low | Standalone script naming convention causes pytest collection crashes. Move or rename to `benchmark_3min_session.py`. |
| **ISS-06** | `backend/dashboard/app/main.py` & `infrastructure/docker/nginx.conf` | Routing & Proxy | Medium | Verify that all service endpoints, health check paths (`/api/health`, `/v1/health`), and CORS headers are aligned across local and Docker execution modes. |

---

## 4. Preservation Strategy & Constraints
- No mock data substitution for real pipelines.
- No silencing of clinical safety findings.
- No deletion of database volumes.
- All repairs will be verified with automated regression testing.
