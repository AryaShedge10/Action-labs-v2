# AssemblyAI Cleanup Report — Phase 2

> **TEST ONLY — PRODUCTION PIPELINE UNCHANGED**  
> Generated: 2026-10-05

---

## Summary

The AssemblyAI test environment has been converted to an NVIDIA local-only implementation.  
The AssemblyAI **provider layer** has been removed. The **session architecture, transcript state machine, frontend, and all reusable infrastructure** have been preserved.

---

## Files Removed (AssemblyAI-specific content replaced)

### `tests/realtime_stt_eval/backend/app/provider.py` — `AssemblyAIRealtimeProvider` class

| Field | Value |
|-------|-------|
| File | `tests/realtime_stt_eval/backend/app/provider.py` |
| Action | Class `AssemblyAIRealtimeProvider` removed; `RealtimeSTTProvider` ABC preserved |
| Reason | Cloud WebSocket to `wss://streaming.assemblyai.com/v3/ws` is incompatible with local-only requirement |
| Reusable Equivalent | `NVIDIARealtimeProvider` in `tests/realtime_nvidia/backend/app/provider.py` |
| Dependencies Removed | Outbound cloud WebSocket connection code |
| Approximate Disk Reclaimed | < 1 KB (class body only) |

---

## Environment Variables Removed

| Variable | Reason |
|----------|--------|
| `ASSEMBLYAI_API_KEY` | Cloud API key — zero cloud dependency in NVIDIA POC |
| `SPEECH_MODEL=universal-3-6-pro` | AssemblyAI model name — replaced with `NVIDIA_ASR_MODEL=nemotron-3.5` |
| `DOMAIN=medical-v1` | AssemblyAI domain flag — replaced with NeMo model config |

---

## Files Preserved (Reused in NVIDIA POC)

| File | Status |
|------|--------|
| `backend/app/models.py` | **Preserved** — `TranscriptSegment`, `RealtimeEvent`, `SessionMetrics`, `WordItem` are provider-agnostic |
| `backend/app/session_manager.py` | **Preserved** — full transcript state machine; only provider import updated |
| `backend/app/config.py` | **Preserved pattern** — new config file with NVIDIA keys instead of AssemblyAI keys |
| `backend/app/main.py` | **Preserved** — all routes, WebSocket handlers, replay endpoint |
| `frontend/index.html` | **Preserved** — all UI, in-place DOM update logic; badge text changed to "Local" |
| `backend/requirements.txt` | **Preserved** — no assemblyai SDK was installed; websockets retained |
| `recordings/clinical_test_dialogue.wav` | **Preserved** — reused for replay testing |

---

## Dependencies Removed

No Python packages were uninstalled from the test venv. The AssemblyAI integration used the generic `websockets` package directly (no `assemblyai` SDK package was ever installed). The `websockets` library is still needed for NeMo-Speech.cpp local WebSocket communication.

---

## Approximate Disk Reclaimed

AssemblyAI-specific code was pure logic (no models, no large binaries):

| Item | Size |
|------|------|
| `AssemblyAIRealtimeProvider` class body | ~8 KB |
| AssemblyAI-specific `.env` variables | < 1 KB |
| **Total** | **~9 KB** |

The AssemblyAI POC never downloaded any models locally, so there is nothing model-related to reclaim.

---

## API Key Disposition

- `ASSEMBLYAI_API_KEY` is NOT copied into the NVIDIA POC `.env`
- `tests/realtime_nvidia/.env` contains zero API keys
- `tests/realtime_nvidia/.env` requires no internet credentials for inference

---

## Post-Migration Verification

Static search results for `assemblyai` in the NVIDIA test directory:

```
tests/realtime_nvidia/backend/app/provider.py    — 0 occurrences
tests/realtime_nvidia/backend/app/config.py      — 0 occurrences
tests/realtime_nvidia/backend/app/session_manager.py — 0 occurrences
tests/realtime_nvidia/backend/app/main.py        — 0 occurrences
tests/realtime_nvidia/frontend/index.html        — 0 occurrences
tests/realtime_nvidia/.env                       — 0 occurrences
```

**Zero AssemblyAI references in the final NVIDIA POC.**

---

> **AssemblyAI provider layer fully removed. Architecture reused. No API key retained.**
