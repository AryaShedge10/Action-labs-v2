"""
Unit Tests: Audio Preprocessor, Speaker Role Classification, and Transcript Formatter.
"""
import pytest
import sys
import numpy as np
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "services" / "transcription"))

from services.transcription.app.audio.preprocessing import AudioPreprocessor
from services.transcription.app.services.roles import detect_speaker_roles
from services.transcription.app.transcription.transcript_formatter import TranscriptFormatter


def test_audio_preprocessing_resampling_and_channels():
    """Verify AudioPreprocessor converts stereo 48kHz to mono 16kHz float32."""
    preprocessor = AudioPreprocessor(target_sample_rate=16000)

    # Synthetic stereo 48kHz audio (1 second)
    sample_rate = 48000
    t = np.linspace(0, 1, sample_rate, endpoint=False)
    left = 0.5 * np.sin(2 * np.pi * 440 * t)
    right = 0.3 * np.sin(2 * np.pi * 880 * t)
    stereo_audio = np.vstack([left, right]).T

    processed = preprocessor.preprocess(stereo_audio, sample_rate)

    # Must be 1D mono
    assert processed.ndim == 1
    # Sample rate converted to 16kHz (1 second = 16000 samples)
    assert abs(len(processed) - 16000) < 50
    # Must be float32 in [-1.0, 1.0]
    assert processed.dtype == np.float32
    assert np.max(np.abs(processed)) <= 1.0


def test_speaker_role_heuristic_classification():
    """Verify content-based heuristic detects DOCTOR vs PATIENT without assuming first speaker is Doctor."""
    # Patient speaks first
    dialogue = [
        {"speaker": "SPEAKER_00", "text": "Hello doctor, my throat has been hurting and I have had a high fever for three days."},
        {"speaker": "SPEAKER_01", "text": "Good morning. Let me examine your throat and listen to your breathing. Any chest pain?"},
        {"speaker": "SPEAKER_00", "text": "No chest pain, just severe throat pain when swallowing."},
        {"speaker": "SPEAKER_01", "text": "Your tonsils are enlarged. I am prescribing amoxicillin 500mg three times daily."},
    ]

    roles = detect_speaker_roles(dialogue)
    # SPEAKER_00 should be Patient, SPEAKER_01 should be Doctor
    assert roles.get("SPEAKER_00") == "Patient"
    assert roles.get("SPEAKER_01") == "Doctor"


def test_transcript_formatter_dual_timestamp_support():
    """Verify TranscriptFormatter produces both start_time/end_time and start/end."""
    formatter = TranscriptFormatter()
    raw_segments = [
        {"start": 0.5, "end": 3.2, "text": "Good morning.", "confidence": 0.98},
        {"start": 3.5, "end": 7.0, "text": "I feel sick.", "confidence": 0.95},
    ]
    labels = {0: "DOCTOR", 1: "PATIENT"}

    res = formatter.format(raw_segments, session_id="TEST-SID", speaker_labels=labels)
    assert res["consultation_id"] == "TEST-SID"
    assert len(res["segments"]) == 2

    seg0 = res["segments"][0]
    assert seg0["speaker"] == "DOCTOR"
    assert seg0["start"] == 0.5
    assert seg0["start_time"] == 0.5
    assert seg0["end"] == 3.2
    assert seg0["end_time"] == 3.2

