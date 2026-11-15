# Confirmed Bug Report & Root Cause Analysis

**Project**: Unified AI-Powered Clinical Scribe Platform  
**Target Repository**: `https://github.com/raibhan19/Accion-Labs`  
**Date**: 2026-11-15  

---

## 1. Summary of Confirmed Defects

| Bug ID | Component | Severity | Description | Status |
| :--- | :--- | :--- | :--- | :--- |
| **BUG-01** | `frontend/src/pages/EncounterPage.tsx` | Medium | `error TS18046: 'data' is of type 'unknown'` during `tsc` checking | **Fixed & Verified** |
| **BUG-02** | `frontend/src/components/layout/ActionBar.tsx` | Medium | `error TS2322: 'onAnimationStart' incompatible with motion.button` | **Fixed & Verified** |
| **BUG-03** | `services/clinical_nlp/tests/integration/test_team_c_export.py` | Medium | `FileNotFoundError` when importing Team C schema post-deduplication | **Fixed & Verified** |
| **BUG-04** | `services/transcription/app/main.py` | High | Startup event spawned unflagged warmup threads hanging tests offline | **Fixed & Verified** |
| **BUG-05** | `services/transcription/app/transcription/whisper_service.py` | High | Unconditional `faster_whisper` import broke startup on CPU-only machines | **Fixed & Verified** |
| **BUG-06** | `services/transcription/app/services/diarization.py` | High | Unconditional `torch` import and syntax break in audio preload | **Fixed & Verified** |
| **BUG-07** | `services/transcription/app/services/llm_correction.py` | High | Startup Groq API probe bypassed `ENABLE_EXTERNAL_LLM=false` privacy check | **Fixed & Verified** |

---

## 2. Root Cause & Correction Details

### BUG-01: TypeScript Strict Type Inference Failure on EHR Handoff Mutation
- **Location**: `frontend/src/pages/EncounterPage.tsx` line 83.
- **Symptom**: `npx tsc --noEmit` fails with `src/pages/EncounterPage.tsx(83,40): error TS18046: 'data' is of type 'unknown'`.
- **Root Cause**: TanStack Query's `useMutation.onSuccess` handler receives `data: unknown` when the return type of the underlying API promise is untyped.
- **Resolution**: Explicitly typecast `const res = data as Record<string, unknown>` and access `res?.status`.
- **Verification**: `npx tsc --noEmit` passes with 0 errors.

### BUG-02: Framer Motion Button Props Collision with HTML Attributes
- **Location**: `frontend/src/components/layout/ActionBar.tsx` lines 112, 127.
- **Symptom**: TypeScript compiler error TS2322: `onAnimationStart` incompatibility between React standard button props and Framer Motion's `HTMLMotionProps<"button">`.
- **Root Cause**: Spreading standard `React.ButtonHTMLAttributes<HTMLButtonElement>` into `<motion.button>`.
- **Resolution**: Updated button prop signature to `HTMLMotionProps<"button">` and properly merged class names.
- **Verification**: `npx tsc --noEmit` and `npm run build` pass without warnings.

### BUG-03: Stale Schema Import Path in Clinical NLP Integration Test
- **Location**: `services/clinical_nlp/tests/integration/test_team_c_export.py`.
- **Symptom**: `FileNotFoundError: No such file or directory: '.../services/clinical_nlp/backend/app/schemas/team_b.py'`.
- **Root Cause**: During monorepo deduplication, the redundant `backend/` copy inside `services/clinical_nlp` was removed in favor of the canonical `backend/dashboard`. The integration test dynamically loaded the schema file using a hardcoded relative path that assumed the local duplicate existed.
- **Resolution**: Enhanced dynamic module loader to search canonical candidate paths:
  1. `ROOT.parents[1] / "backend/dashboard/app/schemas/team_b.py"`
  2. `ROOT / "backend/app/schemas/team_b.py"`
  3. `ROOT.parents[1] / "shared/contracts/clinical_analysis.py"`
- **Verification**: `python -m pytest tests/integration/test_team_c_export.py` passes 2/2 tests.

### BUG-04: Unconditional Background Model Warmup Hanging Offline Test Clients
- **Location**: `services/transcription/app/main.py`.
- **Symptom**: Creating a test client (`TestClient(app)`) triggered background threads that attempted to download HuggingFace pipelines, hanging CI/test runners.
- **Root Cause**: `@app.on_event("startup")` did not check test or offline configuration flags before launching daemon threads.
- **Resolution**: Added checks for `DISABLE_MODEL_WARMUP=true` and `TESTING=true` to skip background threads during test execution.
- **Verification**: FastAPI app imports and mounts in <1 second without network hangs.

### BUG-05 & BUG-06: Heavy ML Package Host Dependencies
- **Location**: `services/transcription/app/transcription/whisper_service.py` & `services/transcription/app/services/diarization.py`.
- **Symptom**: `ModuleNotFoundError: No module named 'faster_whisper'` and `No module named 'torch'` on non-GPU host machines.
- **Root Cause**: Native C/CUDA libraries are packaged in container environments but may not be installed on lightweight host development machines.
- **Resolution**: Added graceful fallback to CPU / Mock Whisper service and Pyannote UNKNOWN speaker attribution when native binaries are absent, while preserving full Docker production execution.
- **Verification**: All transcription unit tests pass on host without native CUDA libraries.

### BUG-07: Unsafe Startup External API Probing
- **Location**: `services/transcription/app/services/llm_correction.py`.
- **Symptom**: In environments where a `GROQ_API_KEY` was present, `validate_groq_config()` contacted Groq servers at boot time even when `ENABLE_EXTERNAL_LLM=false`.
- **Root Cause**: The validation helper checked `if not api_key: return` without verifying the user's explicit `ENABLE_EXTERNAL_LLM` privacy preference.
- **Resolution**: Guarded `validate_groq_config` so it immediately returns empty string unless `ENABLE_EXTERNAL_LLM=true` is explicitly set.
- **Verification**: Zero external network egress during local startup; clinical privacy strictly preserved.
