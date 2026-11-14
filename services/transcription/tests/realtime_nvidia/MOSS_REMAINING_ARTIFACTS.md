# MOSS Remaining Artifacts — Phase 1 Verification

> Generated: 2026-10-05  
> Scan scope: `tests/` directory + `~/.cache/huggingface/hub/`

---

## Result: MOSS IS FULLY ABSENT

No MOSS artifacts were found anywhere in the workspace or HuggingFace model cache.

---

## Scan Performed

### Test Directories Checked

| Path | Status |
|------|--------|
| `tests/moss_env/` | ABSENT — verified not present |
| `tests/moss_hybrid/` | ABSENT — verified not present |
| `tests/moss_profile_env/` | ABSENT — verified not present |
| `tests/moss_profile_env_clean/` | ABSENT — verified not present |
| `tests/moss_realtime/` | ABSENT — verified not present |
| `tests/moss_test/` | ABSENT — verified not present |

### HuggingFace Cache Checked

| Path | Status |
|------|--------|
| `~/.cache/huggingface/hub/models--OpenMOSS-Team--MOSS-Transcribe-Diarize` | ABSENT — verified not present |
| `~/.cache/huggingface/hub/` (all dirs scanned for MOSS-pattern names) | No MOSS directories found |

---

## Previous MOSS Cleanup (Already Done)

As documented in `tests/realtime_stt_eval/reports/ASSEMBLYAI_REALTIME_REPORT.md`, the MOSS cleanup was completed prior to the AssemblyAI POC:

| Previously Deleted Path | Disk Reclaimed |
|------------------------|----------------|
| `tests/moss_env/` (37,057 files) | 5,266.54 MB |
| `tests/moss_hybrid/` (243 files) | 5.73 MB |
| `tests/moss_profile_env/` (30,056 files) | 9,971.26 MB |
| `tests/moss_profile_env_clean/` (48,850 files) | 5,564.39 MB |
| `tests/moss_realtime/` (80 files) | 61.83 MB |
| `tests/moss_test/` (123 files) | 0.99 MB |
| `~/.cache/huggingface/.../MOSS-Transcribe-Diarize` | 3,496.34 MB |
| **Total** | **24,367.08 MB (23.796 GB)** |

---

## Nothing to Delete

MOSS is completely gone. No deletions were performed in this phase.

---

> **Conclusion: MOSS cleanup from the previous phase remains intact. Zero MOSS artifacts found.**
