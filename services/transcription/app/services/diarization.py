"""
Real speaker diarization using pyannote.audio.

Singleton pattern: pipeline is loaded ONCE at startup and reused —
eliminates the per-request 5-10s model load cost.
"""
import os
import time
import warnings
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
import torch

# Suppress harmless torchcodec and pyannote warnings on Windows
warnings.filterwarnings("ignore", category=UserWarning, module="pyannote")
warnings.filterwarnings("ignore", message=".*torchcodec.*")

# Load environment variables
load_dotenv()

# Global pipeline cache
_pipeline = None
_pipeline_load_time = None


def warmup_diarization():
    """Pre-load the diarization pipeline at server startup."""
    get_diarization_pipeline()


def get_diarization_pipeline():
    """
    Get or create the diarization pipeline (singleton pattern).
    
    Returns:
        Diarization pipeline or None if loading fails
    """
    global _pipeline, _pipeline_load_time
    
    if _pipeline is not None:
        return _pipeline
    
    try:
        from pyannote.audio import Pipeline
        
        # Get HuggingFace token from environment
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token or hf_token == "your_huggingface_token_here":
            print("[WARN] HF_TOKEN not set or is placeholder value")
            print("   Diarization will fall back to UNKNOWN speaker labels")
            print("   To enable diarization:")
            print("   1. Get token from https://huggingface.co/settings/tokens")
            print("   2. Accept terms at https://huggingface.co/pyannote/speaker-diarization-3.1")
            print("   3. Set HF_TOKEN in .env file")
            return None
        
        # Detect device
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        print(f"Loading speaker diarization pipeline...")
        print(f"  Device: {device}")
        
        start_time = time.time()
        
        # Load pre-trained pipeline
        _pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=hf_token
        )
        
        # Move to appropriate device
        _pipeline.to(device)
        
        _pipeline_load_time = time.time() - start_time
        
        print(f"[OK] Diarization pipeline loaded in {_pipeline_load_time:.2f}s")
        
        return _pipeline
        
    except Exception as e:
        print(f"[ERROR] loading diarization pipeline: {e}")
        print("   Falling back to UNKNOWN speaker labels")
        return None


import threading
import numpy as np

# Global GPU lock to prevent concurrent heavy Pyannote & Whisper CUDA execution on 4GB VRAM
_gpu_lock = threading.Lock()


def get_gpu_lock() -> threading.Lock:
    """Return the global GPU lock to coordinate CUDA inference across models."""
    return _gpu_lock


def diarize_chunk(
    audio_data: np.ndarray,
    sample_rate: int = 16000,
    offset_seconds: float = 0.0,
    min_speakers: Optional[int] = 1,
    max_speakers: Optional[int] = 2
) -> List[Dict]:
    """
    Perform speaker diarization directly on an in-memory numpy array (16kHz mono).
    Timestamps are adjusted by offset_seconds to align with the global conversation timeline.

    Args:
        audio_data: Float32 mono 16kHz numpy array
        sample_rate: Sampling rate (default 16000)
        offset_seconds: Global start offset in seconds
        min_speakers: Minimum number of speakers (default 1)
        max_speakers: Maximum number of speakers (default 2)

    Returns:
        List of diarization turns: [{"start": float, "end": float, "speaker": str}, ...]
    """
    pipeline = get_diarization_pipeline()
    if pipeline is None:
        return []

    if audio_data is None or len(audio_data) < sample_rate * 0.5:
        # Less than 0.5s audio — skip
        return []

    try:
        t0 = time.time()
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # Convert to 2D torch tensor (channels, samples)
        tensor = torch.from_numpy(audio_data)
        if tensor.dim() == 1:
            tensor = tensor.unsqueeze(0)

        audio_input = {"waveform": tensor, "sample_rate": sample_rate}

        kwargs = {}
        if min_speakers is not None:
            kwargs["min_speakers"] = min_speakers
        if max_speakers is not None:
            kwargs["max_speakers"] = max_speakers

        with _gpu_lock:
            with torch.inference_mode():
                output = pipeline(audio_input, **kwargs)

        turns = []
        if hasattr(output, "speaker_diarization"):
            for turn, speaker in output.speaker_diarization:
                turns.append({
                    "start": round(float(turn.start) + offset_seconds, 2),
                    "end": round(float(turn.end) + offset_seconds, 2),
                    "speaker": speaker
                })
        else:
            for turn, _, speaker in output.itertracks(yield_label=True):
                turns.append({
                    "start": round(float(turn.start) + offset_seconds, 2),
                    "end": round(float(turn.end) + offset_seconds, 2),
                    "speaker": speaker
                })

        turns.sort(key=lambda x: x["start"])
        elapsed = time.time() - t0
        print(f"  [Pyannote chunk @ {offset_seconds:.1f}s] {len(turns)} turns in {elapsed:.2f}s")
        return turns

    except Exception as e:
        print(f"[ERROR] diarize_chunk failed: {e}")
        return []


