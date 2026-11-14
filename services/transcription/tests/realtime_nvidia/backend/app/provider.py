"""
NVIDIA NeMo-Speech.cpp v0.2.0 Realtime Provider
tests/realtime_nvidia/backend/app/provider.py

Verified protocol (from debug_nemo_events.py):
  CONNECT  -> server sends session.created
  CLIENT   -> session.update  (before any audio)
  CLIENT   -> binary PCM16 little-endian frames (continuous)
  SERVER   -> delta events    (sub-word fragments, accumulate for live display)
  SERVER   -> completed events (final utterance after endpointing silence)
  CLIENT   -> input_audio_buffer.commit  (graceful stop)
  SERVER   -> input_audio_buffer.committed  (all done)

Delta fields (verified):
  type: "conversation.item.input_audio_transcription.delta"
  delta: "Good"  (sub-word fragment — NO item_id)
  audio_processed: 3.97  (seconds of audio sent so far)
  event_id: "event_NNN"

Completed fields:
  type: "conversation.item.input_audio_transcription.completed"
  transcript: "Good morning doctor."
  words: [{word, start, end, speaker}]  speaker = 1-based int (1,2,3...)
  start, end: float seconds

Point 2: completed words[] grouped by consecutive speaker → multiple bubbles
Point 3: first speaker = Doctor, second = Patient (deterministic, no LLM)
Point 4: word timing availability reported
Point 5: LIVE delta shows neutral "Speaking..." bubble; completed replaces it
Point 6: endpointing timestamp logged
"""

import abc
import asyncio
import json
import os
import time
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional

import websockets

from .config import settings

# ── Log directory ──────────────────────────────────────────────────────────
_LOGS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "logs"


# ── Logging helpers ────────────────────────────────────────────────────────

def _log_event(raw: dict) -> None:
    """Append every NeMo WebSocket event to nvidia_events.jsonl."""
    try:
        _LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(_LOGS_DIR / "nvidia_events.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"wall_time": time.time(), **raw}) + "\n")
    except Exception:
        pass


def _save_completed_event(data: dict) -> None:
    """
    Point 1: Save each completed event as an individual JSON file.
    Also appended to all_completed_events.jsonl for easy inspection.
    """
    try:
        _LOGS_DIR.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        with open(_LOGS_DIR / f"completed_{ts}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        with open(_LOGS_DIR / "all_completed_events.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"wall_time": time.time(), **data}) + "\n")
    except Exception:
        pass


# ── Speaker grouping ───────────────────────────────────────────────────────

def _normalize_speaker(raw_spk) -> str:
    """NeMo returns 1-based ints. Normalize to 0-based strings."""
    if isinstance(raw_spk, int):
        return f"speaker_{raw_spk - 1}"
    return str(raw_spk)


def _group_words_by_speaker(words: list) -> list:
    """
    Point 2: Group consecutive words with the same speaker.
    Returns list of segment dicts, one per speaker run.

    Example:
      words: [Hello(spk=1), how(spk=1), yes(spk=2), okay(spk=1)]
      → [{speaker_0: "Hello how"}, {speaker_1: "yes"}, {speaker_0: "okay"}]
    """
    if not words:
        return []

    groups: list = []
    current_spk: Optional[str] = None
    current_words: list = []

    for w in words:
        spk = _normalize_speaker(w.get("speaker", 1))
        if current_spk is None:
            current_spk = spk
            current_words = [w]
        elif spk == current_spk:
            current_words.append(w)
        else:
            groups.append(_build_group(current_spk, current_words))
            current_spk = spk
            current_words = [w]

    if current_words:
        groups.append(_build_group(current_spk, current_words))

    return groups


def _build_group(speaker: str, words: list) -> dict:
    text = " ".join(
        w.get("word", w.get("text", "")).strip() for w in words
    ).strip()
    starts = [float(w.get("start", 0.0)) for w in words]
    ends   = [float(w.get("end",   0.0)) for w in words]
    has_real = any(s != 0.0 or e != 0.0 for s, e in zip(starts, ends))
    return {
        "speaker":        speaker,
        "text":           text,
        "start":          min(starts) if has_real else 0.0,
        "end":            max(ends)   if has_real else 0.0,
        "word_count":     len(words),
        "has_real_timing": has_real,
    }


# ── Abstract Provider ──────────────────────────────────────────────────────

class RealtimeSTTProvider(abc.ABC):

    @abc.abstractmethod
    async def start_session(self, session_id: str) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def send_audio(self, pcm_bytes: bytes) -> None:
        pass

    @abc.abstractmethod
    async def receive_events(self) -> AsyncGenerator[Dict[str, Any], None]:
        pass

    @abc.abstractmethod
    async def stop_session(self) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def close(self) -> None:
        pass


