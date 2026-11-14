"""
Session Manager and Realtime Transcript State Machine
tests/realtime_nvidia/backend/app/session_manager.py

Preserved from AssemblyAI POC — architecture reused exactly.
Only change: provider import → NVIDIARealtimeProvider.

Phase 18: Same architecture as AssemblyAI POC.
Phase 19: Canonical segment state (LIVE → STABLE → FINAL).
Phase 20: Partial replaces in-place (never duplicated).
Phase 21: Final advances to next segment.
Phase 22: Speaker identity is session-level (never reset per chunk).
Phase 23: Speaker cache maintained across silence gaps.
Phase 34: Stop flushes final audio before closing.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import numpy as np

from .config import settings
from .models import (
    TranscriptSegment,
    WordItem,
    RealtimeEvent,
    SessionMetrics,
)
from .provider import NVIDIARealtimeProvider, RealtimeSTTProvider, create_provider


class RealtimeSession:
    def __init__(
        self,
        session_id: str,
        provider: Optional[RealtimeSTTProvider] = None,
    ):
        self.session_id = session_id
        self.provider = provider or create_provider()

        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.stopped_at: Optional[float] = None
        # States: created → active → finalizing → completed | error
        self.status = "created"

        # Transcript State (Phase 19)
        self.segments: Dict[str, TranscriptSegment] = {}
        self.segment_order: List[str] = []
        self.current_segment_id: Optional[str] = None
        self.turn_counter = 0

        # Speaker Attribution State (Phase 22 — deterministic, session-level)
        self.speaker_role_map: Dict[str, str] = {}
        self.detected_speakers: List[str] = []

        # Audio / Metrics Tracking
        self.audio_bytes_received = 0
        self.audio_frames_sent = 0
        self.total_samples = 0
        self.metrics = SessionMetrics(session_id=session_id)

        # Event subscription (fan-out to all WebSocket clients)
        self.subscribers: Set[asyncio.Queue] = set()
        self._provider_task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()

    async def start(self) -> Dict[str, Any]:
        async with self.lock:
            self.started_at = time.time()
            self.status = "active"
            res = await self.provider.start_session(self.session_id)
            self._provider_task = asyncio.create_task(self._process_provider_events())
            return res

    async def push_audio(self, pcm_bytes: bytes) -> None:
        """Receive PCM16 16kHz mono audio from client and forward to NeMo runtime."""
        if self.status != "active":
            return

        now = time.time()
        if self.metrics.time_to_first_audio_frame_ms is None and self.started_at:
            self.metrics.time_to_first_audio_frame_ms = round(
                (now - self.started_at) * 1000.0, 2
            )

        self.audio_bytes_received += len(pcm_bytes)
        self.audio_frames_sent += 1
        self.total_samples += len(pcm_bytes) // 2  # 16-bit PCM = 2 bytes/sample
        self.metrics.total_audio_frames_sent = self.audio_frames_sent
        self.metrics.total_bytes_sent = self.audio_bytes_received
        self.metrics.audio_duration_seconds = round(
            self.total_samples / settings.sample_rate, 2
        )

        await self.provider.send_audio(pcm_bytes)

    def _map_speaker_to_role(self, speaker_id: str) -> str:
        """
        Phase 24: Deterministic session-level speaker → Doctor/Patient mapping.

        Rules:
        - First unique speaker encountered → settings.first_speaker_role (Doctor)
        - Second unique speaker encountered → settings.second_speaker_role (Patient)
        - Additional speakers → "Speaker N"
        - Mapping persists for the entire session (never remapped mid-session)
        - UNKNOWN / empty speaker → "Unassigned"
        """
        if not speaker_id or speaker_id.upper() in ("UNKNOWN", "NONE", ""):
            return "Unassigned"

        clean_id = speaker_id.strip().lower()  # normalize: "Speaker_0" → "speaker_0"

        if clean_id not in self.speaker_role_map:
            if clean_id not in self.detected_speakers:
                self.detected_speakers.append(clean_id)

            idx = self.detected_speakers.index(clean_id)
            if idx == 0:
                self.speaker_role_map[clean_id] = settings.first_speaker_role
            elif idx == 1:
                self.speaker_role_map[clean_id] = settings.second_speaker_role
            else:
                self.speaker_role_map[clean_id] = f"Speaker {idx + 1}"

        return self.speaker_role_map[clean_id]

    async def _process_provider_events(self):
        """
        Asynchronously consume events from NVIDIARealtimeProvider and update
        the canonical transcript state.
        """
        try:
            async for event in self.provider.receive_events():
                etype = event.get("type")
                now = time.time()

                if etype == "begin":
                    await self._emit_event(RealtimeEvent(
                        type="session_status",
                        session_id=self.session_id,
                        status="ready",
                        message=(
                            "Connected to NVIDIA NeMo-Speech.cpp — "
                            f"ASR: {settings.nvidia_asr_model} | "
                            f"Diarization: {settings.nvidia_diarization_model}"
                        ),
                        timestamp=now,
                    ))

                elif etype == "turn":
                    data = event.get("data", {})
                    await self._handle_turn_data(data, now)

                elif etype == "diarization_update":
                    # Phase 23: Speaker identity update from Streaming Sortformer.
                    # Update speaker role map if new speaker detected.
                    data = event.get("data", {})
                    speaker_id = data.get("speaker_id", "UNKNOWN")
                    if speaker_id and speaker_id != "UNKNOWN":
                        self._map_speaker_to_role(speaker_id)
                        # Check if any existing LIVE segment needs speaker revision
                        async with self.lock:
                            if self.current_segment_id:
                                seg = self.segments.get(self.current_segment_id)
                                if seg and seg.speaker_id == "UNKNOWN":
                                    new_role = self._map_speaker_to_role(speaker_id)
                                    if new_role != seg.role:
                                        seg.speaker_id = speaker_id.lower()
                                        seg.role = new_role
                                        seg.version += 1
                                        self.metrics.speaker_revisions_count += 1
                                        if self.metrics.time_to_speaker_revision_ms is None and self.started_at:
                                            self.metrics.time_to_speaker_revision_ms = round(
                                                (now - self.started_at) * 1000.0, 2
                                            )
                                        await self._emit_event(RealtimeEvent(
                                            type="speaker_revision",
                                            session_id=self.session_id,
                                            segment=seg,
                                            timestamp=now,
                                        ))

                elif etype == "speech_started":
                    pass  # Activity hint — no state change needed

                elif etype == "termination":
                    self.status = "completed"

                elif etype == "connection_closed":
                    if self.status not in ("completed", "finalizing"):
                        self.status = "completed"

                elif etype == "error":
                    await self._emit_event(RealtimeEvent(
                        type="error",
                        session_id=self.session_id,
                        message=event.get("error", "Unknown error"),
                        timestamp=now,
                    ))

        except asyncio.CancelledError:
            pass
        except Exception as ex:
            await self._emit_event(RealtimeEvent(
                type="error",
                session_id=self.session_id,
                message=f"Event loop exception: {ex}",
                timestamp=time.time(),
            ))

    async def _handle_turn_data(self, data: Dict[str, Any], now: float):
        """
        Process Turn events from NVIDIARealtimeProvider.

        LIVE (end_of_turn=False):
          - speaker = UNKNOWN (delta has no speaker data)
          - Point 5: show one neutral "Speaking..." LIVE segment
          - Same segment_id updated in-place → browser overwrites same DOM element

        FINAL (end_of_turn=True):
          - Point 2: word_groups contains per-speaker segments from words[]
          - If multiple speakers in word_groups → emit multiple FINAL segments
          - If single speaker → emit one FINAL segment
          - Point 3: first speaker maps to Doctor, second to Patient (session-stable)
          - Clears current_segment_id → next speech creates a NEW segment
        """
        transcript  = data.get("transcript", "").strip()
        end_of_turn = bool(data.get("end_of_turn", False))
        speaker_label = str(data.get("speaker") or "UNKNOWN")
        word_groups   = data.get("word_groups", [])   # Point 2
        words_data    = data.get("words", [])

        if not transcript and not end_of_turn:
            return

        # Latency tracking
        if transcript and self.started_at:
            if self.metrics.time_to_first_partial_ms is None:
                self.metrics.time_to_first_partial_ms = round(
                    (now - self.started_at) * 1000.0, 2)
            if self.metrics.time_to_first_visible_text_ms is None:
                self.metrics.time_to_first_visible_text_ms = round(
                    (now - self.started_at) * 1000.0, 2)

        # ── LIVE (delta) ──────────────────────────────────────────────────
        if not end_of_turn:
            # Point 5: one neutral LIVE segment regardless of speaker
            async with self.lock:
                if self.current_segment_id is None:
                    self.turn_counter += 1
                    seg_id = f"seg_{self.turn_counter:04d}"
                    self.current_segment_id = seg_id
                    self.segment_order.append(seg_id)
                    start_t = float(data.get("start", 0.0)) or round(
                        self.total_samples / settings.sample_rate, 2)
                    self.segments[seg_id] = TranscriptSegment(
                        segment_id=seg_id,
                        turn_id=self.turn_counter,
                        start_time=start_t,
                        end_time=float(data.get("end", start_t)),
                        speaker_id="unknown",
                        role="Speaking...",   # Point 5: neutral label while live
                        text=transcript,
                        status="LIVE",
                        is_final=False,
                        words=[],
                        version=1,
                    )
                else:
                    seg = self.segments[self.current_segment_id]
                    seg.text = transcript
                    seg.end_time = float(data.get("end", seg.end_time))
                    seg.version += 1

                seg = self.segments[self.current_segment_id]
                self.metrics.partial_count += 1

            print(f"[SESSION] LIVE  seg={self.current_segment_id}  "
                  f"len={len(transcript)}  text='{transcript[:50]}'", flush=True)

            await self._emit_event(RealtimeEvent(
                type="segment_update",
                session_id=self.session_id,
                segment=seg,
                timestamp=now,
            ))
            return

        # ── FINAL (completed) ─────────────────────────────────────────────
        # Point 2: use word_groups for per-speaker segment splitting.
        # If word_groups has multiple speakers, close the LIVE segment and
        # emit one FINAL segment per speaker group.
        if not transcript:
            # Empty completed (commit on silence) — just close current LIVE
            async with self.lock:
                if self.current_segment_id:
                    seg = self.segments[self.current_segment_id]
                    seg.status = "FINAL"
                    seg.is_final = True
                    self.current_segment_id = None
            return

        # Determine segments to emit
        # If word_groups available and diarization produced multiple speakers → split
        if word_groups and len({g["speaker"] for g in word_groups}) > 1:
            groups_to_emit = word_groups
        elif word_groups:
            groups_to_emit = word_groups  # single speaker group
        else:
            # Fallback: no word groups (diarization off or words empty)
            groups_to_emit = [{
                "speaker": speaker_label,
                "text": transcript,
                "start": float(data.get("start", 0.0)),
                "end": float(data.get("end", 0.0)),
                "word_count": len(words_data),
                "has_real_timing": False,
            }]

        print(f"[SESSION] FINAL  groups={len(groups_to_emit)}  "
              f"speakers={[g['speaker'] for g in groups_to_emit]}", flush=True)

        async with self.lock:
            # Close / remove the existing LIVE segment — it will be replaced
            # by the FINAL per-speaker segments
            if self.current_segment_id:
                live_seg_id = self.current_segment_id
                # Remove from order — we'll add proper final segments below
                if live_seg_id in self.segment_order:
                    self.segment_order.remove(live_seg_id)
                del self.segments[live_seg_id]
                self.current_segment_id = None

            # Emit one FINAL segment per speaker group (Point 2)
            final_segs: List[TranscriptSegment] = []
            for group in groups_to_emit:
                grp_text = group.get("text", "").strip()
                if not grp_text:
                    continue

                grp_spk  = group.get("speaker", speaker_label)
                grp_role = self._map_speaker_to_role(grp_spk)  # Point 3
                grp_start = float(group.get("start", 0.0))
                grp_end   = float(group.get("end", 0.0))

                self.turn_counter += 1
                seg_id = f"seg_{self.turn_counter:04d}"
                self.segment_order.append(seg_id)

                # Build WordItems for this group
                grp_words: List[WordItem] = []
                for w in words_data:
                    from .provider import _normalize_speaker
                    w_spk = _normalize_speaker(w.get("speaker", 1))
                    if w_spk == grp_spk:
                        grp_words.append(WordItem(
                            text=w.get("word", w.get("text", "")),
                            start=float(w.get("start", 0.0)),
                            end=float(w.get("end", 0.0)),
                            speaker=w_spk,
                            word_is_final=True,
                        ))

                new_seg = TranscriptSegment(
                    segment_id=seg_id,
                    turn_id=self.turn_counter,
                    start_time=grp_start,
                    end_time=grp_end,
                    speaker_id=grp_spk,
                    role=grp_role,
                    text=grp_text,
                    status="FINAL",
                    is_final=True,
                    words=grp_words,
                    version=1,
                )
                self.segments[seg_id] = new_seg
                final_segs.append(new_seg)

            self.metrics.final_count += len(final_segs)
            if self.metrics.time_to_final_turn_ms is None and self.started_at:
                self.metrics.time_to_final_turn_ms = round(
                    (now - self.started_at) * 1000.0, 2)

        # Broadcast all FINAL segments
        for fs in final_segs:
            print(f"[SESSION] FINAL seg={fs.segment_id}  "
                  f"role={fs.role}  text='{fs.text[:60]}'", flush=True)
            await self._emit_event(RealtimeEvent(
                type="segment_update",
                session_id=self.session_id,
                segment=fs,
                timestamp=now,
            ))

    async def _emit_event(self, event: RealtimeEvent):
        """Broadcast event to all subscribed WebSocket clients."""
        dead_subs: Set[asyncio.Queue] = set()
        for q in self.subscribers:
            try:
                q.put_nowait(event)
            except Exception:
                dead_subs.add(q)
        self.subscribers -= dead_subs

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.subscribers.discard(q)

    async def stop(self) -> Dict[str, Any]:
        """
        Phase 34: Graceful stop sequence.
        1. Stop microphone (handled by client before sending stop message)
        2. Send end_of_stream to NeMo-Speech.cpp
        3. Allow final buffered audio to be processed
        4. Collect final ASR and diarization results
        5. Mark session complete and save transcript
        """
        self.status = "finalizing"
        t0 = time.time()

        stop_res = await self.provider.stop_session()
        self.stopped_at = time.time()

        flush_ms = (self.stopped_at - t0) * 1000.0
        self.metrics.stop_to_final_ms = round(flush_ms, 2)

        if self.started_at:
            total_wall = self.stopped_at - self.started_at
            self.metrics.wall_clock_processing_seconds = round(total_wall, 2)
            self.metrics.session_total_latency_ms = round(total_wall * 1000.0, 2)
            if self.metrics.audio_duration_seconds > 0:
                self.metrics.rtf = round(
                    total_wall / self.metrics.audio_duration_seconds, 3
                )

        # Finalize all remaining LIVE segments
        async with self.lock:
            for s in self.segments.values():
                s.status = "FINAL"
                s.is_final = True
            self.status = "completed"

        final_segments = [self.segments[sid] for sid in self.segment_order]

        # Save session artifacts to logs/
        self._save_session_artifacts(final_segments)

        # Broadcast final summary to all subscribers
        await self._emit_event(RealtimeEvent(
            type="final_summary",
            session_id=self.session_id,
            all_segments=final_segments,
            metrics=self.metrics.model_dump(),
            timestamp=time.time(),
        ))

        await self.provider.close()

        return {
            "status": "completed",
            "session_id": self.session_id,
            "metrics": self.metrics.model_dump(),
            "total_segments": len(final_segments),
            "segments": [s.model_dump() for s in final_segments],
        }

    def _save_session_artifacts(self, final_segments: List[TranscriptSegment]) -> None:
        """Save structured transcript and metrics to logs/."""
        log_json = settings.logs_dir / f"session_{self.session_id}.json"
        log_txt = settings.logs_dir / f"session_{self.session_id}.txt"

        data = {
            "session_id": self.session_id,
            "provider": "nvidia_nemo_local",
            "asr_model": settings.nvidia_asr_model,
            "diarization_model": settings.nvidia_diarization_model,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "metrics": self.metrics.model_dump(),
            "segments": [s.model_dump() for s in final_segments],
        }
        log_json.write_text(json.dumps(data, indent=2), encoding="utf-8")

        with open(log_txt, "w", encoding="utf-8") as f:
            f.write(f"Session: {self.session_id}\n")
            f.write(f"Provider: NVIDIA NeMo Local (no cloud)\n")
            f.write(f"ASR: {settings.nvidia_asr_model} | Diarization: {settings.nvidia_diarization_model}\n")
            f.write(
                f"Audio: {self.metrics.audio_duration_seconds}s | "
                f"Wall: {self.metrics.wall_clock_processing_seconds}s | "
                f"RTF: {self.metrics.rtf}\n"
            )
            f.write(
                f"First Text: {self.metrics.time_to_first_visible_text_ms}ms | "
                f"First Partial: {self.metrics.time_to_first_partial_ms}ms | "
                f"Final Turn: {self.metrics.time_to_final_turn_ms}ms\n"
            )
            f.write("=" * 64 + "\n\n")
            for s in final_segments:
                f.write(f"{s.role}: {s.text}\n\n")


class SessionManager:
    """Manages active realtime sessions."""

    def __init__(self):
        self.sessions: Dict[str, RealtimeSession] = {}
        self.lock = asyncio.Lock()

    async def create_session(
        self,
        session_id: Optional[str] = None,
        use_simulation: bool = False,
    ) -> "RealtimeSession":
        async with self.lock:
            sid = session_id or f"nv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            session = RealtimeSession(
                session_id=sid,
                provider=create_provider(use_simulation=use_simulation),
            )
            self.sessions[sid] = session
            return session

    def get_session(self, session_id: str) -> Optional["RealtimeSession"]:
        return self.sessions.get(session_id)

    async def remove_session(self, session_id: str) -> None:
        async with self.lock:
            if session_id in self.sessions:
                s = self.sessions.pop(session_id)
                await s.provider.close()


# Module-level singleton
session_manager = SessionManager()
