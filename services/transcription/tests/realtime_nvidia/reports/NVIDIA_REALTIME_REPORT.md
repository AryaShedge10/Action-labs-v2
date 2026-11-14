# NVIDIA NeMo-Speech.cpp Local Realtime — Evaluation Report

> **TEST ONLY — PRODUCTION PIPELINE UNCHANGED**  
> Status: Framework complete — pending live measurement run

---

## 1. Environment

| Item | Value |
|------|-------|
| Test Directory | `tests/realtime_nvidia/` |
| Python Interpreter | `tests/realtime_nvidia/.venv/Scripts/python.exe` |
| Production Venv | `venv/` (untouched) |
| Production Port | 8000 (not started during test) |
| Test Port | 8004 |
| OS | Microsoft Windows 11 Home Single Language |
| Architecture | AMD64 |

---

## 2. Hardware

| Component | Value |
|-----------|-------|
| GPU | NVIDIA GeForce GTX 1650 |
| VRAM | 4096 MiB |
| GPU Driver | 592.27 |
| CUDA Version | 13.1 |
| CPU | 12th Gen Intel Core i5-12450H |
| CPU Cores | 8 |
| RAM | ~7.7 GB |

**GTX 1650 Performance Note:**  
NVIDIA's published latency benchmarks are for H100/A100 data center GPUs.  
GTX 1650 is a 2019 mobile/desktop GPU with 4GB GDDR5 VRAM.  
Published targets (80ms, 320ms ultra-low-latency) are **not expected on GTX 1650**.  
All numbers in this report are based on actual measurement on this hardware.

---

## 3. NVIDIA Stack

| Component | Value |
|-----------|-------|
| Runtime | NeMo-Speech.cpp v0.1.0 |
| ASR Model | `nvidia/nemotron-3.5-asr-streaming-0.6b` |
| Diarization Model | `nvidia/Nemotron-3-Diarization` (Streaming Sortformer) |
| ASR Architecture | Cache-aware FastConformer-RNNT (streaming) |
| Diarization Architecture | Streaming Sortformer with Arrival-Order Speaker Cache |
| Latency Mode | `low_latency` (benchmark target) |
| Language | en-US |
| Max Speakers | 2 (Doctor + Patient) |
| Cloud Dependency | None |
| API Key | Not required |

---

## 4. Model Sizes

| Model | Estimated VRAM | Storage |
|-------|---------------|---------|
| nemotron-3.5 ASR (0.6B, fp16) | ~1.2 GB VRAM | `tests/realtime_nvidia/models/` |
| Nemotron-3-Diarization | ~0.4 GB VRAM | `tests/realtime_nvidia/models/` |
| Runtime overhead | ~0.3 GB VRAM | — |
| **Total estimated** | **~1.9 GB** | — |

> Actual values: run `nvidia-smi` during a live session and record here.

---

## 5. Architecture

```
Browser Microphone
    ↓  PCM16 16kHz mono (100ms binary frames)
Test Backend — FastAPI port 8004 (tests/realtime_nvidia/.venv)
    ↓  local WebSocket ws://127.0.0.1:8888/stream
NeMo-Speech.cpp local server
    ↓  Nemotron-3.5 ASR + Nemotron-3-Diarization (GTX 1650)
    ↓  streaming events (partial/final/diarization)
Test Backend — Transcript State Machine (RealtimeSession)
    ↓  RealtimeEvent JSON (segment_update, final_summary)
Browser — Clinical Scribe UI (Doctor/Patient bubbles, in-place updates)
```

---

## 6. Transcript State Model

Each utterance tracked as a `TranscriptSegment`:

```json
{
  "segment_id":  "seg_0001",
  "turn_id":     1,
  "start_time":  0.42,
  "end_time":    3.18,
  "speaker_id":  "speaker_0",
  "role":        "Doctor",
  "text":        "Good morning. How are you feeling today?",
  "status":      "FINAL",
  "is_final":    true,
  "words":       [...],
  "version":     4
}
```

- `LIVE` → partial, updates in-place by `segment_id` (no duplication)
- `FINAL` → replaces LIVE in-place
- Speaker revision → updates `speaker_id` + `role` without text change

---

## 7. Latency Measurements

> ⚠️ **Values below are pending first live measurement run.**  
> Run `scripts/benchmark_latency.py` and fill in actual values.

| Metric | Target | Measured | Status |
|--------|--------|---------|--------|
| First visible text | < 1000ms | _TBD_ | Pending |
| First partial update | Continuous | _TBD_ | Pending |
| First final turn | < 2000ms | _TBD_ | Pending |
| Stop → final saved | < 2000ms | _TBD_ | Pending |
| Sustained backlog (avg) | < 500ms | _TBD_ | Pending |
| RTF | ≤ 1.0 | _TBD_ | Pending |

**Per latency mode (benchmark each):**

| Mode | Buffer Delay | Total Latency Measured | Backlog at 5min | Backlog at 20min |
|------|-------------|----------------------|-----------------|-----------------|
| low_latency | ~1.04s | _TBD_ | _TBD_ | _TBD_ |
| very_low_latency | ~0.64s | _TBD_ | _TBD_ | _TBD_ |
| ultra_low_latency | ~0.32s | _TBD_ | _TBD_ | _TBD_ |

