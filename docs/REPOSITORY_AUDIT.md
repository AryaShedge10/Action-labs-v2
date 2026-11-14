# Comprehensive Three-Repository Technical Audit

**Project:** Unified AI-Powered Clinical Scribe Platform  
**Date:** November 14, 2026  
**Auditor:** Principal Software Architect & Lead Systems Engineer  

---

## 1. Executive Summary

This audit evaluates the architectural state, code quality, dependency structures, and API contracts of three independently developed repositories:
1. **Repository A (Audio & Transcription):** \SahilKhaire2006/Accion_lab_team_M3\ (145 files)
2. **Repository B (Clinical NLP & Safety):** \AryaShedge10/Action_labs\ (147 files)
3. **Repository C (Dashboard, EHR & Encounter Lifecycle):** \munnsss/clinical-scribe\ (89 files)

The repositories represent complementary facets of a clinical documentation pipeline, but currently suffer from architectural fragmentation, code duplication, field name discrepancies, and environment-bound assumptions (e.g., sounddevice microphone access vs. browser audio capture).

---

## 2. Repository A: Audio Processing & Transcription

- **Primary Stack:** Python 3.10+, FastAPI, Faster-Whisper, Pyannote.Audio, SoundDevice, SoundFile, Librosa, Groq SDK.
- **Core Components:**
  - \pp/api/routes.py\: File upload endpoint (\POST /transcribe\), health, and model listing.
  - \pp/api/live_routes.py\: Server-side streaming recording via \sounddevice.InputStream\ (\POST /start-recording\, \POST /stop-recording\, \GET /live-feed\, \GET /transcript/{session_id}\, and Team B integration \GET /api/v1/live/team-b/consultation/{consultation_id}\).
  - \pp/transcription/whisper_service.py\: Local Faster-Whisper singleton runner.
  - \pp/speaker/diarization_interface.py\ & \pp/services/diarization.py\: Pyannote audio speaker diarization.
  - \pp/services/alignment.py\ & \pp/services/merge.py\: Word-level alignment and utterance merging.
  - \pp/services/roles.py\: Heuristic keyword-based role assignment (Doctor vs. Patient).
  - \pp/services/llm_correction.py\: Optional cloud-based Groq LLM role refinement and cleanup.
- **Strengths:**
  - Robust on-device Faster-Whisper singleton architecture.
  - Local content-based heuristic role detector (\_DOCTOR_PATTERNS\, \_PATIENT_PATTERNS\).
  - Clean timestamped output format with segment confidence scores.
- **Critical Vulnerabilities & Limitations:**
  - **Server-Side Microphone Dependency:** \live_routes.py\ binds directly to the server's sound hardware via \sounddevice.InputStream\. In containerized or remote server deployments, this fails or records the host machine rather than the physician's microphone.
  - **Unintentional Cloud Leakage:** \pp/services/llm_correction.py\ defaults to sending transcript text to Groq API. In privacy-preserving/HIPAA environments, this must be disabled by default or made explicitly opt-in with strict PHI safeguards.
  - **BOM Character In Source:** \pp/api/routes.py\ contains a UTF-8 BOM character (\﻿\) that causes standard Python AST parsers to fail.
  - **No Dockerfile:** Repository A lacked containerization configurations.

---

## 3. Repository B: Clinical NLP & Safety Engine

- **Primary Stack:** Python 3.11+, FastAPI, Pydantic v2, Requests, Ollama (Local LLM), SQLite/in-memory store.
- **Core Components:**
  - \pp/pipeline.py\: End-to-end clinical pipeline orchestrator (normalization -> extraction -> safety rules -> prescription generation -> SOAP note generation -> grounding verification).
  - \pp/extraction/\: Rule-based & hybrid entity extractors (medications, allergies, conditions, vitals).
  - \pp/safety/\: Deterministic safety rules engine (\llergy_rules.py\, \medication_rules.py\, \demographic_rules.py\).
  - \pp/grounding/\: Transcript evidence verifier (\erifier.py\).
  - \pp/ingestion/adapter.py\ & \	eam_a_client.py\: Inbound adapter normalising Team A payloads.
  - \pp/export/team_c.py\: Outbound mapper converting internal \ConsultationAnalysis\ into Team C's \TeamBPayload\.
- **Strengths:**
  - Fully local-first, zero-remote-leakage architecture. Safe deterministic fallbacks if Ollama is unreachable.
  - Rigorous safety rule checks (e.g. penicillin allergy vs amoxicillin prescription).
  - Claim-level grounding and transcript segment citation linking.
- **Critical Vulnerabilities & Limitations:**
  - **Massive Code Duplication:** Repository B contained a full copy of Repository C's \ackend/\, \rontend/\, \mock_ehr/\, and \docker/\.
  - **Divergent Schema Fix in Copied Code:** In epo_b/backend/app/schemas/team_b.py\, Team B patched \Patient.age\ to be \int | None = None\ and updated conflict validation accordingly, while original Repository C retained \ge: int\.
  - **No Unified Database:** Stored consultation results in a local SQLite file (\data/store/consultations.db\) rather than connecting with the primary encounter lifecycle.

---

## 4. Repository C: Dashboard, Encounter Lifecycle & EHR

- **Primary Stack:** TypeScript, React 18, Tailwind CSS, Vite, TanStack Query, Framer Motion, Lucide, FastAPI, SQLAlchemy 2.0, PostgreSQL 16, ReportLab, Psycopg 3.
- **Core Components:**
  - \ackend/app/main.py\: Encounter management API and startup schema creation.
  - \ackend/app/api/encounters.py\: REST endpoints for encounters, validation, notes, finalizing, audit trails, and PDF/FHIR export.
  - \ackend/app/models/orm.py\: SQLAlchemy models for \Encounter\, \AuditEvent\, \EhrHandoff\.
  - \ackend/app/validators/\: Independent clinical and grounding validators.
  - \rontend/src/\: Comprehensive physician dashboard with SOAP editor, transcript viewer, validation panel, and audit drawer.
  - \mock_ehr/\: OpenEMR-style FHIR bundle receiver.
- **Strengths:**
  - Mature encounter lifecycle and physician approval gate (AI drafts are never finalized automatically).
  - Comprehensive audit logging and export to PDF and FHIR Bundle JSON.
  - Polished modern UI with responsive feedback.
- **Critical Vulnerabilities & Limitations:**
  - **No Browser Audio Recording UI:** Lacked audio recording or upload workflows; could only load static demo encounters or receive external webhooks.
  - **Demo-Grade Authentication:** \uth.py\ accepts any non-empty string as a Bearer token and returns a dummy doctor principal.
  - **Strict Demographic Validation:** Required \ge\ as a non-null integer, which broke compatibility with real-world transcripts where patient age is unstated.
  - **Timestamp Field Discrepancies:** Frontend & backend schemas expected \start\ and \end\, whereas Team A emitted \start_time\ and \end_time\.

---

## 5. Architectural Reconciliation Plan

1. Monorepo structure with clear ownership boundaries.
2. In-browser audio capture with chunk/file upload to the Transcription service.
3. Canonical contract schemas in \shared/contracts/\ with backward-compatible adapters.
4. Harmonization of nullable patient demographics.
5. Removal of duplicated 2C code from 2B while preserving Team B's fixes.
6. Unified Docker Compose orchestrating all services with private network DNS.
