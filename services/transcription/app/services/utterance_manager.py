"""
Canonical Utterance Manager & Deduplication Engine.

Maintains canonical conversation utterances across streaming stages:
1. Fast-Path (Provisional): Immediate Whisper transcript (speaker="Pending...")
2. Diarized: Pyannote alignment updates speaker labels
3. Refined: 3-chunk window Groq/local refinement merges consecutive same-speaker turns
4. Final: Clean completed consultation records

Provides stable utterance_id tracking to prevent duplicate UI bubbles during
overlapping window processing.
"""
from typing import List, Dict, Optional
import threading
import time
import copy


class UtteranceManager:
    """Thread-safe manager for canonical conversation utterances."""

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.lock = threading.Lock()
        self._utterances: List[Dict] = []
        self._next_id = 1
        self._role_mapping: Dict[str, str] = {}  # e.g. {"SPEAKER_00": "DOCTOR", "SPEAKER_01": "PATIENT"}

    def _generate_id(self) -> str:
        uid = f"utt_{self._next_id:05d}"
        self._next_id += 1
        return uid

    def set_role_mapping(self, mapping: Dict[str, str]):
        with self.lock:
            self._role_mapping.update(mapping)
            # Re-apply to existing utterances if needed
            for u in self._utterances:
                raw = u.get("speaker_raw", "")
                if raw in self._role_mapping:
                    u["speaker"] = self._role_mapping[raw].upper()

    def get_role_mapping(self) -> Dict[str, str]:
        with self.lock:
            return dict(self._role_mapping)

    def add_provisional_chunks(self, chunk_id: int, segments: List[Dict]) -> List[Dict]:
        """
        State A (Immediate Transcript):
        Add fast-path Whisper segments with status='provisional' and speaker='Pending...'.
        Returns list of newly added provisional utterances.
        """
        with self.lock:
            new_utts = []
            for seg in segments:
                text = str(seg.get("text", "")).strip()
                if not text:
                    continue
                utt = {
                    "conversation_id": self.conversation_id,
                    "utterance_id": self._generate_id(),
                    "speaker": "Pending...",
                    "speaker_raw": "UNKNOWN",
                    "start": round(float(seg.get("start", 0.0)), 2),
                    "end": round(float(seg.get("end", 0.0)), 2),
                    "text": text,
                    "source_chunks": [chunk_id],
                    "status": "provisional",
                    "confidence": 0.50,
                    "overlap": bool(seg.get("overlap", False)),
                }
                self._utterances.append(utt)
                new_utts.append(copy.deepcopy(utt))
            return new_utts

    def apply_aligned_segments(self, chunk_id: int, aligned_segments: List[Dict]):
        """
        State B (Diarized):
        Update provisional utterances from chunk_id with acoustic speaker labels from alignment.
        """
        with self.lock:
            # Find utterances belonging to this chunk
            chunk_utts = [u for u in self._utterances if chunk_id in u.get("source_chunks", [])]

            if not aligned_segments or not chunk_utts:
                return

            # Match aligned segments with provisional utterances
            for seg in aligned_segments:
                spk_raw = seg.get("speaker", "UNKNOWN")
                spk_resolved = self._role_mapping.get(spk_raw, spk_raw).upper()

                # Find best matching utterance by time overlap
                best_utt = None
                best_overlap = 0.0
                for u in chunk_utts:
                    ov_start = max(u["start"], seg["start"])
                    ov_end = min(u["end"], seg["end"])
                    ov = max(0.0, ov_end - ov_start)
                    if ov > best_overlap:
                        best_overlap = ov
                        best_utt = u

                if best_utt and best_overlap > 0:
                    best_utt["speaker_raw"] = spk_raw
                    best_utt["speaker"] = spk_resolved if spk_resolved != "UNKNOWN" else best_utt["speaker"]
                    best_utt["overlap"] = seg.get("overlap", best_utt.get("overlap", False))
                    best_utt["confidence"] = 0.85
                    if best_utt["status"] == "provisional" and spk_resolved != "UNKNOWN":
                        best_utt["status"] = "diarized"

    def apply_window_refinement(self, window_start: float, window_end: float, refined_turns: List[Dict]):
        """
        State C (3-Chunk Window Contextual Refinement):
        Applies refined turns from Groq/LLM or local rule engine to the window [window_start, window_end].
        Merges consecutive same-speaker turns, splits genuine speaker changes, and preserves stable IDs.
        """
        with self.lock:
            if not refined_turns:
                return

            # Identify which utterances fall within or intersect this window
            indices_in_window = []
            for i, u in enumerate(self._utterances):
                # An utterance is in the window if it overlaps significantly with [window_start, window_end]
                if u["end"] > window_start + 0.1 and u["start"] < window_end - 0.1:
                    indices_in_window.append(i)

            if not indices_in_window:
                return

            # Keep existing IDs where possible to preserve UI stability
            existing_ids = [self._utterances[i]["utterance_id"] for i in indices_in_window]
            all_source_chunks = set()
            for i in indices_in_window:
                all_source_chunks.update(self._utterances[i].get("source_chunks", []))

            # Build new refined utterances for this window
            new_window_utts = []
            for k, turn in enumerate(refined_turns):
                spk = str(turn.get("speaker", "UNKNOWN")).upper()
                text = str(turn.get("text", "")).strip()
                if not text:
                    continue

                uid = existing_ids[k] if k < len(existing_ids) else self._generate_id()
                raw_spk = turn.get("speaker_raw", spk)

                new_window_utts.append({
                    "conversation_id": self.conversation_id,
                    "utterance_id": uid,
                    "speaker": spk,
                    "speaker_raw": raw_spk,
                    "start": round(float(turn.get("start", window_start)), 2),
                    "end": round(float(turn.get("end", window_end)), 2),
                    "text": text,
                    "source_chunks": sorted(list(all_source_chunks)),
                    "status": "refined",
                    "confidence": 0.95,
                    "overlap": bool(turn.get("overlap", False)),
                })

            # Replace the window segment in self._utterances
            first_idx = indices_in_window[0]
            last_idx = indices_in_window[-1]

            self._utterances = (
                self._utterances[:first_idx]
                + new_window_utts
                + self._utterances[last_idx + 1:]
            )

            # Ensure chronological order by start time
            self._utterances.sort(key=lambda x: (x["start"], x["end"]))

    def merge_consecutive_same_speaker(self, max_gap_seconds: float = 3.5):
        """
        Section 12: Merge consecutive utterances from the same speaker into one conversational turn.
        Section 13: Never merge across different speakers.
        """
        with self.lock:
            if len(self._utterances) < 2:
                return

            merged = []
            curr = dict(self._utterances[0])

            for nxt in self._utterances[1:]:
                same_speaker = (
                    curr["speaker"] == nxt["speaker"]
                    and curr["speaker"] not in ("Pending...", "UNKNOWN")
                )
                gap = nxt["start"] - curr["end"]

                if same_speaker and gap <= max_gap_seconds and not curr.get("overlap") and not nxt.get("overlap"):
                    # Merge nxt into curr
                    curr_text = curr["text"].rstrip()
                    nxt_text = nxt["text"].lstrip()
                    # Add space or punctuation
                    if curr_text and not curr_text.endswith((".", "?", "!", ",", ";")):
                        curr["text"] = f"{curr_text}. {nxt_text}"
                    else:
                        curr["text"] = f"{curr_text} {nxt_text}"

                    curr["end"] = max(curr["end"], nxt["end"])
                    curr_chunks = set(curr.get("source_chunks", []))
                    curr_chunks.update(nxt.get("source_chunks", []))
                    curr["source_chunks"] = sorted(list(curr_chunks))
                    # Keep status of most progressed
                    if nxt["status"] == "final" or curr["status"] == "final":
                        curr["status"] = "final"
                    elif nxt["status"] == "refined" or curr["status"] == "refined":
                        curr["status"] = "refined"
                else:
                    merged.append(curr)
                    curr = dict(nxt)

            merged.append(curr)
            self._utterances = merged

    def mark_all_final(self):
        """Finalize all utterances when recording ends."""
        with self.lock:
            self.merge_consecutive_same_speaker()
            for u in self._utterances:
                if u["speaker"] == "Pending...":
                    # Fallback to UNKNOWN / DOCTOR if pending
                    u["speaker"] = "DOCTOR"
                u["status"] = "final"

    def get_utterances(self) -> List[Dict]:
        """Return a snapshot copy of current canonical utterances."""
        with self.lock:
            return [copy.deepcopy(u) for u in self._utterances]

    def to_team_b_segments(self) -> List[Dict]:
        """Convert canonical utterances to Team B compatible segments format."""
        with self.lock:
            team_b = []
            for u in self._utterances:
                seg = {
                    "speaker": u["speaker"].upper(),
                    "start_time": u["start"],
                    "end_time": u["end"],
                    "text": u["text"],
                    "confidence": u.get("confidence", 0.95),
                    "utterance_id": u["utterance_id"],
                    "_internal": {
                        "original_speaker": u.get("speaker_raw", u["speaker"]),
                        "status": u.get("status", "final"),
                        "overlap": u.get("overlap", False),
                        "source_chunks": u.get("source_chunks", []),
                    }
                }
                team_b.append(seg)
            return team_b
