"""
Unit tests for UtteranceManager.
"""
import pytest
from app.services.utterance_manager import UtteranceManager


def test_add_provisional_chunks():
    mgr = UtteranceManager("sess_123")
    segs = [
        {"start": 0.0, "end": 2.1, "text": "Good morning."},
        {"start": 2.2, "end": 4.5, "text": "How can I help you today?"}
    ]
    new_utts = mgr.add_provisional_chunks(chunk_id=0, segments=segs)
    assert len(new_utts) == 2
    assert new_utts[0]["speaker"] == "Pending..."
    assert new_utts[0]["status"] == "provisional"
    assert new_utts[0]["utterance_id"] == "utt_00001"
    assert new_utts[1]["utterance_id"] == "utt_00002"


def test_apply_aligned_segments():
    mgr = UtteranceManager("sess_123")
    mgr.set_role_mapping({"SPEAKER_00": "DOCTOR", "SPEAKER_01": "PATIENT"})
    mgr.add_provisional_chunks(chunk_id=0, segments=[
        {"start": 0.0, "end": 2.0, "text": "Hello doctor."}
    ])
    aligned = [
        {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_01", "overlap": False}
    ]
    mgr.apply_aligned_segments(chunk_id=0, aligned_segments=aligned)
    utts = mgr.get_utterances()
    assert utts[0]["speaker"] == "PATIENT"
    assert utts[0]["speaker_raw"] == "SPEAKER_01"


def test_same_speaker_merging():
    """Section 12: Consecutive same-speaker turns are merged into one."""
    mgr = UtteranceManager("sess_123")
    mgr._utterances = [
        {
            "conversation_id": "sess_123",
            "utterance_id": "utt_00001",
            "speaker": "PATIENT",
            "speaker_raw": "SPEAKER_01",
            "start": 0.0,
            "end": 2.0,
            "text": "Not feeling good.",
            "source_chunks": [0],
            "status": "refined",
            "overlap": False
        },
        {
            "conversation_id": "sess_123",
            "utterance_id": "utt_00002",
            "speaker": "PATIENT",
            "speaker_raw": "SPEAKER_01",
            "start": 2.2,
            "end": 4.5,
            "text": "I have some pain in my stomach.",
            "source_chunks": [1],
            "status": "refined",
            "overlap": False
        },
        {
            "conversation_id": "sess_123",
            "utterance_id": "utt_00003",
            "speaker": "PATIENT",
            "speaker_raw": "SPEAKER_01",
            "start": 4.6,
            "end": 6.8,
            "text": "Which bothers me for a few days.",
            "source_chunks": [1],
            "status": "refined",
            "overlap": False
        }
    ]

    mgr.merge_consecutive_same_speaker()
    utts = mgr.get_utterances()

    assert len(utts) == 1
    assert utts[0]["speaker"] == "PATIENT"
    assert "Not feeling good" in utts[0]["text"]
    assert "pain in my stomach" in utts[0]["text"]
    assert "bothers me for a few days" in utts[0]["text"]
    assert utts[0]["start"] == 0.0
    assert utts[0]["end"] == 6.8


def test_different_speaker_splitting():
    """Section 13: Speech is split when actual speaker changes."""
    mgr = UtteranceManager("sess_123")
    mgr._utterances = [
        {
            "conversation_id": "sess_123",
            "utterance_id": "utt_00001",
            "speaker": "PATIENT",
            "speaker_raw": "SPEAKER_01",
            "start": 0.0,
            "end": 2.0,
            "text": "I have pain in my stomach.",
            "source_chunks": [0],
            "status": "refined",
            "overlap": False
        },
        {
            "conversation_id": "sess_123",
            "utterance_id": "utt_00002",
            "speaker": "DOCTOR",
            "speaker_raw": "SPEAKER_00",
            "start": 2.2,
            "end": 4.5,
            "text": "How long has it been happening?",
            "source_chunks": [1],
            "status": "refined",
            "overlap": False
        }
    ]

    mgr.merge_consecutive_same_speaker()
    utts = mgr.get_utterances()

    assert len(utts) == 2
    assert utts[0]["speaker"] == "PATIENT"
    assert utts[1]["speaker"] == "DOCTOR"
