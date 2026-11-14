"""
Audio preprocessing module for normalizing and preparing audio for transcription.
Includes noise reduction via spectral subtraction and high-pass filtering.
"""
import numpy as np
try:
    import librosa
except ImportError:
    librosa = None
from typing import Optional


class AudioPreprocessor:
    """Preprocesses audio files for optimal Whisper transcription."""
    
    def __init__(self, target_sample_rate: int = 16000):
        """
        Initialize preprocessor.
        
        Args:
            target_sample_rate: Target sample rate (Whisper uses 16kHz)
        """
        self.target_sample_rate = target_sample_rate
    
    def preprocess(
        self,
        audio_data: np.ndarray,
        original_sample_rate: int,
        fast_mode: bool = False,
    ) -> np.ndarray:
        """
        Complete preprocessing pipeline.

        Steps (always):
          1. Convert to mono
          2. Resample to 16kHz
          3. High-pass filter  (removes AC hum / rumble < 80 Hz)
          4. Normalize volume  (RMS-based)

        Step 5 (full mode only — for final audio, NOT live chunks):
          5. Spectral noise reduction  (STFT-based, ~1s overhead)

        Args:
            audio_data:           Input audio data (any dtype, any channels)
            original_sample_rate: Original sample rate
            fast_mode:            True → skip spectral subtraction (use for live 5s chunks)

        Returns:
            Preprocessed float32 audio ready for Whisper
        """
        print("Preprocessing audio...")

        # Step 1: Convert to mono
        audio_mono = self._to_mono(audio_data)
        print("  [OK] Converted to mono")

        # Step 2: Resample to target rate
        if original_sample_rate != self.target_sample_rate:
            audio_resampled = self._resample(
                audio_mono,
                original_sample_rate,
                self.target_sample_rate,
            )
            print(f"  [OK] Resampled to {self.target_sample_rate} Hz")
        else:
            audio_resampled = audio_mono.astype(np.float32)
            print(f"  [OK] Already at {self.target_sample_rate} Hz")

        # Step 3: High-pass filter — always fast (<5 ms)
        audio_filtered = self._high_pass_filter(audio_resampled, cutoff_hz=80)
        print("  [OK] High-pass filter applied (>80 Hz)")

        # Step 4: Spectral noise reduction — only for final audio
        if not fast_mode:
            audio_filtered = self._reduce_noise(audio_filtered)
            print("  [OK] Noise reduction applied")

        # Step 5: Normalize volume
        audio_normalized = self._normalize(audio_filtered)
        print("  [OK] Normalized volume")

        return audio_normalized
    
    def _to_mono(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Convert audio to mono.
        
        Args:
            audio_data: Input audio (can be mono or stereo)
            
        Returns:
            Mono audio data
        """
        if audio_data.ndim == 1:
            # Already mono
            return audio_data
        elif audio_data.ndim == 2:
            # Convert stereo to mono by averaging channels
            return np.mean(audio_data, axis=1)
        else:
            raise ValueError(f"Unsupported audio shape: {audio_data.shape}")
    
    def _resample(
        self, 
        audio_data: np.ndarray, 
        orig_sr: int, 
        target_sr: int
    ) -> np.ndarray:
        """
        Resample audio to target sample rate.
        
        Args:
            audio_data: Input audio
            orig_sr: Original sample rate
            target_sr: Target sample rate
            
        Returns:
            Resampled audio
        """
        if orig_sr == target_sr:
            return audio_data.astype(np.float32)
        if librosa is not None:
            return librosa.resample(
                audio_data, 
                orig_sr=orig_sr, 
                target_sr=target_sr
            )
        try:
            from scipy.signal import resample_poly
            from math import gcd
            g = gcd(orig_sr, target_sr)
            up = target_sr // g
            down = orig_sr // g
            return resample_poly(audio_data, up, down).astype(np.float32)
        except Exception:
            num_samples = int(len(audio_data) * target_sr / orig_sr)
            indices = np.linspace(0, len(audio_data) - 1, num_samples)
            return np.interp(indices, np.arange(len(audio_data)), audio_data).astype(np.float32)
    
    def _normalize(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Normalize audio volume using RMS-based normalization.
        This is more robust than peak normalization for speech.
        
        Args:
            audio_data: Input audio
            
        Returns:
            Normalized audio
        """
        # RMS-based normalization targets -20 dBFS
        rms = np.sqrt(np.mean(audio_data ** 2))
        if rms > 1e-6:
            target_rms = 0.1  # -20 dBFS
            audio_data = audio_data * (target_rms / rms)
        # Clip to prevent any peaks from exceeding ±1
        return np.clip(audio_data, -1.0, 1.0)

    def _high_pass_filter(self, audio_data: np.ndarray, cutoff_hz: float = 80) -> np.ndarray:
        """
        Apply a high-pass filter to remove low-frequency noise.
        Removes: AC hum (50/60 Hz), microphone rumble, wind noise.
        
        Args:
            audio_data: Input audio at target_sample_rate
            cutoff_hz:  Cutoff frequency in Hz (default 80 Hz)
            
        Returns:
            Filtered audio
        """
        try:
            from scipy.signal import butter, filtfilt
            nyq = self.target_sample_rate / 2.0
            normal_cutoff = cutoff_hz / nyq
            normal_cutoff = min(normal_cutoff, 0.99)  # clamp below Nyquist
            b, a = butter(4, normal_cutoff, btype='high', analog=False)
            # Use filtfilt for zero-phase (no time shift in the signal)
            return filtfilt(b, a, audio_data).astype(np.float32)
        except ImportError:
            # scipy not available — skip silently
            return audio_data

    def _reduce_noise(self, audio_data: np.ndarray,
                      noise_sample_duration: float = 0.3,
                      reduction_strength: float = 1.5) -> np.ndarray:
        """
        Spectral subtraction noise reduction.
        Estimates noise from the first `noise_sample_duration` seconds of audio
        (usually silence / room tone) and subtracts it from the whole signal.
        
        Args:
            audio_data:             Input audio (float32, mono, 16kHz)
            noise_sample_duration:  How many seconds at the start to use as noise profile
            reduction_strength:     Multiplier for noise floor suppression (1.0=light, 2.0=aggressive)
            
        Returns:
            Denoised audio (same shape as input)
        """
        n_fft = 512
        hop_length = n_fft // 4

        if librosa is None:
            return audio_data

        audio_data = audio_data.astype(np.float32)

        # Need at least 2× n_fft samples to run STFT meaningfully
        if len(audio_data) < n_fft * 2:
            return audio_data

        # Compute STFT
        stft = librosa.stft(audio_data, n_fft=n_fft, hop_length=hop_length)
        magnitude, phase = np.abs(stft), np.angle(stft)

        # Estimate noise floor from the opening silence
        noise_samples = int(noise_sample_duration * self.target_sample_rate)
        noise_samples = max(n_fft, min(noise_samples, len(audio_data) // 4))
        noise_frames_count = max(1, noise_samples // hop_length)

        # Use first N frames as noise reference
        noise_profile = np.mean(magnitude[:, :noise_frames_count], axis=1, keepdims=True)

        # Spectral subtraction: suppress frequencies that look like noise
        cleaned = magnitude - reduction_strength * noise_profile

        # Wiener-like flooring: never go below 10% of original magnitude
        cleaned = np.maximum(cleaned, 0.1 * magnitude)

        # Reconstruct audio from cleaned magnitude + original phase
        stft_clean = cleaned * np.exp(1j * phase)
        audio_out = librosa.istft(stft_clean, hop_length=hop_length, length=len(audio_data))
        return audio_out.astype(np.float32)
