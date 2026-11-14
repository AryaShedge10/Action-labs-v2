"""
Unit tests for alignment engine (Rules 1-4, interruptions, same-speaker merging).
"""
import pytest
from app.services.alignment import (
    calculate_overlap,
    filter_unstable_diarization_jitter,
    split_segment_by_speaker_transition,
    align_whisper_with_diarization,
    detect_interruption_overlaps
)


def test_rule_1_stable_speaker():
    """Rule 1: Segment where words match single speaker is assigned cleanly."""
    whisper_segs = [{
        "start": 0.0,
        "end": 2.5,
        "text": "Good morning doctor.",
        "words": [
            {"word": "Good", "start": 0.0, "end": 0.5},
            {"word": "morning", "start": 0.6, "end": 1.2},
            {"word": "doctor.", "start": 1.3, "end": 2.5},
        ]
    }]
    diarization_turns = [
        {"start": 0.0, "end": 3.0, "speaker": "SPEAKER_01"}
    ]
    aligned = align_whisper_with_diarization(whisper_segs, diarization_turns)
    assert len(aligned) == 1
    assert aligned[0]["speaker"] == "SPEAKER_01"
    assert aligned[0]["text"] == "Good morning doctor."


def test_rule_2_speaker_transition_no_pause():
    """Rule 2: Speaker transition inside a segment splits at word boundary without pause."""
    whisper_segs = [{
        "start": 0.0,
        "end": 4.0,
        "text": "I have stomach pain How long has it been?",
        "words": [
            {"word": "I", "start": 0.0, "end": 0.3},
            {"word": "have", "start": 0.3, "end": 0.7},
            {"word": "stomach", "start": 0.7, "end": 1.2},
            {"word": "pain", "start": 1.2, "end": 1.8},
            # Transition happens at 1.9s with no pause
            {"word": "How", "start": 1.9, "end": 2.3},
            {"word": "long", "start": 2.3, "end": 2.7},
            {"word": "has", "start": 2.7, "end": 3.0},
            {"word": "it", "start": 3.0, "end": 3.3},
            {"word": "been?", "start": 3.3, "end": 4.0},
        ]
    }]
    diarization_turns = [
        {"start": 0.0, "end": 1.85, "speaker": "SPEAKER_01"},  # Patient
        {"start": 1.85, "end": 4.2, "speaker": "SPEAKER_00"}   # Doctor
    ]
    aligned = align_whisper_with_diarization(whisper_segs, diarization_turns)
    assert len(aligned) == 2
    assert aligned[0]["speaker"] == "SPEAKER_01"
    assert aligned[0]["text"] == "I have stomach pain"
    assert aligned[1]["speaker"] == "SPEAKER_00"
    assert aligned[1]["text"] == "How long has it been?"


def test_rule_3_short_unstable_speaker_filtered():
    """Rule 3: Short jitter blip (<0.55s) between same speaker is filtered."""
    turns = [
        {"start": 0.0, "end": 3.0, "speaker": "SPEAKER_00"},
        {"start": 3.0, "end": 3.3, "speaker": "SPEAKER_01"},  # 0.3s blip
        {"start": 3.3, "end": 6.0, "speaker": "SPEAKER_00"}
    ]
    filtered = filter_unstable_diarization_jitter(turns)
    assert len(filtered) == 1
    assert filtered[0]["speaker"] == "SPEAKER_00"
    assert filtered[0]["start"] == 0.0
    assert filtered[0]["end"] == 6.0


def test_rule_4_sustained_speaker_change():
    """Rule 4: Sustained speaker change is retained even without pause."""
    turns = [
        {"start": 0.0, "end": 3.0, "speaker": "SPEAKER_00"},
        {"start": 3.0, "end": 6.0, "speaker": "SPEAKER_01"}   # 3.0s sustained
    ]
    filtered = filter_unstable_diarization_jitter(turns)
    assert len(filtered) == 2
    assert filtered[0]["speaker"] == "SPEAKER_00"
    assert filtered[1]["speaker"] == "SPEAKER_01"


def test_interruption_overlap_detection():
    """Section 14: Overlapping speech turns are tagged with overlap=True."""
    segments = [
        {"speaker": "SPEAKER_01", "start": 10.0, "end": 12.7, "text": "I have pain and"},
        {"speaker": "SPEAKER_00", "start": 12.2, "end": 14.0, "text": "How long has it been?"}
    ]
    tagged = detect_interruption_overlaps(segments, overlap_threshold=0.2)
    assert tagged[0]["overlap"] is True
    assert tagged[1]["overlap"] is True
