"""Listener settings."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Values used by `python -m vad`."""

    sample_rate: int = 16000
    frame_s: float = 0.04
    hop_s: float = 0.02
    calibration_s: float = 0.5
    consecutive: int = 5
    release_consecutive: int = 6
    gap_frames: int = 1
    silence_s: float = 2.0
    noise_multiplier: float = 3.0
    min_level: float = 0.0001
    min_harmonicity: float = 0.35
    pitch_low_hz: float = 70.0
    pitch_high_hz: float = 400.0
    min_f0_hz: float = 75.0
    max_f0_hz: float = 360.0
    min_fund_share: float = 0.12
    max_fund_share: float = 0.95
    max_peak_ratio: float = 0.5
    harmonic_band_hz: float = 45.0
