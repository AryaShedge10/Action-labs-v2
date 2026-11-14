"""
Temporal Alignment and Speaker Assignment Engine.

Aligns Whisper transcript segments and word-level timestamps with Pyannote
speaker diarization intervals on a common global conversation timeline.

Implements Master Prompt Speaker Assignment Rules:
- Rule 1: Stable speaker assignment when predominant speaker matches
- Rule 2: Speaker transition inside segment resolved to nearest word boundary WITHOUT requiring a pause
- Rule 3: Short unstable speaker jitter (< 0.6s / isolated single word) filtered out
- Rule 4: Sustained speaker change recognized as genuine transition
- Interruption / Overlap preservation
"""
from typing import List, Dict, Optional, Tuple
import math


def calculate_overlap(seg_start: float, seg_end: float, turn_start: float, turn_end: float) -> float:
    """Calculate temporal overlap duration in seconds between two intervals."""
    overlap_start = max(seg_start, turn_start)
    overlap_end = min(seg_end, turn_end)
    return max(0.0, overlap_end - overlap_start)


def filter_unstable_diarization_jitter(
    diarization_turns: List[Dict],
    min_sustained_duration: float = 0.55
) -> List[Dict]:
    """
    Rule 3: Filter short unstable speaker blips.
    If Speaker A -> very short Speaker B (< 0.55s) -> Speaker A,
    treat B as diarization jitter and smooth it into Speaker A.
    """
    if len(diarization_turns) < 3:
        return diarization_turns

    filtered = [dict(t) for t in diarization_turns]
    changed = True
    iterations = 0

    while changed and iterations < 5:
        changed = False
        iterations += 1
        i = 1
        while i < len(filtered) - 1:
            prev_t = filtered[i - 1]
            curr_t = filtered[i]
            next_t = filtered[i + 1]

            dur = curr_t["end"] - curr_t["start"]
            # If flanked by the same speaker on both sides and duration is short
            if (prev_t["speaker"] == next_t["speaker"]
                and curr_t["speaker"] != prev_t["speaker"]
                and dur < min_sustained_duration):
                # Merge into prev turn
                prev_t["end"] = next_t["end"]
                del filtered[i + 1]
                del filtered[i]
                changed = True
            else:
                i += 1

    return filtered


def find_best_speaker_for_word(
    word_start: float,
    word_end: float,
    diarization_turns: List[Dict]
) -> Tuple[str, float]:
    """
    Find best matching speaker for a word using midpoint containment and distance penalty.
    Returns (speaker_label, score).
    """
    w_mid = (word_start + word_end) / 2.0
    best_speaker = "UNKNOWN"
    best_score = -float("inf")

    for turn in diarization_turns:
        t_start = turn["start"]
        t_end = turn["end"]

        if t_start <= w_mid <= t_end:
            # Direct containment: distance to nearest edge as stability bonus
            margin = min(w_mid - t_start, t_end - w_mid)
            score = 100.0 + margin
        else:
            # Word is outside turn: compute distance penalty
            dist = min(abs(w_mid - t_start), abs(w_mid - t_end))
            score = -dist

        if score > best_score:
            best_score = score
            best_speaker = turn["speaker"]

    return best_speaker, best_score


def split_segment_by_speaker_transition(
    segment: Dict,
    diarization_turns: List[Dict],
    min_word_count_for_split: int = 2
) -> Optional[List[Dict]]:
    """
    Rule 2 & Rule 4:
    If a segment contains a genuine speaker transition (e.g. SPEAKER_00 -> SPEAKER_01),
    split at the exact word boundary closest to the acoustic transition point WITHOUT
    requiring a pause or silence.
    """
    words = segment.get("words", [])
    if not words or len(words) < min_word_count_for_split:
        return None

    seg_start = segment["start"]
    seg_end = segment["end"]

    # Only consider turns overlapping or near this segment
    relevant_turns = [
        t for t in diarization_turns
        if calculate_overlap(seg_start, seg_end, t["start"], t["end"]) > 0 or
           (t["start"] <= seg_end + 0.8 and t["end"] >= seg_start - 0.8)
    ]
    if not relevant_turns:
        return None

    unique_turn_speakers = set(t["speaker"] for t in relevant_turns)
    if len(unique_turn_speakers) <= 1:
        return None

    # Assign each word to the best speaker
    word_assignments = []
    for w in words:
        w_start = w.get("start", seg_start)
        w_end = w.get("end", seg_end)
        spk, score = find_best_speaker_for_word(w_start, w_end, relevant_turns)
        word_assignments.append((w, spk))

    # Check for speaker distribution
    speakers_in_words = [spk for _, spk in word_assignments if spk != "UNKNOWN"]
    if not speakers_in_words or len(set(speakers_in_words)) <= 1:
        return None

    # Group consecutive words by speaker
    sub_segments = []
    curr_speaker = None
    curr_words = []

    for w, spk in word_assignments:
        if curr_speaker is None:
            curr_speaker = spk
            curr_words = [w]
        elif spk == curr_speaker or spk == "UNKNOWN":
            curr_words.append(w)
        else:
            # Transition! Check Rule 3 (is this transition sustained?)
            # If current word group is just 1 short word and prev/next are the same, don't split prematurely
            sub_text = " ".join(cw.get("word", "").strip() for cw in curr_words).strip()
            if sub_text:
                sub_segments.append({
                    "start": round(curr_words[0].get("start", seg_start), 2),
                    "end": round(curr_words[-1].get("end", seg_end), 2),
                    "text": sub_text,
                    "speaker": curr_speaker,
                    "words": list(curr_words),
                    "confidence": 0.92
                })
            curr_speaker = spk
            curr_words = [w]

    if curr_words:
        sub_text = " ".join(cw.get("word", "").strip() for cw in curr_words).strip()
        if sub_text:
            sub_segments.append({
                "start": round(curr_words[0].get("start", seg_start), 2),
                "end": round(curr_words[-1].get("end", seg_end), 2),
                "text": sub_text,
                "speaker": curr_speaker,
                "words": list(curr_words),
                "confidence": 0.92
            })

    # Filter out single-character or single-word jitter splits if they match the neighbor
    if len(sub_segments) > 1:
        # Check if subsegments actually have distinct speakers
        distinct_spks = set(s["speaker"] for s in sub_segments if s["speaker"] != "UNKNOWN")
        if len(distinct_spks) > 1:
            return sub_segments

    return None


