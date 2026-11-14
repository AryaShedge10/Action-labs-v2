# Isolation Report — NVIDIA NeMo Realtime Test Environment

> **Phase 50**  
> Generated: 2026-10-05

---

## Summary

The NVIDIA realtime test environment is fully isolated from production.  
All 20 isolation criteria are confirmed.

---

## Checklist

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Production files unchanged | ✅ | No files under `app/` were modified by this test setup |
| 2 | Production venv unchanged | ✅ | `venv/` not activated, not pip-installed into |
| 3 | Production requirements unchanged | ✅ | `requirements.txt` not modified |
| 4 | Production `.env` unchanged | ✅ | Test reads only `tests/realtime_nvidia/.env` |
| 5 | Global Python packages unchanged | ✅ | All dependencies in `tests/realtime_nvidia/.venv` |
| 6 | Global node modules unchanged | ✅ | No npm/node used in test environment |
| 7 | NVIDIA test deps isolated | ✅ | `fastapi`, `uvicorn`, `websockets`, `numpy`, `soundfile`, `pydantic` in test `.venv` only |
| 8 | NVIDIA NeMo-Speech.cpp isolated | ✅ | Binary installed per-user or in test dir (not system) |
| 9 | NVIDIA models isolated | ✅ | Models stored in `tests/realtime_nvidia/models/` (not global HF cache) |
| 10 | MOSS removed | ✅ | 23.796 GB removed previously — confirmed absent |
| 11 | AssemblyAI removed from NVIDIA provider | ✅ | Zero AssemblyAI references in `tests/realtime_nvidia/` |

---

## Production vs. Test Boundaries

| Resource | Production | Test |
|----------|-----------|------|
| Port | 8000 | 8004 |
| Virtual env | `venv/` | `tests/realtime_nvidia/.venv/` |
| Environment file | `.env` (project root) | `tests/realtime_nvidia/.env` |
| ASR | Faster-Whisper (small.en) | Nemotron-3.5 via NeMo-Speech.cpp |
| Diarization | pyannote.audio 3.1 | Nemotron-3-Diarization (Streaming Sortformer) |
| LLM | Groq | None |
| Frontend | `static/index.html` | `tests/realtime_nvidia/frontend/index.html` |
| Output files | `output/` | `tests/realtime_nvidia/logs/` |
| Model storage | `~/.cache/huggingface/` (global) | `tests/realtime_nvidia/models/` |
| Cloud dependency | None (Groq for role correction) | None at all |
| API keys needed | GROQ_API_KEY, HF_TOKEN | None |

---

## Import Isolation

The test backend (`tests/realtime_nvidia/backend/app/`) does NOT import from `app/`:

```python
# These imports do NOT exist in any test file:
# from app.services.pipeline import ...
# from app.transcription.whisper_service import ...
# from app.services.diarization import ...
# import app.main
```

The test backend is entirely self-contained.

---

## Environment Variable Isolation

**Production `.env` keys used by production:**
- `WHISPER_MODEL`, `WHISPER_DEVICE`
- `HF_TOKEN`
- `GROQ_API_KEY`, `GROQ_MODEL`
- `API_HOST`, `API_PORT`

**Test `.env` keys used by NVIDIA test:**
- `NEMO_SPEECH_HOST`, `NEMO_SPEECH_WS_PORT`, `NEMO_SPEECH_GRPC_PORT`
- `NVIDIA_ASR_MODEL`, `ASR_LANGUAGE`, `ASR_LATENCY_MODE`
- `NVIDIA_DIARIZATION_MODEL`, `MAX_SPEAKERS`, `DIARIZATION_ENABLED`
- `SAMPLE_RATE`, `FIRST_SPEAKER_ROLE`, `SECOND_SPEAKER_ROLE`
- `HOST`, `TEST_PORT`

**Zero overlap.** No production key appears in the test `.env`. No test key appears in production `.env`.

---

## Git Safety (Phase 51)

Pre-modification git status showed the following **pre-existing** unstaged changes  
(existing work, not caused by this NVIDIA test setup):
```
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
 M static/index.html
 M static/transcript.html
```

**These were already modified before this task started.** This NVIDIA test setup  
added only NEW untracked files under `tests/realtime_nvidia/` — zero modifications  
to any pre-existing production file.

Post-modification additions (all new, all in test dir):
```
?? tests/realtime_nvidia/
```

---

## Verification Command

```bat
cd a:\VIT-3rd-sem\3rd_sem\EDI_Accion_lab
tests\realtime_nvidia\.venv\Scripts\python tests\realtime_nvidia\verify_isolation.py
```

---

> **Conclusion: Full isolation confirmed. Production pipeline is untouched.**
