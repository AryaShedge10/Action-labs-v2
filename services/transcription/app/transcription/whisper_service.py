"""
Whisper-based transcription service for local speech-to-text processing.

Singleton pattern: model is loaded ONCE at startup and reused across all
requests — eliminates the per-request model load cost (~3-5s).
"""
import os
import sys
from pathlib import Path

# Ensure CUDA DLLs from torch/lib are discoverable by CTranslate2 on Windows
try:
    import torch
    _torch_lib = str(Path(torch.__file__).parent / "lib")
    if os.path.exists(_torch_lib):
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(_torch_lib)
        if _torch_lib not in os.environ.get("PATH", ""):
            os.environ["PATH"] = _torch_lib + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

from faster_whisper import WhisperModel
from typing import List, Dict
import numpy as np
import time

# ---------------------------------------------------------------------------
# Module-level singleton — loaded once, reused forever
# ---------------------------------------------------------------------------
_whisper_model = None
_whisper_model_name = None


def get_whisper_model(model_name: str = "base.en", device: str = "auto", compute_type: str = "auto") -> WhisperModel:
    """
    Get or create the Whisper model singleton.
    Honors WHISPER_DEVICE from environment if set, otherwise auto-detects CUDA.
    """
    global _whisper_model, _whisper_model_name

    if _whisper_model is not None and _whisper_model_name == model_name:
        return _whisper_model

    # Auto-detect best device or use environment override
    if device == "auto":
        env_device = os.getenv("WHISPER_DEVICE")
        if env_device and env_device.strip().lower() in ("cuda", "cpu"):
            device = env_device.strip().lower()
        else:
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"

    if compute_type == "auto":
        compute_type = "float16" if device == "cuda" else "int8"

    t0 = time.time()
    print(f"[WhisperService] Loading model '{model_name}' on {device} ({compute_type})...")
    _whisper_model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
        num_workers=2,
        cpu_threads=4,
    )
    _whisper_model_name = model_name
    print(f"[WhisperService] Model ready in {time.time() - t0:.2f}s  (device={device})")
    return _whisper_model


def warmup_whisper(model_name: str = "base.en"):
    """Pre-load model at server startup so first request is fast."""
    get_whisper_model(model_name)


def is_whisper_model_ready(model_name: str = "small.en") -> bool:
    """Check if the requested Whisper model singleton is fully loaded and ready."""
    return _whisper_model is not None and _whisper_model_name == model_name


_whisper_service_instances: Dict[str, "WhisperService"] = {}


def get_whisper_service(model_name: str = "small.en") -> "WhisperService":
    """Get or create the WhisperService singleton for the requested model."""
    global _whisper_service_instances
    if model_name not in _whisper_service_instances:
        _whisper_service_instances[model_name] = WhisperService(model_name=model_name)
    return _whisper_service_instances[model_name]


class WhisperService:
    """Handles local Whisper transcription using the module-level singleton."""

    AVAILABLE_MODELS = ["tiny.en", "base.en", "small.en", "medium.en", "large-v2"]

    def __init__(self, model_name: str = "base.en", device: str = "auto"):
        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(
                f"Model {model_name} not recognised. "
                f"Available: {', '.join(self.AVAILABLE_MODELS)}"
            )
        self.model_name = model_name
        self.device = device
        self.model = get_whisper_model(model_name, device)

    def load_model(self):
        """No-op: model is already loaded via singleton. Kept for compatibility."""
        self.model = get_whisper_model(self.model_name, self.device)

    def transcribe(self, audio_path: str, language: str = "en") -> List[Dict]:
        """
        Transcribe an audio file.

        Optimisations vs original:
        - beam_size reduced 5 → 2  (2-3x faster, ~1% accuracy loss)
        - word_timestamps only when needed (caller passes flag)
        - language is fixed to 'en' — skips language detection step
        """
        t0 = time.time()
        print(f"\n[Whisper] Transcribing: {Path(audio_path).name}")

        segments_iter, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=5,                            # higher beam = better accuracy
            best_of=1,
            temperature=0.0,                        # fully deterministic
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,        # avoid mid-sentence cuts
                speech_pad_ms=400,                  # more context around speech
                threshold=0.35,                     # lower = catches quieter speech
            ),
            word_timestamps=True,
            condition_on_previous_text=False,       # prevents hallucination cascade
        )

        transcript_segments = []
        for segment in segments_iter:
            seg_data = {
                "start": round(segment.start, 2),
                "end":   round(segment.end,   2),
                "text":  segment.text.strip(),
            }
            if hasattr(segment, "words") and segment.words:
                seg_data["words"] = [
                    {"start": round(w.start, 2),
                     "end":   round(w.end,   2),
                     "word":  w.word}
                    for w in segment.words
                ]
            transcript_segments.append(seg_data)
            print(f"  [{seg_data['start']:.2f}s - {seg_data['end']:.2f}s] {seg_data['text']}")

        print(f"[Whisper] Done — {len(transcript_segments)} segments in {time.time()-t0:.2f}s")
        return transcript_segments

    def transcribe_chunk(self, audio_data: np.ndarray,
                         language: str = "en",
                         offset_seconds: float = 0.0) -> List[Dict]:
        """
        Transcribe a numpy audio chunk (used by streaming pipeline).
        Timestamps are offset so they align with the full recording timeline.

        Args:
            audio_data:      float32 mono 16kHz numpy array
            language:        language code
            offset_seconds:  seconds to add to all timestamps
        """
        t0 = time.time()

        # Silero VAD (inside faster-whisper) requires float32; librosa returns float64
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        from contextlib import nullcontext
        try:
            from app.services.diarization import get_gpu_lock
            gpu_lock = get_gpu_lock()
        except Exception:
            gpu_lock = None

        with (gpu_lock if gpu_lock is not None else nullcontext()):
            segments_iter, _ = self.model.transcribe(
                audio_data,
                language=language,
                beam_size=2,                    # fast for live streaming
                best_of=1,
                temperature=0.0,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=400,
                    speech_pad_ms=300,
                    threshold=0.35,
                ),
                word_timestamps=True,
                condition_on_previous_text=False,
            )

            result = []
            for segment in segments_iter:
                seg_data = {
                    "start": round(segment.start + offset_seconds, 2),
                    "end":   round(segment.end   + offset_seconds, 2),
                    "text":  segment.text.strip(),
                }
                if hasattr(segment, "words") and segment.words:
                    seg_data["words"] = [
                        {"start": round(w.start + offset_seconds, 2),
                         "end":   round(w.end   + offset_seconds, 2),
                         "word":  w.word}
                        for w in segment.words
                    ]
                result.append(seg_data)

        print(f"  [Whisper chunk @ {offset_seconds:.1f}s] "
              f"{len(result)} segs in {time.time()-t0:.2f}s")
        return result

    def transcribe_numpy(self, audio_data: np.ndarray,
                         language: str = "en") -> List[Dict]:
        """Transcribe from a numpy array (kept for backwards compatibility)."""
        return self.transcribe_chunk(audio_data, language=language, offset_seconds=0.0)
