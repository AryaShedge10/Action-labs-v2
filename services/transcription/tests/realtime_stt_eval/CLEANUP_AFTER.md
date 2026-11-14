# Phase 1 — Post-Cleanup Verification & Disk Reclaimed Report

**Date / Time:** 2026-10-05 12:38 IST  
**Host System:** Windows (NT)  
**Workspace:** `A:\VIT-3rd-sem\3rd_sem\EDI_Accion_lab`  
**Status:** SUCCESSFUL — All targeted MOSS experiments completely removed.

---

## 1. Summary of Removed Paths and Space Reclaimed

| Deleted Path | Description | Files Removed | Space Reclaimed (MB) | Space Reclaimed (GB) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `tests\moss_env\` | Isolated Python virtualenv with MOSS dependencies | 37,057 | 5,266.54 MB | 5.143 GB | Completely Removed |
| `tests\moss_hybrid\` | Experimental 3-layer hybrid server & worker scripts | 243 | 5.73 MB | 0.006 GB | Completely Removed |
| `tests\moss_profile_env\` | Virtualenv used during Step 1 profiling | 30,056 | 9,971.26 MB | 9.738 GB | Completely Removed |
| `tests\moss_profile_env_clean\` | Clean profiling environment snapshot | 48,850 | 5,564.39 MB | 5.434 GB | Completely Removed |
| `tests\moss_realtime\` | MOSS realtime 20s-window test server & UI | 80 | 61.83 MB | 0.060 GB | Completely Removed |
| `tests\moss_test\` | MOSS Git submodule / harness repository | 123 | 0.99 MB | 0.001 GB | Completely Removed |
| `~/.cache/huggingface/hub/models--OpenMOSS-Team--MOSS-Transcribe-Diarize\` | MOSS model weights (safely targeted) | 36 | 3,496.34 MB | 3.414 GB | Completely Removed |
| **TOTALS** | — | **116,445** | **24,367.08 MB** | **23.796 GB** | **RECLAIMED** |

---

## 2. Remaining Files & Unrelated Artifacts Intentionally Left Untouched

The following caches, environments, and directories were examined and **intentionally preserved**:

1. **Production Virtual Environment (`venv\`):**
   - Contains production dependencies (`faster-whisper`, `pyannote.audio`, `fastapi`, `uvicorn`, etc.).
   - Untouched and intact.
2. **Production Hugging Face Model Caches:**
   - `models--pyannote--speaker-diarization-3.1` (Required by production diarization)
   - `models--pyannote--segmentation-3.0` (Required by pyannote)
   - `models--pyannote--wespeaker-voxceleb-resnet34-LM` (Required by pyannote)
   - `models--Systran--faster-whisper-base.en` (Required by production Whisper)
   - `models--Systran--faster-whisper-small.en` (Required by production Whisper)
   - `models--google--owlvit-base-patch32`, `models--Salesforce--blip-vqa-base` (Unrelated user models)
3. **Production Application Code:**
   - `app/` and `static/` remain completely untouched.

---

## 3. Remaining MOSS Files Check

A scan of the repository confirms:
- Zero MOSS virtual environments remain in `tests/`.
- Zero MOSS scripts or benchmark logs remain in `tests/`.
- Zero MOSS cache entries remain in the Hugging Face hub cache.

Phase 1 cleanup is 100% complete.
