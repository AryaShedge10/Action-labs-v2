"""
Asynchronous Streaming Pipeline Orchestrator.

Implements Master Prompt Architecture:
- 5s chunking on a global conversation timeline
- Decoupled Whisper (fast-path: <1s transcript) & Pyannote (asynchronous GPU diarization)
- Controlled GPU concurrency (shared lock)
- Alignment queue with word-boundary splitting and jitter suppression (Rules 1-4)
- 3-Chunk rolling window contextual refinement via Groq / local fallback
- Stable canonical utterance tracking (no duplicate chat bubbles)
- Non-blocking graceful stop / finalization
- Latency and queue depth metrics
"""
import threading
import queue
import time
import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
import soundfile as sf
from datetime import datetime

from app.transcription.whisper_service import get_whisper_service
from app.services.diarization import diarize_chunk
from app.services.alignment import align_whisper_with_diarization
from app.services.utterance_manager import UtteranceManager
from app.services.llm_correction import refine_window_with_llm
from app.services.roles import detect_speaker_roles


class LivePipeline:
    """Manages the real-time asynchronous streaming transcription & diarization session."""

    def __init__(self, session_id: str, chunk_duration_sec: float = 5.0, sample_rate: int = 16000):
        self.session_id = session_id
        self.chunk_duration_sec = chunk_duration_sec
        self.sample_rate = sample_rate

        self.utterance_manager = UtteranceManager(session_id)

        # Global timeline tracker
        self.total_processed_samples = 0
        self.chunk_index = 0
        self.is_active = True
        self.is_finalizing = False
        self.is_completed = False

        # Audio history buffer (16kHz mono)
        self._audio_buffer_lock = threading.Lock()
        self._full_audio_mono: List[np.ndarray] = []

        # Worker queues
        self.whisper_queue = queue.Queue(maxsize=10)
        self.diarization_queue = queue.Queue(maxsize=10)
        self.alignment_queue = queue.Queue(maxsize=10)

        # 3-chunk window tracking
        self._window_chunks: List[Tuple[int, float, float, List[Dict]]] = []  # (chunk_id, start, end, aligned_segs)
        self._window_stride = 2  # slide window every 2 chunks with 1 chunk overlap
        self._last_refined_chunk = -1

        # Performance & Latency Metrics
        self.metrics_lock = threading.Lock()
        self.metrics = {
            "whisper_latency_sec": 0.0,
            "pyannote_latency_sec": 0.0,
            "alignment_latency_sec": 0.0,
            "groq_latency_sec": 0.0,
            "total_chunks_processed": 0,
            "whisper_queue_depth": 0,
            "diarization_queue_depth": 0,
            "alignment_queue_depth": 0,
        }

        # Background worker threads
        self._threads: List[threading.Thread] = []
        self._start_workers()

    def _start_workers(self):
        t_whisper = threading.Thread(target=self._whisper_worker, daemon=True, name=f"WhisperWorker-{self.session_id}")
        t_diarize = threading.Thread(target=self._diarization_worker, daemon=True, name=f"DiarizeWorker-{self.session_id}")
        t_align = threading.Thread(target=self._alignment_worker, daemon=True, name=f"AlignWorker-{self.session_id}")

        self._threads = [t_whisper, t_diarize, t_align]
        for t in self._threads:
            t.start()

    # -----------------------------------------------------------------------
    # Ingestion: Feed 5-second audio chunk
    # -----------------------------------------------------------------------
    def feed_chunk(self, chunk_audio_16k: np.ndarray, is_last: bool = False):
        """
        Feed a processed 16kHz mono audio chunk into the pipeline.
        Calculates exact global timeline timestamps.
        """
        if not self.is_active:
            return

        with self._audio_buffer_lock:
            self._full_audio_mono.append(chunk_audio_16k.copy())

        chunk_id = self.chunk_index
        self.chunk_index += 1

        offset_sec = round(self.total_processed_samples / self.sample_rate, 2)
        chunk_len_sec = round(len(chunk_audio_16k) / self.sample_rate, 2)
        end_sec = round(offset_sec + chunk_len_sec, 2)
        self.total_processed_samples += len(chunk_audio_16k)

        # Context audio for Pyannote (current chunk + up to 5s of previous context)
        with self._audio_buffer_lock:
            total_samples = sum(len(c) for c in self._full_audio_mono)
            all_audio = np.concatenate(self._full_audio_mono)
            # Take last 10 seconds for rich diarization context
            context_samples = min(total_samples, self.sample_rate * 10)
            context_audio = all_audio[-context_samples:]
            context_offset_sec = round((total_samples - context_samples) / self.sample_rate, 2)

        task = {
            "chunk_id": chunk_id,
            "start_time": offset_sec,
            "end_time": end_sec,
            "chunk_audio": chunk_audio_16k,
            "context_audio": context_audio,
            "context_offset": context_offset_sec,
            "is_last": is_last,
        }

        # Dispatch in parallel to both independent queues
        try:
            self.whisper_queue.put(task, block=False)
        except queue.Full:
            print(f"[Pipeline] [WARN] whisper_queue full for chunk {chunk_id}")

        try:
            self.diarization_queue.put(task, block=False)
        except queue.Full:
            print(f"[Pipeline] [WARN] diarization_queue full for chunk {chunk_id}")

    # -----------------------------------------------------------------------
    # Worker 1: Whisper Fast-Path (<1s Transcript)
    # -----------------------------------------------------------------------
    def _whisper_worker(self):
        ws = get_whisper_service()
        while self.is_active or not self.whisper_queue.empty():
            try:
                task = self.whisper_queue.get(timeout=0.3)
            except queue.Empty:
                continue

            chunk_id = task["chunk_id"]
            start_sec = task["start_time"]
            chunk_audio = task["chunk_audio"]

            t0 = time.time()
            try:
                # Transcribe with word timestamps on global timeline
                segs = ws.transcribe_chunk(chunk_audio, offset_seconds=start_sec)
            except Exception as e:
                print(f"[WhisperWorker] Error on chunk {chunk_id}: {e}")
                segs = []

            dur = time.time() - t0
            with self.metrics_lock:
                self.metrics["whisper_latency_sec"] = round(dur, 2)
                self.metrics["whisper_queue_depth"] = self.whisper_queue.qsize()

            # State A: Add provisional utterances immediately!
            self.utterance_manager.add_provisional_chunks(chunk_id, segs)

            # Pass to alignment queue
            self.alignment_queue.put({
                "type": "whisper",
                "chunk_id": chunk_id,
                "start_time": start_sec,
                "end_time": task["end_time"],
                "segments": segs,
                "is_last": task["is_last"]
            })
            self.whisper_queue.task_done()

    # -----------------------------------------------------------------------
    # Worker 2: Asynchronous Pyannote Diarization (GPU)
    # -----------------------------------------------------------------------
    def _diarization_worker(self):
        while self.is_active or not self.diarization_queue.empty():
            try:
                task = self.diarization_queue.get(timeout=0.3)
            except queue.Empty:
                continue

            chunk_id = task["chunk_id"]
            context_audio = task["context_audio"]
            context_offset = task["context_offset"]

            t0 = time.time()
            try:
                # Run diarization on context audio
                raw_turns = diarize_chunk(
                    context_audio,
                    sample_rate=self.sample_rate,
                    offset_seconds=context_offset,
                    min_speakers=1,
                    max_speakers=2
                )
                # Keep only turns that touch or overlap this chunk
                chunk_turns = [
                    t for t in raw_turns
                    if t["end"] >= task["start_time"] - 0.2 and t["start"] <= task["end_time"] + 0.2
                ]
            except Exception as e:
                print(f"[DiarizeWorker] Error on chunk {chunk_id}: {e}")
                chunk_turns = []

            dur = time.time() - t0
            with self.metrics_lock:
                self.metrics["pyannote_latency_sec"] = round(dur, 2)
                self.metrics["diarization_queue_depth"] = self.diarization_queue.qsize()

            # Pass to alignment queue
            self.alignment_queue.put({
                "type": "diarization",
                "chunk_id": chunk_id,
                "start_time": task["start_time"],
                "end_time": task["end_time"],
                "turns": chunk_turns,
                "is_last": task["is_last"]
            })
            self.diarization_queue.task_done()

    # -----------------------------------------------------------------------
    # Worker 3: Alignment, 3-Chunk Window Batching & Groq Refinement
    # -----------------------------------------------------------------------
    def _alignment_worker(self):
        pending_whisper: Dict[int, Dict] = {}
        pending_diarization: Dict[int, Dict] = {}

        while self.is_active or not self.alignment_queue.empty() or pending_whisper or pending_diarization:
            try:
                item = self.alignment_queue.get(timeout=0.3)
                if item["type"] == "whisper":
                    pending_whisper[item["chunk_id"]] = item
                elif item["type"] == "diarization":
                    pending_diarization[item["chunk_id"]] = item
                self.alignment_queue.task_done()
            except queue.Empty:
                pass

            with self.metrics_lock:
                self.metrics["alignment_queue_depth"] = self.alignment_queue.qsize()

            # Find chunks that have BOTH whisper and diarization ready
            ready_chunks = sorted(list(set(pending_whisper.keys()) & set(pending_diarization.keys())))

            for cid in ready_chunks:
                w_item = pending_whisper.pop(cid)
                d_item = pending_diarization.pop(cid)

                t0 = time.time()
                aligned_segs = align_whisper_with_diarization(
                    whisper_segments=w_item["segments"],
                    diarization_turns=d_item["turns"]
                )

                # State B: Update provisional utterances with acoustic speaker labels
                self.utterance_manager.apply_aligned_segments(cid, aligned_segs)

                # Update global role mapping if not yet locked
                role_map = self.utterance_manager.get_role_mapping()
                if not role_map:
                    detected_roles = detect_speaker_roles(aligned_segs)
                    if detected_roles:
                        self.utterance_manager.set_role_mapping(detected_roles)

                align_dur = time.time() - t0
                with self.metrics_lock:
                    self.metrics["alignment_latency_sec"] = round(align_dur, 2)
                    self.metrics["total_chunks_processed"] += 1

                # Append to 3-chunk window buffer
                self._window_chunks.append((cid, w_item["start_time"], w_item["end_time"], aligned_segs))

                # Check if we have 3 chunks in window for Groq contextual refinement
                if len(self._window_chunks) >= 3 and cid > self._last_refined_chunk:
                    self._trigger_window_refinement(is_final=False)

    def _trigger_window_refinement(self, is_final: bool = False):
        """
        Sections 8, 9, 10, 11:
        Groups chunks into 3-chunk rolling window and invokes Groq / local refiner.
        """
        if not self._window_chunks:
            return

        window_start = self._window_chunks[0][1]
        window_end = self._window_chunks[-1][2]
        window_cids = [c[0] for c in self._window_chunks]

        # Gather utterances in this window from canonical manager
        current_utts = [
            u for u in self.utterance_manager.get_utterances()
            if any(cid in u.get("source_chunks", []) for cid in window_cids)
        ]

        if not current_utts:
            return

        window_payload = {
            "conversation_id": self.session_id,
            "window": {
                "start": window_start,
                "end": window_end
            },
            "utterances": [
                {
                    "chunk_id": u.get("source_chunks", [0])[0],
                    "text": u["text"],
                    "start": u["start"],
                    "end": u["end"],
                    "speaker": u.get("speaker_raw", u["speaker"]),
                    "overlap": u.get("overlap", False)
                }
                for u in current_utts
            ]
        }

        t0 = time.time()
        refinement_result = refine_window_with_llm(window_payload)
        groq_dur = time.time() - t0

        with self.metrics_lock:
            self.metrics["groq_latency_sec"] = round(groq_dur, 2)

        refined_turns = refinement_result.get("turns", [])
        if refined_turns:
            # State C: Apply refined window to canonical utterances
            self.utterance_manager.apply_window_refinement(window_start, window_end, refined_turns)

        self._last_refined_chunk = window_cids[-1]

        # Slide window: keep last chunk for overlapping context
        if not is_final and len(self._window_chunks) >= 3:
            self._window_chunks = self._window_chunks[self._window_stride:]

    # -----------------------------------------------------------------------
    # Section 18: Graceful End Conversation Flow
    # -----------------------------------------------------------------------
    def stop(self, timeout_sec: float = 12.0) -> Dict:
        """
        Gracefully stop conversation:
        1. Complete in-flight Whisper & Pyannote jobs
        2. Process final partial window
        3. Merge remaining same-speaker utterances
        4. Save canonical JSON
        5. Mark complete
        """
        self.is_active = False
        self.is_finalizing = True

        print(f"\n[Pipeline] Stopping session {self.session_id} gracefully...")
        t_stop_start = time.time()

        # Wait for whisper and diarization queues to drain
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            w_done = self.whisper_queue.empty()
            d_done = self.diarization_queue.empty()
            a_done = self.alignment_queue.empty()
            if w_done and d_done and a_done:
                break
            time.sleep(0.15)

        # Trigger final partial window refinement
        if self._window_chunks:
            self._trigger_window_refinement(is_final=True)

        # Finalize canonical utterances (merges remaining consecutive turns)
        self.utterance_manager.mark_all_final()

        # Save to output file
        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / f"session_{self.session_id}.json"

        team_b_segments = self.utterance_manager.to_team_b_segments()
        total_duration = round(self.total_processed_samples / self.sample_rate, 2)

        session_data = {
            "consultation_id": self.session_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "duration": total_duration,
            "segments": team_b_segments,
            "metadata": {
                "total_segments": len(team_b_segments),
                "total_duration": total_duration,
                "diarization_status": "enabled",
                "model": "whisper-local-small.en + pyannote-3.1",
                "format_version": "team_b_compatible_v1",
                "pipeline": "real-time-asynchronous-pipeline",
                "metrics": dict(self.metrics)
            }
        }

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        self.is_finalizing = False
        self.is_completed = True
        print(f"[Pipeline] [OK] Finalized session {self.session_id} in {time.time()-t_stop_start:.2f}s -> {out_path}")

        return session_data

    def get_live_state(self) -> Dict:
        """
        Returns real-time session state for UI streaming polling or WebSocket:
        Includes canonical utterances with their statuses (provisional vs diarized vs refined vs final)
        and current performance latency metrics.
        """
        with self.metrics_lock:
            current_metrics = dict(self.metrics)
            current_metrics["whisper_queue_depth"] = self.whisper_queue.qsize()
            current_metrics["diarization_queue_depth"] = self.diarization_queue.qsize()
            current_metrics["alignment_queue_depth"] = self.alignment_queue.qsize()

        utts = self.utterance_manager.get_utterances()
        total_dur = round(self.total_processed_samples / self.sample_rate, 2)

        return {
            "session_id": self.session_id,
            "is_active": self.is_active,
            "is_finalizing": self.is_finalizing,
            "is_completed": self.is_completed,
            "duration": total_dur,
            "total_utterances": len(utts),
            "utterances": utts,
            "metrics": current_metrics,
        }