# ── NVIDIA NeMo-Speech.cpp v0.2.0 ─────────────────────────────────────────

class NVIDIARealtimeProvider(RealtimeSTTProvider):
    """
    Connects to the local NeMo-Speech.cpp serve endpoint.
    Endpoint: ws://127.0.0.1:8090/v1/audio/transcriptions/realtime

    State:
      _partial_text       — accumulated delta fragments for current utterance
      _partial_audio_start — audio_processed value when utterance started
      _session_start_wall  — wall time when session started (for latency)
    """

    def __init__(self):
        self.ws_url = (
            f"ws://{settings.nemo_speech_host}:{settings.nemo_speech_ws_port}"
            f"/v1/audio/transcriptions/realtime"
        )
        self.ws = None
        self.session_id: Optional[str] = None
        self.is_connected = False
        self.is_flushing = False
        self._receive_task: Optional[asyncio.Task] = None
        self._event_queue: asyncio.Queue = asyncio.Queue()

        # Live partial state — reset on each completed event
        self._partial_text: str = ""
        self._partial_audio_start: float = 0.0
        self._session_start_wall: float = 0.0

    async def start_session(self, session_id: str) -> Dict[str, Any]:
        self.session_id = session_id
        self._session_start_wall = time.time()

        try:
            self.ws = await websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=15,
                max_size=10 * 1024 * 1024,
                open_timeout=10,
            )
        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to NeMo-Speech.cpp at {self.ws_url}\n"
                f"Start the server first:\n"
                f"  nemo-speech serve --asr-model nemotron-3.5 "
                f"--diar-model nemotron-3-diarization --port 8090\n"
                f"Error: {e}"
            )

        self.is_connected = True
        self.is_flushing = False
        self._partial_text = ""

        # Start background receive loop
        self._receive_task = asyncio.create_task(self._read_messages_loop())

        # Wait for session.created (arrives immediately on connect)
        try:
            begin_event = await asyncio.wait_for(self._event_queue.get(), timeout=5.0)
            await self._event_queue.put(begin_event)  # put back for receive_events()
        except asyncio.TimeoutError:
            raise ConnectionError(
                "NeMo-Speech.cpp did not send session.created within 5s."
            )

        # Send session.update BEFORE any audio
        await self.ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "sample_rate":         settings.sample_rate,   # 16000
                "language":            settings.asr_language,  # en-US
                "automatic_punctuation": True,
                "word_timestamps":     True,    # required for speaker data
                "speaker_diarization": True,    # Nemotron-3-Diarization
                "verbatim":            False,
                "endpointing_ms":      800,     # ~800ms natural pause threshold
            }
        }))

        return {
            "status":      "connected",
            "provider":    "nvidia_nemo_local",
            "endpoint":    self.ws_url,
            "asr_model":   settings.nvidia_asr_model,
            "diarization": True,
            "endpointing_ms": 800,
        }

    async def send_audio(self, pcm_bytes: bytes) -> None:
        if not self.is_connected or not self.ws or self.is_flushing:
            return
        try:
            await self.ws.send(pcm_bytes)
        except Exception as e:
            await self._event_queue.put({"type": "error", "error": f"send: {e}"})

    async def _read_messages_loop(self):
        """
        Read NeMo events and translate to internal schema.

        DELTA   → accumulate _partial_text → emit LIVE turn (same segment)
        COMPLETED → group words by speaker → emit per-speaker FINAL turns
                    → reset _partial_text for next utterance
        """
        try:
            async for raw_msg in self.ws:
                if isinstance(raw_msg, bytes):
                    continue
                try:
                    data = json.loads(raw_msg)
                except Exception:
                    continue

                _log_event(data)
                msg_type = data.get("type", "")

                # ── session.created ────────────────────────────────────────
                if msg_type == "session.created":
                    print(f"[NEMO] session.created", flush=True)
                    await self._event_queue.put({"type": "begin", "data": data})

                # ── session.updated ────────────────────────────────────────
                elif msg_type == "session.updated":
                    print(f"[NEMO] session.updated config={data.get('session',{})}", flush=True)

                # ── DELTA ──────────────────────────────────────────────────
                # Sub-word fragment. Accumulate → show as one growing LIVE segment.
                # DO NOT create a new segment per delta.
                elif msg_type == "conversation.item.input_audio_transcription.delta":
                    fragment = data.get("delta", "")
                    audio_t  = data.get("audio_processed", 0.0)

                    if not self._partial_text:
                        self._partial_audio_start = audio_t
                        wall_latency = time.time() - self._session_start_wall
                        print(f"[NEMO] FIRST DELTA  wall_latency={wall_latency:.3f}s", flush=True)

                    if fragment:
                        self._partial_text += fragment
                        print(f"[NEMO] delta +'{fragment}'  partial='{self._partial_text[-60:]}'", flush=True)

                    if self._partial_text.strip():
                        await self._event_queue.put({
                            "type": "turn",
                            "data": {
                                "transcript":  self._partial_text,
                                "end_of_turn": False,       # LIVE
                                "speaker":     "UNKNOWN",   # no speaker in delta
                                "word_groups": [],
                                "words":       [],
                                "start":       self._partial_audio_start,
                                "end":         audio_t,
                            }
                        })

                # ── COMPLETED ─────────────────────────────────────────────
                # Utterance finalized after endpointing silence.
                # words[] contains word-level speaker info (1-based int).
                # Point 2: group by speaker → multiple bubbles if speakers differ.
                elif msg_type == "conversation.item.input_audio_transcription.completed":
                    transcript = data.get("transcript", "").strip()
                    raw_words  = data.get("words", [])
                    seg_start  = float(data.get("start", self._partial_audio_start))
                    seg_end    = float(data.get("end",   0.0))

                    # Point 1: save raw JSON
                    _save_completed_event(data)

                    # Point 4: timing availability
                    has_real = any(
                        w.get("start", 0) != 0 or w.get("end", 0) != 0
                        for w in raw_words
                    )
                    spk_set = {_normalize_speaker(w.get("speaker", 1))
                               for w in raw_words}
                    endpt_wall = time.time() - self._session_start_wall

                    print(f"[NEMO] COMPLETED  wall={endpt_wall:.3f}s "
                          f"text='{transcript[:70]}'  "
                          f"words={len(raw_words)}  speakers={sorted(spk_set)}  "
                          f"timings={'REAL' if has_real else 'ALL_ZERO'}", flush=True)
                    # Point 6: endpointing timestamp
                    print(f"[ENDPOINTING] fired at session_wall={endpt_wall:.3f}s", flush=True)

                    # Point 2: build per-speaker word groups
                    word_groups = _group_words_by_speaker(raw_words)

                    # Dominant speaker (most words) for turn-level fallback
                    spk_counts: Dict[str, int] = {}
                    for w in raw_words:
                        s = _normalize_speaker(w.get("speaker", 1))
                        spk_counts[s] = spk_counts.get(s, 0) + 1
                    dominant = (max(spk_counts, key=spk_counts.get)
                                if spk_counts else "speaker_0")

                    # Reset partial — next delta is a new utterance
                    self._partial_text = ""
                    self._partial_audio_start = 0.0

                    await self._event_queue.put({
                        "type": "turn",
                        "data": {
                            "transcript":      transcript,
                            "end_of_turn":     True,
                            "speaker":         dominant,
                            "word_groups":     word_groups,   # Point 2
                            "words":           raw_words,
                            "start":           seg_start,
                            "end":             seg_end,
                            "has_real_timing": has_real,      # Point 4
                            "confidence":      0.95,
                        }
                    })

                # ── COMMITTED ─────────────────────────────────────────────
                elif msg_type == "input_audio_buffer.committed":
                    print(f"[NEMO] input_audio_buffer.committed", flush=True)
                    await self._event_queue.put({"type": "termination", "data": data})

                elif msg_type == "input_audio_buffer.cleared":
                    pass

                elif msg_type == "error":
                    err = data.get("error", {})
                    msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                    print(f"[NEMO] ERROR: {msg}", flush=True)
                    await self._event_queue.put({"type": "error", "error": msg})

                else:
                    print(f"[NEMO] {msg_type}", flush=True)
                    await self._event_queue.put({"type": "other", "data": data})

        except websockets.ConnectionClosed as e:
            code   = e.rcvd.code   if e.rcvd else "?"
            reason = e.rcvd.reason if e.rcvd else ""
            print(f"[NEMO] connection closed  code={code}  reason='{reason}'", flush=True)
            if code == 1011:
                print(f"[NEMO] 1011 = server internal error — check Window 1 (nemo-speech serve)", flush=True)
        except Exception as ex:
            await self._event_queue.put({"type": "error", "error": f"receive loop: {ex}"})
        finally:
            self.is_connected = False
            await self._event_queue.put({"type": "connection_closed"})

    async def receive_events(self) -> AsyncGenerator[Dict[str, Any], None]:
        while self.is_connected or not self._event_queue.empty():
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=0.1)
                yield event
            except asyncio.TimeoutError:
                continue

    async def stop_session(self) -> Dict[str, Any]:
        """Graceful stop: commit, wait up to 8s for final events."""
        if not self.is_connected or not self.ws:
            return {"status": "already_stopped"}

        self.is_flushing = True
        t0 = time.time()
        try:
            await self.ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
        except Exception as e:
            return {"status": "error", "error": str(e)}

        deadline = time.time() + 8.0
        while time.time() < deadline:
            if not self.is_connected:
                break
            await asyncio.sleep(0.05)

        return {
            "status":   "stopped",
            "flush_ms": round((time.time() - t0) * 1000.0, 2),
            "provider": "nvidia_nemo_local",
        }

    async def close(self) -> None:
        self.is_connected = False
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
        self.ws = None


