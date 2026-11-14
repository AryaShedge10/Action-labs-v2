"""
Create synthetic test audio files for NVIDIA NeMo realtime testing.
tests/realtime_nvidia/scripts/create_test_audio.py

Phase 36: Test recordings covering required test scenarios.
Uses numpy to generate realistic clinical dialogue timing with sine tones.

Run from tests/realtime_nvidia/ with the test venv activated:
    .venv\Scripts\python scripts\create_test_audio.py

Output: recordings/*.wav
"""

import math
import struct
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "recordings"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def sine_tone(freq: float, duration_s: float, amplitude: float = 0.4) -> np.ndarray:
    """Generate a sine tone (simulates speech presence)."""
    n = int(duration_s * SAMPLE_RATE)
    t = np.linspace(0, duration_s, n, endpoint=False)
    return (amplitude * np.sin(2 * math.pi * freq * t)).astype(np.float32)


def silence(duration_s: float) -> np.ndarray:
    """Generate silence."""
    return np.zeros(int(duration_s * SAMPLE_RATE), dtype=np.float32)


def noise(duration_s: float, amplitude: float = 0.02) -> np.ndarray:
    """Generate background noise (simulates clinic ambient noise)."""
    n = int(duration_s * SAMPLE_RATE)
    return (amplitude * np.random.randn(n)).astype(np.float32)


def save_wav(audio: np.ndarray, filename: str):
    """Save float32 audio as 16kHz mono 16-bit WAV."""
    path = OUTPUT_DIR / filename
    # Clip and convert to int16
    audio_clipped = np.clip(audio, -1.0, 1.0)
    audio_int16 = (audio_clipped * 32767).astype(np.int16)

    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_int16.tobytes())

    dur = len(audio) / SAMPLE_RATE
    size_kb = path.stat().st_size / 1024
    print(f"  Saved: {filename} ({dur:.1f}s, {size_kb:.0f} KB)")


def build_clinical_dialogue() -> np.ndarray:
    """
    Phase 36 scenario 1: Normal doctor/patient consultation.
    14 turns, ~40 seconds total.
    Tone frequency differences simulate two speakers:
      Doctor:  220 Hz
      Patient: 330 Hz
    """
    # (speaker_freq, duration_s, gap_after_s)
    turns = [
        (220, 2.0, 0.3),   # Doctor: Good morning...
        (330, 1.5, 0.3),   # Patient: Good morning doctor.
        (220, 2.5, 0.3),   # Doctor: How are you feeling today?
        (330, 3.0, 0.3),   # Patient: I've been having chest pain...
        (220, 1.8, 0.3),   # Doctor: Can you describe it?
        (330, 2.5, 0.3),   # Patient: Center of chest, left arm...
        (220, 1.5, 0.3),   # Doctor: How long has it been?
        (330, 2.0, 0.3),   # Patient: About three days.
        (220, 1.8, 0.3),   # Doctor: Any medications?
        (330, 2.5, 0.4),   # Patient: Metformin 500mg.
        (220, 1.2, 0.3),   # Doctor: Yes.
        (330, 0.8, 0.3),   # Patient: Yes (short answer)
        (220, 2.2, 0.3),   # Doctor: I'll run an ECG today.
        (330, 1.5, 0.5),   # Patient: Thank you doctor.
    ]

    segments = []
    bg = noise(0.1, 0.01)  # subtle background noise
    for freq, dur, gap in turns:
        tone = sine_tone(freq, dur, amplitude=0.35)
        # Add subtle noise to tone
        tone += noise(dur, 0.02)
        segments.append(tone)
        if gap > 0:
            segments.append(silence(gap) + noise(gap, 0.01))

    return np.concatenate(segments)


def build_interruption_test() -> np.ndarray:
    """
    Phase 26/36 scenario 8: Interruption test.
    Doctor starts → Patient interrupts → Doctor continues.
    """
    segments = [
        sine_tone(220, 1.5),             # Doctor: Have you noticed the pain when
        silence(0.05),                    # brief overlap gap
        sine_tone(330, 0.6),             # Patient (interrupting): Yes.
        silence(0.1),
        sine_tone(220, 1.2),             # Doctor: walking upstairs?
        silence(0.3),
        sine_tone(330, 1.5),             # Patient: Yes, exactly.
    ]
    return np.concatenate(segments)


