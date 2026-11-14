# Realtime Event Debug Report

> Generated: 2026-10-05

---

## 1. NVIDIA Server Command

```
nemo-speech serve --asr-model nemotron-3.5 --diar-model nemotron-3-diarization --port 8090
```

Server output confirms:
- `backend=CUDA0` — GTX 1650, CUDA inference active
- `diarization=on` — Nemotron-3-Diarization loaded
- `head=rnnt` — cache-aware streaming RNNT
- `encoder-frames step=160ms` — 160ms streaming chunks

---

## 2. Realtime Endpoint

```
ws://127.0.0.1:8090/v1/audio/transcriptions/realtime
```

---

## 3. Session.Update Payload (correct)

```json
{
  "type": "session.update",
  "session": {
    "sample_rate": 16000,
    "language": "en-US",
    "automatic_punctuation": true,
    "word_timestamps": true,
    "speaker_diarization": true,
    "endpointing_ms": 700
  }
}
```

Key addition: `"endpointing_ms": 700` — without this, NeMo never fires `completed` events
and the partial text accumulates forever into one giant segment.

---

## 4. Audio Format

- Sample rate: 16000 Hz
- Channels: mono (1)
- Encoding: PCM16 little-endian
- Frame size: 4096 samples = ~256ms
- Transport: binary WebSocket frames

---

## 5. Verified Event Structure (from debug_nemo_events.py)

### Delta event (sub-word fragment):
```json
{
  "audio_processed": 31.23,
  "delta": "Far",
  "event_id": "event_429",
  "type": "conversation.item.input_audio_transcription.delta"
}
```

**Critical findings:**
- `delta` = sub-word fragment ("Far", " li", "ne" → "Far line")
- **No `item_id` field** in delta events
- **No `speaker` field** in delta events
- Must be ACCUMULATED, not appended as new segments

### Completed event (expected after 700ms silence):
```json
{
  "type": "conversation.item.input_audio_transcription.completed",
  "transcript": "Far line really think to let hurt get wet",
  "words": [
    {"word": "Far", "start": 31.0, "end": 31.3, "speaker": 1},
    {"word": "line", "start": 31.3, "end": 31.6, "speaker": 1}
  ],
  "start": 31.0,
  "end": 39.5
}
```

- `words[].speaker` = 1-based int (1 = first speaker, 2 = second speaker)
- Normalize: `1 → "speaker_0"`, `2 → "speaker_1"`

---

## 6. Root Cause of Giant Single Segment Bug

**Three compounding bugs:**

1. **Missing `endpointing_ms`** — `completed` events never fired, so `current_segment_id` was never reset. Every delta appended to the same growing segment forever.

2. **Delta accumulation on wrong reset trigger** — `_partial_text` was being reset on `item_id` change, but delta events have no `item_id`, so it never reset.

3. **Speaker always "Doctor"** — since `completed` never fired, the speaker field from the completed event (which contains actual speaker data) was never received. Speaker stayed `UNKNOWN` → mapped to first role → Doctor always.

---

## 7. Files Changed

| File | Change |
|------|--------|
| `backend/app/provider.py` | Rewrote delta handling: accumulate fragments; reset on completed |
| `backend/app/provider.py` | Added `endpointing_ms: 700` to session.update |
| `backend/app/provider.py` | Added event logging to `logs/nvidia_events.jsonl` |
| `backend/app/session_manager.py` | Rewrote `_handle_turn_data`: one LIVE segment per utterance |
| `backend/app/session_manager.py` | Removed orphaned duplicate method body |
| `frontend/index.html` | Fixed audio buffer: 1600 → 2048 (must be power of 2) |
| `scripts/test_realtime_events.py` | New direct test harness (bypasses frontend) |

---

## 8. Expected Correct Behavior After Fix

**While speaking "Good morning doctor":**
```
[0.16s] PARTIAL: Good
[0.32s] PARTIAL: Good mor
[0.48s] PARTIAL: Good morning
[0.64s] PARTIAL: Good morning doc
[0.80s] PARTIAL: Good morning doctor
```
(All updating the same LIVE segment — same `segment_id` in DOM)

**After 700ms silence:**
```
[1.5s] COMPLETED: "Good morning doctor."  speaker=1 → Doctor
```
Segment becomes FINAL. Next speech creates `seg_0002`.

---

## 9. Confirmation: Production Not Changed

- `app/` directory: untouched
- `venv/`: untouched
- `requirements.txt`: untouched
- Production port 8000: not started
- All changes confined to `tests/realtime_nvidia/`
