# Phase 0 — Pre-Cleanup Safety & Inventory Report

**Date / Time:** 2026-10-05 12:35 IST  
**Host System:** Windows (NT)  
**Workspace:** `A:\VIT-3rd-sem\3rd_sem\EDI_Accion_lab`  
**Purpose:** Pre-cleanup inventory of all MOSS-specific experimental environments, caches, models, and dependencies prior to removal.

---

## 1. Production Baseline Identification (DO NOT TOUCH)

The following components represent the production system and are strictly off-limits from modification, deletion, or dependency changes:

- **Production Backend Directory:** `A:\VIT-3rd-sem\3rd_sem\EDI_Accion_lab\app\`
- **Production Frontend Directory:** `A:\VIT-3rd-sem\3rd_sem\EDI_Accion_lab\static\`
- **Production Virtual Environment:** `A:\VIT-3rd-sem\3rd_sem\EDI_Accion_lab\venv\` (Python 3.10 with Whisper, Pyannote 3.1, Groq LLM, FastAPI)
- **Production Requirements Files:** `requirements.txt`, `requirements-simple.txt`
- **Production Environment Config:** `.env`, `.env.example`
- **Production Hugging Face Model Caches:**
  - `models--pyannote--speaker-diarization-3.1`
  - `models--pyannote--segmentation-3.0`
  - `models--pyannote--wespeaker-voxceleb-resnet34-LM`
  - `models--Systran--faster-whisper-base.en`
  - `models--Systran--faster-whisper-small.en`

---

## 2. Identified MOSS Experimental Artifacts & Disk Usage

All MOSS experimentation was confined to test folders and a dedicated Hugging Face hub cache entry. No MOSS packages were installed in the production `venv`.

| Component / Artifact | Exact Location | File Count | Size (MB) | Size (GB) | Status / Action Plan |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **MOSS Virtual Environment** | `tests\moss_env\` | 37,057 | 5,266.54 MB | 5.143 GB | Marked for deletion |
| **MOSS Hybrid Experiment** | `tests\moss_hybrid\` | 243 | 5.73 MB | 0.006 GB | Marked for deletion |
| **MOSS Profile Env (Step 1)** | `tests\moss_profile_env\` | 30,056 | 9,971.26 MB | 9.738 GB | Marked for deletion |
| **MOSS Profile Env Clean** | `tests\moss_profile_env_clean\` | 48,850 | 5,564.39 MB | 5.434 GB | Marked for deletion |
| **MOSS Realtime POC** | `tests\moss_realtime\` | 80 | 61.83 MB | 0.060 GB | Marked for deletion |
| **MOSS Test Repo/Harness** | `tests\moss_test\` | 123 | 0.99 MB | 0.001 GB | Marked for deletion |
| **Hugging Face MOSS Cache** | `~/.cache/huggingface/hub/models--OpenMOSS-Team--MOSS-Transcribe-Diarize` | 36 | 3,496.34 MB | 3.414 GB | Marked for deletion |
| **TOTAL MOSS FOOTPRINT** | — | **116,445** | **24,367.08 MB** | **23.796 GB** | **To be safely removed** |

---

## 3. Git Status Before Cleanup

```text
 M app/api/live_routes.py
 M app/api/routes.py
 M app/audio/preprocessing.py
 M app/main.py
 M app/services/diarization.py
 M app/services/llm_correction.py
 M app/services/merge.py
 M app/services/roles.py
 M app/services/text_cleanup.py
 M app/transcription/transcript_formatter.py
 M app/transcription/whisper_service.py
 M output/temp_processed.wav
 M static/index.html
 M static/transcript.html
 M tests/test_swap_endpoint.py
?? Port
?? app/services/alignment.py
?? app/services/pipeline.py
?? app/services/utterance_manager.py
?? tests/moss_env/
?? tests/moss_hybrid/
?? tests/moss_profile_env/
?? tests/moss_profile_env_clean/
?? tests/moss_realtime/
?? tests/moss_test/
?? tests/realtime_stt_eval/
?? tests/test_alignment.py
?? tests/test_utterance_manager.py
?? tests/test_window_refiner.py
```

*Note: All MOSS directories are untracked (`??`). Production core files will remain untouched during the transition.*

---

## 4. Deletion Safety Rules Verified

1. **Production Isolation:** No MOSS dependency or file exists inside `app/`, `static/`, or `venv/`.
2. **Selective Hugging Face Hub Purge:** Only `models--OpenMOSS-Team--MOSS-Transcribe-Diarize` will be removed from `~/.cache/huggingface/hub/`. All `pyannote` and `faster-whisper` models will remain untouched.
3. **Verification Command:** Re-evaluating disk space post-deletion in Phase 1 to verify that exactly ~23.8 GB is reclaimed.