def build_long_silence_test() -> np.ndarray:
    """
    Phase 23/36 scenario 14: Long silence between speakers.
    Tests speaker cache continuity across silence gaps.
    """
    return np.concatenate([
        sine_tone(220, 2.0),    # Doctor speaks
        silence(4.0),           # 4s silence
        sine_tone(330, 2.0),    # Patient speaks
        silence(8.0),           # 8s silence
        sine_tone(220, 1.5),    # Doctor speaks again — must stay Doctor (not swap)
        silence(0.5),
    ])


def build_medical_terms_test() -> np.ndarray:
    """
    Phase 31/36 scenario 11-13: Medical terminology, medication, numbers.
    ~12 seconds of alternating doctor/patient tones.
    """
    return np.concatenate([
        sine_tone(220, 2.5),  # Doctor: Your HbA1c is 7.2 percent.
        silence(0.3),
        sine_tone(330, 2.0),  # Patient: What does that mean?
        silence(0.3),
        sine_tone(220, 3.0),  # Doctor: Your metformin dose is 500 milligrams.
        silence(0.3),
        sine_tone(330, 1.5),  # Patient: Twice daily?
        silence(0.3),
        sine_tone(220, 2.0),  # Doctor: Yes, with meals.
    ])


def build_quiet_patient_test() -> np.ndarray:
    """
    Phase 36 scenario 2: Quiet patient (low amplitude).
    Tests sensitivity.
    """
    return np.concatenate([
        sine_tone(220, 2.0, amplitude=0.4),   # Doctor (normal)
        silence(0.4),
        sine_tone(330, 2.5, amplitude=0.08),  # Patient (very quiet)
        silence(0.4),
        sine_tone(220, 1.5, amplitude=0.4),   # Doctor
        silence(0.4),
        sine_tone(330, 2.0, amplitude=0.08),  # Patient (quiet again)
    ])


def build_rapid_switch_test() -> np.ndarray:
    """
    Phase 36 scenario 15: Rapid turn switching.
    """
    # Rapid back-and-forth
    chunks = []
    for _ in range(8):
        chunks.append(sine_tone(220, 0.6))  # Doctor
        chunks.append(silence(0.15))
        chunks.append(sine_tone(330, 0.5))  # Patient
        chunks.append(silence(0.15))
    return np.concatenate(chunks)


def build_filler_words_test() -> np.ndarray:
    """
    Phase 29/36 scenario 6: Filler words, pause mid-sentence.
    Single long patient utterance with hesitations.
    """
    return np.concatenate([
        sine_tone(220, 2.0),   # Doctor: Tell me what happened.
        silence(0.5),
        sine_tone(330, 1.5),   # Patient: Actually...
        silence(0.8),          # Long pause (filler, "um")
        sine_tone(330, 1.2),   # Patient: I've been having pain...
        silence(0.5),          # Another pause
        sine_tone(330, 2.0),   # Patient: mostly at night.
        silence(0.4),
    ])


if __name__ == "__main__":
    print(f"Creating test recordings in: {OUTPUT_DIR}")
    print()

    save_wav(build_clinical_dialogue(),   "clinical_test_dialogue.wav")
    save_wav(build_interruption_test(),   "test_interruption.wav")
    save_wav(build_long_silence_test(),   "test_long_silence.wav")
    save_wav(build_medical_terms_test(),  "test_medical_terms.wav")
    save_wav(build_quiet_patient_test(),  "test_quiet_patient.wav")
    save_wav(build_rapid_switch_test(),   "test_rapid_switching.wav")
    save_wav(build_filler_words_test(),   "test_filler_pause.wav")

    print()
    print("All test recordings created.")
    print("NOTE: These are synthetic tone files — not real speech.")
    print("      Use real microphone recordings for meaningful ASR accuracy testing.")
    print("      The NeMo ASR model may produce empty transcripts for pure tones.")
    print("      These files are for pipeline/latency/state-machine validation only.")