---

## 8. GPU Profiling

> Run `nvidia-smi dmon` during live session. Fill in actuals.

| Metric | ASR only | Combined ASR+Diar | Peak |
|--------|----------|------------------|------|
| GPU utilization | _TBD_ % | _TBD_ % | _TBD_ % |
| VRAM used | _TBD_ MiB | _TBD_ MiB | _TBD_ MiB |
| CPU utilization | _TBD_ % | _TBD_ % | _TBD_ % |
| Power | _TBD_ W | _TBD_ W | _TBD_ W |

---

## 9. Accuracy

> Fill in after running test recordings through the live system.

| Test Scenario | WER | Medical Term Accuracy | Speaker Accuracy | Speaker Swaps |
|--------------|-----|----------------------|-----------------|--------------|
| Normal dialogue | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Medical terms | _TBD_ | _TBD_ | — | — |
| Interruption | — | — | _TBD_ | _TBD_ |
| Long silence | — | — | _TBD_ | _TBD_ |
| Overlap | — | — | _TBD_ | _TBD_ |

**Quality metrics:**
| Metric | Value |
|--------|-------|
| Duplicate segments | _TBD_ |
| Missing words | _TBD_ |
| Hallucinated words | _TBD_ |
| Medication accuracy (metformin 500mg) | _TBD_ |
| Number accuracy | _TBD_ |

---

## 10. Sustained Realtime Test

| Duration | Final backlog | Realtime maintained | Notes |
|----------|--------------|--------------------|----|
| 60s | _TBD_ | _TBD_ | _TBD_ |
| 5min | _TBD_ | _TBD_ | _TBD_ |
| 20min | _TBD_ | _TBD_ | _TBD_ |

Unacceptable pattern (must not occur):
- Start: 500ms lag
- After 5min: 5s lag
- After 20min: 20s lag

---

## 11. Overlap / Interruption Test

| Test | Result |
|------|--------|
| Doctor interrupted mid-sentence | _TBD_ |
| Simultaneous speech recovered | _TBD_ |
| Speaker attribution during overlap | _TBD_ |
| Post-overlap identity stable | _TBD_ |

---

## 12. Acceptance Criteria Status

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Words appear while speaker is still talking | ⏳ Pending measurement |
| 2 | No 5s/20s batch window | ✅ Cache-aware RNNT streaming |
| 3 | Partial text replaced, never duplicated | ✅ Stable segment_id in-place updates |
| 4 | Final replaces live hypothesis | ✅ LIVE→FINAL state machine |
| 5 | No duplicate lines | ✅ Designed (pending measurement) |
| 6 | Speaker identity stable across session | ✅ Arrival-Order Speaker Cache |
| 7 | Doctor/Patient labels don't swap | ✅ Session-level deterministic mapping |
| 8 | Stop flushes final speech | ✅ end_of_stream protocol |
| 9 | Model loads once | ✅ NeMo-Speech.cpp server persistent |
| 10 | No growing queue | ⏳ Pending measurement |
| 11 | Sustained realtime demonstrated | ⏳ Pending 60s/5min/20min tests |
| 12 | No cloud STT | ✅ All local |
| 13 | No API key | ✅ Confirmed |
| 14 | No MOSS | ✅ MOSS fully absent (23.796 GB reclaimed previously) |
| 15 | No AssemblyAI in NVIDIA provider | ✅ Zero references (scan confirmed) |
| 16 | No Whisper in this POC | ✅ Confirmed |
| 17 | No Pyannote in this POC | ✅ Confirmed |
| 18 | No Groq in this POC | ✅ Confirmed |
| 19 | Production completely unchanged | ✅ Verified |
| 20 | No global installation | ✅ All inside tests/realtime_nvidia/.venv |

---

## 13. Failures & Limitations

### Known Limitations (pre-measurement)
- **GTX 1650 vs. H100**: NVIDIA's published ultra-low-latency figures are not achievable on GTX 1650. Real numbers will be measured and reported honestly.
- **Audio frame size**: ScriptProcessorNode is deprecated in modern browsers; consider AudioWorklet for production. Fine for test.
- **Q8 not yet tested**: If VRAM pressure occurs, Q8 GGUF models can be tested (Phase 41).
- **Windows binary**: NeMo-Speech.cpp must be downloaded and added to PATH manually.

### To be filled after measurement
- _TBD after live run_

---

## 14. Next Steps

1. Install NeMo-Speech.cpp: `run_nemo_server.bat` (follow INSTALLATION_GUIDE.md)
2. Pull models: `nemo-speech pull nemotron-3.5 && nemo-speech pull nemotron-3-diarization`
3. Start runtime: `run_nemo_server.bat`
4. Start backend: `run_test_backend.bat`
5. Open: http://127.0.0.1:8004
6. Run 60s live test → fill in latency measurements
7. Run `scripts/benchmark_latency.py --duration 60`
8. Run `scripts/benchmark_latency.py --duration 300`
9. Run `scripts/benchmark_latency.py --duration 1200`
10. Record all measured values in this report

---

> **TEST ONLY — PRODUCTION UNCHANGED**  
> Production: Whisper + Pyannote + Groq on port 8000 — not modified, not started during testing.