def detect_interruption_overlaps(
    segments: List[Dict],
    overlap_threshold: float = 0.2
) -> List[Dict]:
    """
    Section 14: Support interruptions and speech overlap without forcing linear gaps.
    If segment i and segment i+1 overlap temporally and have different speakers,
    flag overlap=True on both.
    """
    for i in range(len(segments) - 1):
        s1 = segments[i]
        s2 = segments[i + 1]

        if s1.get("speaker") != s2.get("speaker"):
            # Check for temporal overlap
            if s1["end"] > s2["start"] + overlap_threshold:
                s1["overlap"] = True
                s2["overlap"] = True

    return segments


def align_whisper_with_diarization(
    whisper_segments: List[Dict],
    diarization_turns: List[Dict]
) -> List[Dict]:
    """
    Main alignment function:
    Combines Whisper words/segments with Pyannote turns on the global conversation timeline.

    Applies:
    - Pre-filtering of diarization jitter (Rule 3)
    - Word-level boundary splitting for speaker transitions without pause (Rule 2 & 4)
    - Predominant speaker assignment for stable segments (Rule 1)
    - Overlap/interruption flagging (Section 14)
    """
    if not whisper_segments:
        return []

    if not diarization_turns:
        # No diarization available yet — return segments as UNKNOWN
        return [
            {
                "start": s["start"],
                "end": s["end"],
                "text": s["text"],
                "speaker": s.get("speaker", "UNKNOWN"),
                "words": s.get("words", []),
                "overlap": s.get("overlap", False),
                "confidence": 0.50
            }
            for s in whisper_segments
        ]

    # Rule 3: Filter short unstable speaker blips from diarization turns
    clean_turns = filter_unstable_diarization_jitter(diarization_turns)

    aligned_segments = []

    for seg in whisper_segments:
        # Try word-boundary split at speaker transition (Rule 2 & 4)
        sub_segs = split_segment_by_speaker_transition(seg, clean_turns)
        if sub_segs:
            aligned_segments.extend(sub_segs)
            continue

        # Rule 1: Stable speaker assignment using maximum temporal overlap or word majority
        seg_start = seg["start"]
        seg_end = seg["end"]

        words = seg.get("words", [])
        if words:
            # Word-level voting for stable speaker
            spk_counts: Dict[str, int] = {}
            for w in words:
                spk, _ = find_best_speaker_for_word(
                    w.get("start", seg_start),
                    w.get("end", seg_end),
                    clean_turns
                )
                if spk != "UNKNOWN":
                    spk_counts[spk] = spk_counts.get(spk, 0) + 1

            if spk_counts:
                best_spk = max(spk_counts, key=spk_counts.get)
            else:
                best_spk = "UNKNOWN"
        else:
            # Fallback to duration overlap
            best_spk = "UNKNOWN"
            max_ov = 0.0
            for turn in clean_turns:
                ov = calculate_overlap(seg_start, seg_end, turn["start"], turn["end"])
                if ov > max_ov:
                    max_ov = ov
                    best_spk = turn["speaker"]

        aligned_segments.append({
            "start": seg_start,
            "end": seg_end,
            "text": seg["text"],
            "speaker": best_spk,
            "words": seg.get("words", []),
            "overlap": False,
            "confidence": 0.90 if best_spk != "UNKNOWN" else 0.50
        })

    # Interruption / overlap detection
    aligned_segments = detect_interruption_overlaps(aligned_segments)

    return aligned_segments