def diarize(audio_path: str, min_speakers: int = None, max_speakers: int = None) -> List[Dict]:
    """
    Perform speaker diarization on audio file.
    
    Args:
        audio_path: Path to audio file (WAV format preferred)
        min_speakers: Minimum number of speakers (optional, improves accuracy)
        max_speakers: Maximum number of speakers (optional, improves accuracy)
        
    Returns:
        List of diarization turns: [{"start": float, "end": float, "speaker": str}, ...]
        Sorted by start time. Returns empty list if diarization fails.
    """
    pipeline = get_diarization_pipeline()
    
    if pipeline is None:
        print("Diarization pipeline not available, returning empty result")
        return []
    
    try:
        print(f"Running speaker diarization on: {Path(audio_path).name}")
        if min_speakers is not None and max_speakers is not None:
            print(f"  Constraining to {min_speakers}-{max_speakers} speakers")
        start_time = time.time()
        
        # Run diarization with optional speaker constraints
        kwargs = {}
        if min_speakers is not None:
            kwargs['min_speakers'] = min_speakers
        if max_speakers is not None:
            kwargs['max_speakers'] = max_speakers
        
        # Preload audio into memory tensor to avoid torchcodec dependency
        import torchaudio
        waveform, sample_rate = torchaudio.load(audio_path)
        audio_input = {"waveform": waveform, "sample_rate": sample_rate}
        
        # Run diarization in inference mode for maximum speed & lower memory
        with _gpu_lock:
            with torch.inference_mode():
                output = pipeline(audio_input, **kwargs)
        
        # Extract speaker turns - support both old and new pyannote.audio API
        turns = []
        
        # NEW API (pyannote.audio >= 3.0): output has .speaker_diarization attribute
        if hasattr(output, 'speaker_diarization'):
            for turn, speaker in output.speaker_diarization:
                turns.append({
                    "start": float(turn.start),
                    "end": float(turn.end),
                    "speaker": speaker
                })
        # OLD API (pyannote.audio < 3.0): output has .itertracks() method
        else:
            for turn, _, speaker in output.itertracks(yield_label=True):
                turns.append({
                    "start": float(turn.start),
                    "end": float(turn.end),
                    "speaker": speaker
                })
        
        # Sort by start time
        turns.sort(key=lambda x: x["start"])
        
        # Count unique speakers
        unique_speakers = set(turn["speaker"] for turn in turns)
        
        elapsed = time.time() - start_time
        print(f"[OK] Diarization complete in {elapsed:.2f}s")
        print(f"  Detected {len(unique_speakers)} speaker(s): {', '.join(sorted(unique_speakers))}")
        print(f"  Generated {len(turns)} speaker turn(s)")
        
        if len(unique_speakers) > 2:
            print(f"  [WARN] Note: {len(unique_speakers)} speakers detected (more than 2)")
        
        return turns
        
    except Exception as e:
        print(f"[ERROR] during diarization: {e}")
        print("   Returning empty result (will fall back to UNKNOWN)")
        return []

