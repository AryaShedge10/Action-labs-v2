# NVIDIA Runtime Version Record — Phase 6

> Generated: 2026-10-05  
> Machine: NVIDIA GeForce GTX 1650 / Windows 11 / CUDA 13.1

---

## Hardware

| Component | Detected Value |
|-----------|---------------|
| GPU | NVIDIA GeForce GTX 1650 |
| VRAM | 4096 MiB (4 GB) |
| GPU Driver | 592.27 |
| CUDA Version | 13.1 |
| CPU | 12th Gen Intel Core i5-12450H |
| CPU Cores | 8 |
| RAM | ~7.7 GB |
| OS | Microsoft Windows 11 Home Single Language |
| Architecture | AMD64 |

**Important:** The GTX 1650 (4GB VRAM) is a mid-range consumer GPU from 2019.  
NVIDIA's published latency benchmarks (80ms, 320ms, etc.) are for H100/A100 class hardware.  
Real-world performance on GTX 1650 will be meaningfully higher latency.  
Do not compare directly against NVIDIA's published figures — benchmark this actual machine.

---

## NeMo-Speech.cpp

| Item | Value |
|------|-------|
| Runtime | NeMo-Speech.cpp |
| Container version (NGC) | 0.1.0 |
| Published: | June 2026 |
| Description | Lightweight C++ inference runtime for NVIDIA speech models (ggml-based) |
| Source | https://catalog.ngc.nvidia.com/orgs/nvidia/-/containers/nemo-speech.cpp/0.1.0 |
| GitHub | https://github.com/NVIDIA/NeMo-Speech.cpp |
| Backend | ggml (CPU/CUDA/Vulkan) |
| Python dependency for inference | None (native binary) |
| Realtime WebSocket | Yes — port 8888 |
| gRPC endpoint | Yes — port 50051 |
| Windows support | Yes (binary release) |

---

## ASR Model

| Item | Value |
|------|-------|
| Model short name | nemotron-3.5 |
| Full HuggingFace ID | nvidia/nemotron-3.5-asr-streaming-0.6b |
| Architecture | Cache-aware FastConformer-RNNT |
| Parameters | 0.6 billion |
| Release date | June 4, 2026 |
| Languages | 40+ (language-ID prompt conditioned) |
| Language selected | en-US |
| Streaming | Yes (cache-aware state persists between frames) |
| Latency modes | low_latency (~1.04s buffer), very_low_latency (~0.64s), ultra_low_latency (~0.32s) |
| Punctuation/capitalization | Yes (native, no post-processing) |
| Storage | tests/realtime_nvidia/models/ |
| Install command | `nemo-speech pull nemotron-3.5` |

**Note on cache-aware architecture:**  
The model maintains ASR state across audio frames — it does NOT reset every N seconds.  
Each frame extends the previous state. This is the correct streaming architecture per Phase 10.  
No rolling-window batch inference is used.

---

## Diarization Model

| Item | Value |
|------|-------|
| Model short name | nemotron-3-diarization |
| Full HuggingFace ID | nvidia/Nemotron-3-Diarization |
| Architecture | Streaming Sortformer (Arrival-Order Speaker Cache) |
| Release | September 2026 update |
| Streaming | Yes (runs in parallel with ASR per Phase 4 NVIDIA docs) |
| Speaker cache | Arrival-Order — speaker identity maintained across the session |
| Max speakers | 2 (configured for Doctor + Patient) |
| Storage | tests/realtime_nvidia/models/ |
| Install command | `nemo-speech pull nemotron-3-diarization` |

**Note on Arrival-Order Speaker Cache:**  
Speaker identities persist throughout the session — the diarizer does not reassign  
speaker_0 and speaker_1 independently per audio chunk. This is the correct architecture  
per Phase 23 and specifically addresses the previous MOSS speaker-swap failure mode.

---

## Latency Mode Reference

| Mode | Buffer Delay | Notes |
|------|-------------|-------|
| `low_latency` | ~1.04s | **Recommended start for GTX 1650** — compute budget has margin |
| `very_low_latency` | ~0.64s | May work on GTX 1650 — benchmark before switching |
| `ultra_low_latency` | ~0.32s | May exceed GTX 1650 compute budget — benchmark first |

These are audio buffer delays only. Total latency = buffer + model compute + event propagation + UI update.  
Benchmark all three modes on this machine before selecting one (Phase 13, Phase 37).

---

## Model File Locations

After pulling models, expected structure:

```
tests/realtime_nvidia/
└── models/
    ├── nemotron-3.5/
    │   └── *.gguf (or NeMo-Speech.cpp internal format)
    └── nemotron-3-diarization/
        └── *.gguf (or NeMo-Speech.cpp internal format)
```

Models are stored inside the test directory to avoid polluting the global HuggingFace cache.

---

## Version Determination Method

NeMo-Speech.cpp version `0.1.0` is the current NGC release as of October 2026.  
To verify the exact version after installation:

```bat
nemo-speech --version
```

Record the exact output in this file when running on the target machine.

---

## VRAM Budget Estimate (GTX 1650 — 4GB)

| Component | Estimated VRAM |
|-----------|---------------|
| Nemotron-3.5 ASR (0.6B, fp16) | ~1.2 GB |
| Nemotron-3-Diarization | ~0.4 GB |
| Runtime overhead | ~0.3 GB |
| Available headroom | ~2.1 GB |
| **Total estimated** | **~1.9 GB active** |

This estimate suggests both models should fit within the GTX 1650's 4GB VRAM.  
Q8 quantization is available if VRAM pressure becomes an issue (Phase 41).  
Benchmark actual VRAM usage with nvidia-smi during a live session.

---

> **Record actual measured values in reports/NVIDIA_REALTIME_REPORT.md after running live tests.**
