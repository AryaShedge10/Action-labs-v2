"""
Merge diarization results with Whisper transcript segments.
"""
from typing import List, Dict, Optional


def calculate_overlap(seg_start: float, seg_end: float, turn_start: float, turn_end: float) -> float:
    """
    Calculate temporal overlap between a segment and a diarization turn.
    
    Args:
        seg_start: Segment start time
        seg_end: Segment end time
        turn_start: Turn start time
        turn_end: Turn end time
        
    Returns:
        Overlap duration in seconds
    """
    overlap_start = max(seg_start, turn_start)
    overlap_end = min(seg_end, turn_end)
    overlap = max(0.0, overlap_end - overlap_start)
    return overlap


def split_segment_at_boundaries(
    segment: Dict,
    diarization_turns: List[Dict],
    max_turn_distance: float = 1.0
) -> Optional[List[Dict]]:
    """
    Split a Whisper segment at diarization speaker boundaries using word timestamps.
    
    Assigns each word to the best matching diarization turn based on word midpoint.
    Then groups consecutive words with the same speaker. If multiple speakers are
    present, returns clean sub-segments with no dropped words.
    
    Args:
        segment: Whisper segment with start, end, text, and optionally words
        diarization_turns: List of diarization turns
        max_turn_distance: Maximum distance in seconds from word to turn boundary
        
    Returns:
        List of sub-segments with speaker labels, or None if no split needed
    """
    seg_start = segment["start"]
    seg_end = segment["end"]
    
    words = segment.get("words", [])
    if not words:
        return None

    # Filter turns that are relevant to this segment (overlapping or within 1.0s)
    relevant_turns = [
        t for t in diarization_turns
        if calculate_overlap(seg_start, seg_end, t["start"], t["end"]) > 0 or
           (t["start"] <= seg_end + max_turn_distance and t["end"] >= seg_start - max_turn_distance)
    ]

    if not relevant_turns:
        return None

    # If all relevant turns have the same speaker, no split is needed
    unique_turn_speakers = set(t["speaker"] for t in relevant_turns)
    if len(unique_turn_speakers) <= 1:
        return None

    # Assign each word to the most suitable turn
    word_speakers = []
    for w in words:
        w_start = w.get("start", seg_start)
        w_end = w.get("end", seg_end)
        w_mid = (w_start + w_end) / 2.0

        best_turn = None
        best_score = -float("inf")

        for turn in relevant_turns:
            t_start = turn["start"]
            t_end = turn["end"]

            # Direct containment is best score
            if t_start <= w_mid <= t_end:
                # Give higher priority to turns where the word is well within the boundary
                margin = min(w_mid - t_start, t_end - w_mid)
                score = 100.0 + margin
            else:
                # Word is outside turn: compute distance penalty
                dist = min(abs(w_mid - t_start), abs(w_mid - t_end))
                score = -dist

            if score > best_score:
                best_score = score
                best_turn = turn

        word_spk = best_turn["speaker"] if best_turn else "UNKNOWN"
        word_speakers.append((w, word_spk))

    # Check if there are actually multiple speakers assigned across the words
    assigned_speakers = set(spk for _, spk in word_speakers if spk != "UNKNOWN")
    if len(assigned_speakers) <= 1:
        return None

    # Group consecutive words with the same speaker
    sub_segments = []
    curr_speaker = None
    curr_words = []

    for w, spk in word_speakers:
        if curr_speaker is None:
            curr_speaker = spk
            curr_words = [w]
        elif spk == curr_speaker:
            curr_words.append(w)
        else:
            # Emit sub-segment
            sub_text = " ".join(cw.get("word", "").strip() for cw in curr_words).strip()
            if sub_text:
                sub_segments.append({
                    "start": round(curr_words[0].get("start", seg_start), 2),
                    "end": round(curr_words[-1].get("end", seg_end), 2),
                    "text": sub_text,
                    "speaker": curr_speaker,
                    "words": curr_words
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
                "words": curr_words
            })

    # Only return if we actually split into multiple distinct segments
    if len(sub_segments) > 1:
        return sub_segments

    return None


