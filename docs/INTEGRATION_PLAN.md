# Step-by-Step Service Integration Plan

## Phase Alignment & Execution Strategy

### 1. Phase 1: Target Monorepo Construction
- Establish `clinical-scribe-unified/` with isolated services:
  - `frontend/` (Vite, React, TypeScript)
  - `services/transcription/` (FastAPI, Faster-Whisper, Pyannote)
  - `services/clinical_nlp/` (FastAPI, Extraction, Safety, Grounding)
  - `backend/dashboard/` (FastAPI, SQLAlchemy, Database, Exporters)
  - `mock_ehr/` (Mock OpenEMR receiver)
  - `shared/` (Pydantic contracts, schemas, examples)
  - `tests/` (Unit, Contract, Integration, End-to-End)
  - `infrastructure/docker/` (Dockerfiles & Compose)

### 2. Phase 2: Source Consolidation & Deduplication
- Import clean code from Repositories A, B, and C.
- Remove redundant `backend/`, `frontend/`, `mock_ehr/`, and `docker/` from Repository B.
- Preserve and merge Team B's fixes (nullable age, conflict handling) into the authoritative dashboard.
- Retain all experimental evaluation datasets and logs in `data/evaluation/`.

### 3. Phase 3 & 4: Shared Contracts & Independent Execution
- Implement `shared/contracts/transcript.py`, `clinical_analysis.py`, `encounter.py`.
- Guarantee bidirectional schema compatibility.
- Ensure each microservice is independently testable and runnable with isolated dependencies.

### 4. Phase 5 & 6: End-to-End Integration & Dashboard Enhancements
- Introduce browser-based audio capture (`MediaRecorder`) on the dashboard home and encounter pages.
- Implement dashboard coordinator routes to stream audio to transcription, forward transcript to NLP, and receive enriched SOAP analysis.
- Display citations, grounding confidence, and safety alerts directly within the physician UI.

### 5. Phase 7: Encounter Lifecycle & Safety Gate
- Enforce physician-in-the-loop validation: AI cannot finalize encounters.
- Block finalization on unacknowledged CRITICAL conflicts.
- Implement comprehensive audit logging for all physician note edits.
- Deliver PDF and FHIR export handoffs to Mock EHR.

### 6. Phase 8 & 9: Docker Orchestration & Verification
- Build single-command `docker-compose.yml` orchestrating the entire network.
- Execute automated unit, contract, integration, end-to-end, and failure tests across 3 synthetic clinical encounters.

