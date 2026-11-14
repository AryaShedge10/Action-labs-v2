# Disk Usage Report — NVIDIA NeMo Realtime Test

> **Phase 49**  
> Generated: 2026-10-05

---

## Before State (AssemblyAI POC)

The AssemblyAI test environment (`tests/realtime_stt_eval/`) already existed when this NVIDIA migration started.

| Item | Size |
|------|------|
| `tests/realtime_stt_eval/.venv/` | ~25 MB (minimal: fastapi, uvicorn, websockets, numpy) |
| `tests/realtime_stt_eval/backend/` (code only) | < 1 MB |
| `tests/realtime_stt_eval/frontend/` | < 100 KB |
| `tests/realtime_stt_eval/recordings/` | ~2 MB |
| `tests/realtime_stt_eval/logs/` | < 1 MB |
| **AssemblyAI test subtotal** | **~28 MB** |

AssemblyAI-specific code removed: ~9 KB (the `AssemblyAIRealtimeProvider` class body).

---

## MOSS Artifacts (Previously Removed)

Already cleaned before this task. Confirmed absent:

| Previously Deleted | Disk Reclaimed |
|-------------------|----------------|
| `tests/moss_env/` | 5,266 MB |
| `tests/moss_hybrid/` | 5.7 MB |
| `tests/moss_profile_env/` | 9,971 MB |
| `tests/moss_profile_env_clean/` | 5,564 MB |
| `tests/moss_realtime/` | 61 MB |
| `tests/moss_test/` | 0.9 MB |
| HF MOSS model cache | 3,496 MB |
| **MOSS Total** | **24,367 MB (23.8 GB)** |

---

## After State (NVIDIA POC)

### Python Environment (`tests/realtime_nvidia/.venv/`)
Same minimal package set as AssemblyAI test venv.  
**No torch, no NeMo Python, no pyannote — all inference in native binary.**

| Package | Size estimate |
|---------|--------------|
| fastapi + starlette | ~4 MB |
| uvicorn | ~2 MB |
| websockets | ~1 MB |
| pydantic + pydantic-core | ~10 MB |
| numpy | ~20 MB |
| soundfile + libsndfile | ~5 MB |
| httpx + certifi | ~3 MB |
| python-dotenv, click, etc. | ~2 MB |
| **Test venv total** | **~47 MB** |

### Source Code (`tests/realtime_nvidia/backend/` + `frontend/`)
| File | Size |
|------|------|
| `backend/app/main.py` | ~8 KB |
| `backend/app/provider.py` | ~9 KB |
| `backend/app/session_manager.py` | ~10 KB |
| `backend/app/models.py` | ~2 KB |
| `backend/app/config.py` | ~3 KB |
| `frontend/index.html` | ~7 KB |
| scripts, docs, reports | ~50 KB |
| **Source total** | **< 100 KB** |

### NVIDIA Models (after download)

> Models are downloaded when `nemo-speech pull` is run for the first time.  
> Stored in `tests/realtime_nvidia/models/` — NOT in global HF cache.

| Model | Estimated Size |
|-------|---------------|
| `nvidia/nemotron-3.5-asr-streaming-0.6b` (fp16) | ~1.2 GB |
| `nvidia/Nemotron-3-Diarization` | ~0.5 GB |
| **Models total** | **~1.7 GB** |

(Actual sizes depend on NeMo-Speech.cpp GGUF format used.)

---

## Total NVIDIA POC Footprint

| Component | Size |
|-----------|------|
| Test venv | ~47 MB |
| Source code + docs | < 1 MB |
| NVIDIA models (after download) | ~1.7 GB |
| Logs / recordings | < 10 MB |
| **Total** | **~1.75 GB** |

---

## Comparison

| Environment | Disk Used |
|-------------|----------|
| MOSS (deleted) | 23.8 GB |
| AssemblyAI POC | ~28 MB (no local models) |
| NVIDIA NeMo POC | ~1.75 GB (with local models) |

The NVIDIA POC requires ~1.7 GB for models but is **14x smaller than MOSS** and runs completely offline after download.

---

> **Models download to `tests/realtime_nvidia/models/` only.**  
> **No global HuggingFace cache pollution.**
