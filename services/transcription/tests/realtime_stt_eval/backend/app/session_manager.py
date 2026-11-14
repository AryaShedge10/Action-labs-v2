"""
Session Manager and Realtime Transcript State Machine
tests/realtime_stt_eval/backend/app/session_manager.py
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import numpy as np

from .config import settings
from .models import TranscriptSegment, WordItem, RealtimeEvent, SessionMetrics
from .provider import AssemblyAIRealtimeProvider, RealtimeSTTProvider

class RealtimeSession:
    def __init__(self, session_id: str, provider: Optional[RealtimeSTTProvider] = None):
        self.session_id = session_id
        self.provider = provider or AssemblyAIRealtimeProvider()
        
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.stopped_at: Optional[float] = None
        self.status = "created"  # created, active, finalizing, completed, error
        
        # Transcript State
        self.segments: Dict[str, TranscriptSegment] = {}
        self.segment_order: List[str] = []
        self.current_segment_id: Optional[str] = None
        self.turn_counter = 0
        
        # Speaker Attribution State (Deterministic session mapping)
        self.speaker_role_map: Dict[str, str] = {}
        self.detected_speakers: List[str] = []
        
        # Audio / Metrics Tracking
        self.audio_bytes_received = 0
        self.audio_frames_sent = 0
        self.total_samples = 0
        self.metrics = SessionMetrics(session_id=session_id)
        
        # Event subscription
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
        """Receives audio from client and forwards to AssemblyAI."""
        if self.status != "active":
            return
        
        now = time.time()
        if self.metrics.time_to_first_audio_frame_ms is None and self.started_at:
            self.metrics.time_to_first_audio_frame_ms = round((now - self.started_at) * 1000.0, 2)

        self.audio_bytes_received += len(pcm_bytes)
        self.audio_frames_sent += 1
        self.total_samples += len(pcm_bytes) // 2  # 16-bit PCM = 2 bytes per sample
        self.metrics.total_audio_frames_sent = self.audio_frames_sent
        self.metrics.total_bytes_sent = self.audio_bytes_received
        self.metrics.audio_duration_seconds = round(self.total_samples / settings.sample_rate, 2)

        await self.provider.send_audio(pcm_bytes)

    def _map_speaker_to_role(self, speaker_id: str) -> str:
        """Deterministic session-level speaker mapping (Doctor / Patient)."""
        if not speaker_id or speaker_id.upper() in ("UNKNOWN", "NONE", ""):
            return "Unassigned"

        clean_id = speaker_id.strip()
        if clean_id not in self.speaker_role_map:
            if clean_id not in self.detected_speakers:
                self.detected_speakers.append(clean_id)
            
            # Map first speaker to Doctor, second to Patient
            if len(self.detected_speakers) == 1:
                self.speaker_role_map[clean_id] = settings.first_speaker_role
            elif len(self.detected_speakers) == 2:
                self.speaker_role_map[clean_id] = settings.second_speaker_role
            else:
                self.speaker_role_map[clean_id] = f"Speaker {len(self.detected_speakers)}"

        return self.speaker_role_map[clean_id]

    async def _process_provider_events(self):
        """Asynchronously receives events from AssemblyAI and updates transcript state."""
        try:
            async for event in self.provider.receive_events():
                etype = event.get("type")
                now = time.time()
                
                if etype == "begin":
                    await self._emit_event(RealtimeEvent(
                        type="session_status",
                        session_id=self.session_id,
                        status="ready",
                        message="Connected to AssemblyAI Universal-3.6 Pro Realtime",
                        timestamp=now
                    ))

                elif etype == "turn":
                    data = event.get("data", {})
                    await self._handle_turn_data(data, now)

                elif etype == "speech_started":
                    pass

                elif etype == "termination":
                    self.status = "completed"

                elif etype == "error":
                    await self._emit_event(RealtimeEvent(
                        type="error",
                        session_id=self.session_id,
                        message=event.get("error"),
                        timestamp=now
                    ))
        except asyncio.CancelledError:
            pass
        except Exception as ex:
            await self._emit_event(RealtimeEvent(
                type="error",
                session_id=self.session_id,
                message=f"Event loop exception: {ex}",
                timestamp=time.time()
            ))

    async def _handle_turn_data(self, data: Dict[str, Any], now: float):
        """Processes Turn messages from AssemblyAI."""
        transcript = data.get("transcript", "").strip()
        end_of_turn = bool(data.get("end_of_turn", False))
        speaker_label = str(data.get("speaker_label") or data.get("speaker") or "UNKNOWN")
        words_data = data.get("words", [])

        # Parse word items
        words = []
        dominant_speaker = speaker_label
        for w in words_data:
            w_spk = str(w.get("speaker") or speaker_label or "UNKNOWN")
            words.append(WordItem(
                text=w.get("text", ""),
                start=float(w.get("start", 0)) / 1000.0,
                end=float(w.get("end", 0)) / 1000.0,
                speaker=w_spk,
                word_is_final=bool(w.get("word_is_final", False))
            ))
            if dominant_speaker == "UNKNOWN" and w_spk != "UNKNOWN":
                dominant_speaker = w_spk

        role = self._map_speaker_to_role(dominant_speaker)

        # Track first partial & visible text latency
        if transcript and self.started_at:
            if self.metrics.time_to_first_partial_ms is None:
                self.metrics.time_to_first_partial_ms = round((now - self.started_at) * 1000.0, 2)
            if self.metrics.time_to_first_visible_text_ms is None:
                self.metrics.time_to_first_visible_text_ms = round((now - self.started_at) * 1000.0, 2)

        async with self.lock:
            # If we don't have an active segment, start a new one
            if self.current_segment_id is None:
                if not transcript and not end_of_turn:
                    return
                self.turn_counter += 1
                seg_id = f"seg_{self.turn_counter:04d}"
                self.current_segment_id = seg_id
                self.segment_order.append(seg_id)
                self.segments[seg_id] = TranscriptSegment(
                    segment_id=seg_id,
                    turn_id=self.turn_counter,
                    start_time=words[0].start if words else round(self.total_samples / settings.sample_rate, 2),
                    end_time=words[-1].end if words else round(self.total_samples / settings.sample_rate, 2),
                    speaker_id=dominant_speaker,
                    role=role,
                    text=transcript,
                    status="LIVE",
                    is_final=False,
                    words=words,
                    version=1
                )
            else:
                seg_id = self.current_segment_id
                seg = self.segments[seg_id]
                
                # Check for speaker revision
                old_role = seg.role
                if dominant_speaker != "UNKNOWN" and dominant_speaker != seg.speaker_id:
                    self.metrics.speaker_revisions_count += 1
                    if self.started_at and self.metrics.time_to_speaker_revision_ms is None:
                        self.metrics.time_to_speaker_revision_ms = round((now - self.started_at) * 1000.0, 2)

                seg.text = transcript
                seg.speaker_id = dominant_speaker
                seg.role = role
                if words:
                    seg.end_time = words[-1].end
                    seg.words = words
                seg.version += 1

            seg = self.segments[self.current_segment_id]

            if end_of_turn:
                seg.status = "FINAL"
                seg.is_final = True
                self.metrics.final_count += 1
                if self.started_at and self.metrics.time_to_final_turn_ms is None:
                    self.metrics.time_to_final_turn_ms = round((now - self.started_at) * 1000.0, 2)
                
                # Turn finalized: advance current_segment_id so next speech creates next segment
                self.current_segment_id = None
            else:
                self.metrics.partial_count += 1

        # Emit update event for this segment
        await self._emit_event(RealtimeEvent(
            type="segment_update",
            session_id=self.session_id,
            segment=seg,
            timestamp=now
        ))

    async def _emit_event(self, event: RealtimeEvent):
        """Broadcasts event to all active WebSocket clients."""
        dead_subs = set()
        for q in self.subscribers:
            try:
                q.put_nowait(event)
            except Exception:
                dead_subs.add(q)
        self.subscribers -= dead_subs

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self.subscribers.discard(q)

    async def stop(self) -> Dict[str, Any]:
        """Flushes remaining audio, marks session complete, saves transcript and returns final metrics."""
        self.status = "finalizing"
        t0 = time.time()

        # Call provider stop
        stop_res = await self.provider.stop_session()
        self.stopped_at = time.time()
        stop_duration_ms = (self.stopped_at - t0) * 1000.0
        self.metrics.stop_to_final_ms = round(stop_duration_ms, 2)

        if self.started_at:
            total_wall_s = self.stopped_at - self.started_at
            self.metrics.wall_clock_processing_seconds = round(total_wall_s, 2)
            self.metrics.session_total_latency_ms = round(total_wall_s * 1000.0, 2)
            if self.metrics.audio_duration_seconds > 0:
                self.metrics.rtf = round(total_wall_s / self.metrics.audio_duration_seconds, 3)

        # Mark all live segments as final
        async with self.lock:
            for s in self.segments.values():
                s.status = "FINAL"
                s.is_final = True
            self.status = "completed"

        final_segments = [self.segments[sid] for sid in self.segment_order]

        # Save session transcript to disk
        self._save_session_artifacts(final_segments)

        # Emit final summary event
        await self._emit_event(RealtimeEvent(
            type="final_summary",
            session_id=self.session_id,
            all_segments=final_segments,
            metrics=self.metrics.model_dump(),
            timestamp=time.time()
        ))

        # Close provider
        await self.provider.close()

        return {
            "status": "completed",
            "session_id": self.session_id,
            "metrics": self.metrics.model_dump(),
            "total_segments": len(final_segments),
            "segments": [s.model_dump() for s in final_segments]
        }

    def _save_session_artifacts(self, final_segments: List[TranscriptSegment]):
        """Persists structured transcript and latency report to logs/."""
        log_json = settings.logs_dir / f"session_{self.session_id}.json"
        log_txt = settings.logs_dir / f"session_{self.session_id}.txt"

        data = {
            "session_id": self.session_id,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "metrics": self.metrics.model_dump(),
            "segments": [s.model_dump() for s in final_segments]
        }
        log_json.write_text(json.dumps(data, indent=2), encoding="utf-8")

        with open(log_txt, "w", encoding="utf-8") as f:
            f.write(f"Session: {self.session_id}\n")
            f.write(f"Audio Duration: {self.metrics.audio_duration_seconds}s | Wall: {self.metrics.wall_clock_processing_seconds}s\n")
            f.write(f"First Visible Text: {self.metrics.time_to_first_visible_text_ms}ms | Final Turn: {self.metrics.time_to_final_turn_ms}ms\n")
            f.write("=" * 64 + "\n\n")
            for s in final_segments:
                f.write(f"{s.role}: {s.text}\n\n")


class SessionManager:
    """Manages active realtime sessions."""
    def __init__(self):
        self.sessions: Dict[str, RealtimeSession] = {}
        self.lock = asyncio.Lock()

    async def create_session(self, session_id: Optional[str] = None) -> RealtimeSession:
        async with self.lock:
            sid = session_id or f"rt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            session = RealtimeSession(session_id=sid)
            self.sessions[sid] = session
            return session

    def get_session(self, session_id: str) -> Optional[RealtimeSession]:
        return self.sessions.get(session_id)

    async def remove_session(self, session_id: str):
        async with self.lock:
            if session_id in self.sessions:
                s = self.sessions.pop(session_id)
                await s.provider.close()

session_manager = SessionManager()