def merge_transcript_with_speakers(
    whisper_segments: List[Dict],
    diarization_turns: List[Dict],
    long_segment_threshold: float = 1.5
) -> List[Dict]:
    """
    Merge Whisper transcript segments with diarization speaker turns.
    
    For each Whisper segment, finds the diarization turn with maximum temporal
    overlap and assigns that speaker label. Falls back to "UNKNOWN" if no
    turn overlaps the segment.
    
    Long segments (>8s) that overlap multiple speakers are split at diarization
    boundaries using word-level timestamps.
    
    Args:
        whisper_segments: List of dicts with keys: start, end, text, optionally words
        diarization_turns: List of dicts with keys: start, end, speaker
        long_segment_threshold: Threshold in seconds for considering a segment "long"
        
    Returns:
        List of merged segments with added "speaker" field
    """
    if not diarization_turns:
        # No diarization data - assign UNKNOWN to all
        print("  No diarization data available, assigning UNKNOWN to all segments")
        return [
            {**seg, "speaker": "UNKNOWN"}
            for seg in whisper_segments
        ]
    
    # Sort diarization turns by start time to ensure proper ordering
    diarization_turns = sorted(diarization_turns, key=lambda x: x["start"])
    
    # Debug: Print diarization turns
    print(f"\n  DEBUG: Diarization turns ({len(diarization_turns)} total):")
    for i, turn in enumerate(diarization_turns):
        print(f"    Turn {i}: {turn['speaker']} [{turn['start']:.2f}s - {turn['end']:.2f}s] (duration: {turn['end'] - turn['start']:.2f}s)")
    
    # Count unique speakers in diarization
    unique_diarization_speakers = set(turn["speaker"] for turn in diarization_turns)
    print(f"  DEBUG: Unique speakers in diarization: {unique_diarization_speakers}")
    
    merged = []
    split_count = 0
    
    print(f"\n  DEBUG: Merging {len(whisper_segments)} Whisper segments with diarization:")
    
    for seg_idx, seg in enumerate(whisper_segments):
        seg_start = seg["start"]
        seg_end = seg["end"]
        seg_duration = seg_end - seg_start
        
        print(f"    Segment {seg_idx}: [{seg_start:.2f}s - {seg_end:.2f}s] ({seg_duration:.2f}s)")
        print(f"      Text: {seg['text'][:80]}")
        
        # Try to split segments that span multiple speakers (even short ones)
        # by checking if they have meaningful overlap with more than one speaker turn
        sub_segments = split_segment_at_boundaries(seg, diarization_turns)
        if sub_segments:
            print(f"      [OK] Split into {len(sub_segments)} sub-segments:")
            for sub_idx, sub_seg in enumerate(sub_segments):
                print(f"        Sub {sub_idx}: {sub_seg['speaker']} [{sub_seg['start']:.2f}s - {sub_seg['end']:.2f}s] - {sub_seg['text'][:60]}")
            merged.extend(sub_segments)
            split_count += 1
            continue
        
        # Find turn with maximum overlap (standard behavior)
        best_speaker = "UNKNOWN"
        max_overlap = 0.0
        best_turn_idx = None
        
        # Debug: Show overlap calculation for each turn
        overlap_details = []
        
        for turn_idx, turn in enumerate(diarization_turns):
            overlap = calculate_overlap(
                seg_start, seg_end,
                turn["start"], turn["end"]
            )
            
            overlap_details.append({
                "turn_idx": turn_idx,
                "speaker": turn["speaker"],
                "turn_range": f"[{turn['start']:.2f}-{turn['end']:.2f}]",
                "overlap": overlap
            })
            
            if overlap > max_overlap:
                max_overlap = overlap
                best_speaker = turn["speaker"]
                best_turn_idx = turn_idx
        
        # Show all overlaps for debugging
        print(f"      Overlap analysis (segment overlaps {len([d for d in overlap_details if d['overlap'] > 0])} turn(s)):")
        for detail in overlap_details:
            if detail["overlap"] > 0:
                print(f"        Turn {detail['turn_idx']} ({detail['speaker']} {detail['turn_range']}): {detail['overlap']:.2f}s overlap")
        
        if best_turn_idx is None:
            print(f"      -> Assigned to UNKNOWN (no overlapping turns found)")
        else:
            print(f"      -> Assigned to {best_speaker} (turn {best_turn_idx}, max overlap: {max_overlap:.2f}s)")
        
        # Create merged segment
        merged_seg = {
            "start": seg_start,
            "end": seg_end,
            "text": seg["text"],
            "speaker": best_speaker
        }
        
        merged.append(merged_seg)
    
    # Post-merge sanity check
    unique_merged_speakers = set(seg["speaker"] for seg in merged)
    unique_merged_speakers.discard("UNKNOWN")
    
    print(f"\n  DEBUG: Merge results:")
    print(f"    Diarization detected: {len(unique_diarization_speakers)} speaker(s): {unique_diarization_speakers}")
    print(f"    Merge produced: {len(unique_merged_speakers)} speaker(s): {unique_merged_speakers}")
    
    # Detailed speaker distribution
    speaker_segment_counts = {}
    for seg in merged:
        speaker = seg["speaker"]
        speaker_segment_counts[speaker] = speaker_segment_counts.get(speaker, 0) + 1
    print(f"    Segment distribution: {speaker_segment_counts}")
    
    if len(unique_merged_speakers) < len(unique_diarization_speakers):
        print(f"    [WARN]  WARNING: Merge collapsed {len(unique_diarization_speakers)} detected speakers into {len(unique_merged_speakers)} - possible merge bug!")
        missing_speakers = unique_diarization_speakers - unique_merged_speakers
        print(f"    Missing speakers: {missing_speakers}")
        
        # Additional debug: show which turns were never matched
        matched_turn_indices = set()
        for seg in merged:
            # Find which turn this segment matched
            for turn_idx, turn in enumerate(diarization_turns):
                overlap = calculate_overlap(
                    seg["start"], seg["end"],
                    turn["start"], turn["end"]
                )
                if overlap > 0 and turn["speaker"] == seg["speaker"]:
                    matched_turn_indices.add(turn_idx)
        
        unmatched_turns = [i for i in range(len(diarization_turns)) if i not in matched_turn_indices]
        if unmatched_turns:
            print(f"    Unmatched turns: {unmatched_turns}")
            for idx in unmatched_turns:
                turn = diarization_turns[idx]
                print(f"      Turn {idx}: {turn['speaker']} [{turn['start']:.2f}-{turn['end']:.2f}]")
    
    if split_count > 0:
        print(f"  Split {split_count} long segment(s) at diarization boundaries")
    
    return merged
