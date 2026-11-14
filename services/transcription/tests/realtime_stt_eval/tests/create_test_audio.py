"""
Create Synthetic Clinical Test Audio
tests/realtime_stt_eval/tests/create_test_audio.py

Creates a synthetic doctor/patient dialogue WAV file using Windows TTS.
"""
import sys
import struct
import wave
import math
import random
from pathlib import Path

RECORDINGS_DIR = Path(__file__).resolve().parent.parent / "recordings"
RECORDINGS_DIR.mkdir(exist_ok=True)


def generate_sine_tone(freq_hz: float, duration_s: float, sample_rate: int = 16000, amplitude: float = 0.3) -> bytes:
    n = int(sample_rate * duration_s)
    samples = []
    for i in range(n):
        val = amplitude * math.sin(2 * math.pi * freq_hz * i / sample_rate)
        samples.append(int(val * 32767))
    return struct.pack(f"<{n}h", *samples)


def generate_silence(duration_s: float, sample_rate: int = 16000) -> bytes:
    n = int(sample_rate * duration_s)
    return struct.pack(f"<{n}h", *([0] * n))


def save_wav(filename: str, audio_segments: list, sample_rate: int = 16000):
    output_path = RECORDINGS_DIR / filename
    all_bytes = b"".join(audio_segments)
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(all_bytes)
    print(f"Saved: {output_path} ({len(all_bytes)/2/sample_rate:.2f}s)")
    return output_path


def main():
    """Generates a synthetic clinical dialogue test recording."""
    SR = 16000

    # Turn frequencies (different pitches simulate different speakers)
    DOCTOR_FREQ = 130.0   # Lower pitch for doctor
    PATIENT_FREQ = 220.0  # Higher pitch for patient

    # Script: Clinical consultation dialogue
    # Format: (speaker, duration_s, freq, note)
    dialogue = [
        ("Doctor", 2.0, DOCTOR_FREQ, "Good morning, how are you feeling today?"),
        ("silence", 0.5, 0, "pause between speakers"),
        ("Patient", 2.5, PATIENT_FREQ, "Good morning, Doctor. I've been having some chest pain."),
        ("silence", 0.5, 0, ""),
        ("Doctor", 2.0, DOCTOR_FREQ, "When does the pain usually happen?"),
        ("silence", 0.5, 0, ""),
        ("Patient", 3.0, PATIENT_FREQ, "Mostly when I walk quickly or climb stairs."),
        ("silence", 0.5, 0, ""),
        ("Doctor", 1.5, DOCTOR_FREQ, "Any shortness of breath?"),
        ("silence", 0.3, 0, ""),
        ("Patient", 0.5, PATIENT_FREQ, "Yes."),
        ("silence", 0.3, 0, "quick answer"),
        ("Patient", 1.0, PATIENT_FREQ, "Sometimes."),
        ("silence", 0.5, 0, ""),
        ("Doctor", 2.5, DOCTOR_FREQ, "Are you taking any medications currently?"),
        ("silence", 0.5, 0, ""),
        ("Patient", 4.0, PATIENT_FREQ, "Uh, I take metformin, five hundred milligrams twice a day."),
        ("silence", 0.5, 0, ""),
        ("Doctor", 3.0, DOCTOR_FREQ, "How long have you been experiencing this chest pain?"),
        ("silence", 0.5, 0, ""),
        ("Patient", 4.5, PATIENT_FREQ, "About two weeks. It started after I began my new exercise routine."),
        ("silence", 0.5, 0, ""),
        ("Doctor", 2.5, DOCTOR_FREQ, "Has the pain been getting better or worse?"),
        ("silence", 0.5, 0, ""),
        ("Patient", 2.0, PATIENT_FREQ, "It seems about the same. Maybe slightly better."),
        ("silence", 1.0, 0, "longer pause"),
        ("Patient", 2.0, PATIENT_FREQ, "One more thing. I've been having some dizziness."),
    ]

    print("Creating synthetic clinical test audio...")
    print("=" * 60)
    print("TEST SCRIPT:")
    for turn, _, _, text in dialogue:
        if turn != "silence" and text:
            print(f"  [{turn}]: {text}")
    print("=" * 60)

    segments = []
    for speaker, dur, freq, text in dialogue:
        if speaker == "silence":
            segments.append(generate_silence(dur, SR))
        else:
            # Add slight variation
            varied_dur = dur + random.uniform(-0.1, 0.1)
            segments.append(generate_sine_tone(freq, max(0.3, varied_dur), SR, amplitude=0.25))

    save_wav("clinical_test_dialogue.wav", segments, SR)
    print("\nTest recordings created successfully!")
    print(f"Location: {RECORDINGS_DIR}")
    print("\nNote: This is a pure tone audio for testing the pipeline.")
    print("For realistic testing, record actual doctor/patient dialogue.")


if __name__ == "__main__":
    main()
