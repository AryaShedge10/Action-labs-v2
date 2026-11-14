"""
Unit tests for 3-chunk window contextual refinement.
"""
import pytest
from app.services.llm_correction import local_rule_refine_window, _validate_anti_hallucination


def test_local_rule_refine_window_same_speaker_merging():
    """Section 21: Same speaker across multiple chunks is merged into one utterance."""
    payload = {
        "conversation_id": "test_conv",
        "window": {"start": 0.0, "end": 15.0},
        "utterances": [
            {
                "chunk_id": 0,
                "text": "Not feeling good.",
                "start": 0.5,
                "end": 2.0,
                "speaker": "SPEAKER_01"
            },
            {
                "chunk_id": 1,
                "text": "I have some pain in my stomach",
                "start": 5.2,
                "end": 7.5,
                "speaker": "SPEAKER_01"
            },
            {
                "chunk_id": 2,
                "text": "which bothers me for a few days.",
                "start": 10.1,
                "end": 12.8,
                "speaker": "SPEAKER_01"
            }
        ]
    }

    result = local_rule_refine_window(payload)
    turns = result.get("turns", [])

    assert len(turns) == 1
    assert turns[0]["speaker"] == "PATIENT"
    assert "Not feeling good" in turns[0]["text"]
    assert "pain in my stomach" in turns[0]["text"]
    assert "bothers me for a few days" in turns[0]["text"]


def test_local_rule_refine_window_different_speaker_splitting():
    """Section 22: Speaker changes between chunks are kept separate."""
    payload = {
        "conversation_id": "test_conv",
        "window": {"start": 0.0, "end": 15.0},
        "utterances": [
            {
                "chunk_id": 0,
                "text": "Good morning, Mr. Johnson.",
                "start": 0.5,
                "end": 2.5,
                "speaker": "SPEAKER_00"
            },
            {
                "chunk_id": 1,
                "text": "Good morning, doctor.",
                "start": 5.5,
                "end": 7.0,
                "speaker": "SPEAKER_01"
            },
            {
                "chunk_id": 2,
                "text": "How are you feeling today?",
                "start": 10.5,
                "end": 12.5,
                "speaker": "SPEAKER_00"
            }
        ]
    }

    result = local_rule_refine_window(payload)
    turns = result.get("turns", [])

    assert len(turns) == 3
    assert turns[0]["speaker"] == "DOCTOR"
    assert turns[1]["speaker"] == "PATIENT"
    assert turns[2]["speaker"] == "DOCTOR"


def test_anti_hallucination_check():
    """Section 25: Hallucinated clinical terms are flagged as invalid."""
    input_utts = [
        {"text": "pain in stomach"}
    ]
    # Normal output with same words
    valid_output = [
        {"text": "I have pain in stomach."}
    ]
    assert _validate_anti_hallucination(input_utts, valid_output) is True

    # Hallucinated medical diagnosis
    hallucinated_output = [
        {"text": "Patient has severe acute pancreatitis and appendicitis with myocardial infarction."}
    ]
    assert _validate_anti_hallucination(input_utts, hallucinated_output) is False
