# System Architecture: Unified Clinical Scribe Platform

## 1. High-Level Architecture Overview

The Unified Clinical Scribe Platform is an end-to-end, privacy-first, on-premise/hybrid clinical documentation system. It translates physician-patient consultation speech into structured, grounded, and verified clinical notes with strict human-in-the-loop review.

```
       +--------------------------------------------------------+
       |                  React Frontend (Vite)                 |
       |  - MediaRecorder Audio Capture                         |
       |  - Real-Time Transcript & SOAP Editor                  |
       |  - Grounding & Safety Warnings Review                  |
       |  - Finalize Gate (Physician Electronic Approval)       |
       +----------------------------+---------------------------+
                                    |
                          REST / HTTP Multipart
                                    v
       +--------------------------------------------------------+
       |             Dashboard API (Backend: 8000)              |
       |  - Encounter Lifecycle & Canonical ID Coordinator      |
       |  - PostgreSQL Database (Encounters, Audit, Notes)      |
       |  - PDF / FHIR Exporters & Mock EHR Dispatcher          |
       |  - Role-Based Authentication & Authorization           |
       +-------------+----------------------------+-------------+
                     |                            |
          HTTP / Ingest Audio            HTTP / Canonical Ingestion
                     v                            v
+--------------------------+    +--------------------------------+
| Transcription Service    |    | Clinical NLP Service           |
| (Services/Transcription) |    | (Services/Clinical_NLP: 8002)  |
| - Faster-Whisper ASR     |    | - Rule-based Entity Extraction |
| - Pyannote Diarization   |    | - Conflict & Safety Engine     |
| - Content Role Classifier|    | - Grounding Citation Verifier  |
| - Output: Segments JSON  +--->+ - Local Ollama / Template SOAP |
+--------------------------+    +--------------------------------+
                                                  |
                                                  v
                                      +--------------------------+
                                      | Mock EHR (Mock_EHR: 8001)|
                                      | - FHIR R4 Bundle Ingest  |
                                      | - Storage of Final Chart |
                                      +--------------------------+
```

---

## 2. Service Ownership Boundaries

### A. Transcription Service (`services/transcription`)
- **Domain:** Acoustic signals, speech-to-text, speaker diarization, role mapping.
- **Inputs:** Audio files (WAV, MP3, M4A, WebM, OGG) or streaming PCM chunks.
- **Outputs:** Speaker-labeled timestamped segments with confidence scores (`TeamATranscriptIn`).
- **Privacy Boundary:** Audio never leaves the local instance. Heuristic role classification runs entirely offline. External Groq calls are disabled by default.

### B. Clinical NLP Service (`services/clinical_nlp`)
- **Domain:** Clinical entity extraction, negation, medical history context, safety rule evaluation, grounding verification, draft SOAP and prescription generation.
- **Inputs:** Canonical transcript payloads (`TeamATranscriptIn` or internal `Transcript`).
- **Outputs:** Structured `ConsultationAnalysis` and formatted `TeamBPayload`.
- **Privacy Boundary:** Zero external data transmission by default. Local LLM (Ollama) or deterministic rule-based template generation.

### C. Dashboard & Encounter Service (`backend/dashboard`)
- **Domain:** Source of truth for patient records, encounter persistence, physician authentication, clinical note editing, audit events, finalization enforcement, and EHR export.
- **Inputs:** User interactions, audio uploads, Team B payloads.
- **Outputs:** Verified clinical documentation, FHIR Bundles, PDF summaries, EHR handoffs.
- **Security:** Strict physician authentication; AI cannot finalize records.

---

## 3. Data Flow & Encounter Lifecycle

1. **Patient Selection / Encounter Creation:** Physician chooses or initializes an encounter with canonical `encounter_id`.
2. **Consultation Audio Capture:** Browser `MediaRecorder` streams or posts recorded consultation audio to Dashboard, which dispatches to Transcription.
3. **Transcription & Diarization:** Faster-Whisper generates word timestamps; Pyannote assigns speaker labels; content heuristics determine DOCTOR vs. PATIENT.
4. **Clinical Processing:** Transcript is posted to Clinical NLP service. Entities (medications, allergies, symptoms, conditions) are extracted; safety rules cross-reference patient allergies with draft prescriptions; grounding checks calculate evidence coverage.
5. **Dashboard Presentation:** Dashboard receives full clinical analysis. Citations link SOAP sentences to transcript timestamps; safety warnings appear with severity badges (CRITICAL, HIGH, MEDIUM).
6. **Physician Review & Audit:** Physician validates, edits, or adds clinical statements. Any change generates an immutable audit record.
7. **Finalization Gate:** If CRITICAL conflicts exist, finalization is blocked. Once acknowledged or resolved, the physician finalizes the chart.
8. **Export & Handoff:** System persists finalized encounter, generates FHIR Bundle, exports signed PDF, and dispatches to Mock EHR.