# ── Offline Simulation Provider ────────────────────────────────────────────

class OfflineSimulationProvider(RealtimeSTTProvider):
    """
    Simulates realistic clinical conversation events for UI/state testing.
    Used when NeMo-Speech.cpp is not running (USE_SIMULATION=true).
    """

    TURNS = [
        ("speaker_0", "Good morning. How are you feeling today?",            2.0),
        ("speaker_1", "I've been having some chest pain for the past few days.", 2.5),
        ("speaker_0", "Can you describe where exactly the pain is?",         1.8),
        ("speaker_1", "It's mostly in the center of my chest, radiating to my left arm.", 3.0),
        ("speaker_0", "Does it happen at rest or only when active?",         1.8),
        ("speaker_1", "Mostly when I climb stairs or walk fast.",            2.0),
        ("speaker_0", "Are you taking any medications currently?",           1.5),
        ("speaker_1", "Yes, metformin 500mg twice daily for diabetes.",      2.5),
        ("speaker_0", "I want to run an ECG and check your troponin levels today.", 2.5),
        ("speaker_1", "Alright, thank you doctor.",                         1.5),
    ]

    def __init__(self):
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self.is_connected = False
        self._task: Optional[asyncio.Task] = None

    async def start_session(self, session_id: str) -> Dict[str, Any]:
        self.is_connected = True
        await self._event_queue.put({"type": "begin", "data": {"mode": "simulation"}})
        self._task = asyncio.create_task(self._stream())
        return {"status": "connected", "provider": "offline_simulation",
                "warning": "NeMo-Speech.cpp NOT running — simulated events only"}

    async def _stream(self):
        await asyncio.sleep(0.5)
        t = 0.0
        for spk, text, dur in self.TURNS:
            if not self.is_connected:
                break
            words = text.split()
            wdur = dur / max(len(words), 1)

            # Emit partial updates word by word
            partial = ""
            for i, w in enumerate(words):
                partial += ("" if i == 0 else " ") + w
                await self._event_queue.put({"type": "turn", "data": {
                    "transcript": partial, "end_of_turn": False,
                    "speaker": "UNKNOWN", "word_groups": [], "words": [],
                    "start": t, "end": t + (i + 1) * wdur,
                }})
                await asyncio.sleep(wdur)

            # Word groups for simulation (all one speaker per turn)
            word_list = [{"word": w, "start": t + k*wdur, "end": t+(k+1)*wdur,
                          "speaker": int(spk.split("_")[1]) + 1}
                         for k, w in enumerate(words)]
            await self._event_queue.put({"type": "turn", "data": {
                "transcript": text, "end_of_turn": True,
                "speaker": spk,
                "word_groups": [_build_group(spk, word_list)],
                "words": word_list,
                "start": t, "end": t + dur, "confidence": 0.95,
            }})
            t += dur + 0.5
            await asyncio.sleep(0.5)

        self.is_connected = False
        await self._event_queue.put({"type": "termination", "data": {}})

    async def send_audio(self, pcm_bytes: bytes) -> None:
        pass

    async def receive_events(self) -> AsyncGenerator[Dict[str, Any], None]:
        while self.is_connected or not self._event_queue.empty():
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=0.1)
                yield event
            except asyncio.TimeoutError:
                continue

    async def stop_session(self) -> Dict[str, Any]:
        self.is_connected = False
        if self._task and not self._task.done():
            self._task.cancel()
        return {"status": "stopped"}

    async def close(self) -> None:
        self.is_connected = False


# ── Factory ────────────────────────────────────────────────────────────────

def create_provider(use_simulation: bool = False) -> RealtimeSTTProvider:
    if use_simulation or os.getenv("USE_SIMULATION", "").lower() == "true":
        return OfflineSimulationProvider()
    return NVIDIARealtimeProvider()
