"""Decide whether one microphone frame is voiced speech.

Loudness is only a floor. A clap, a scratch, and a noise burst are loud
without a speech pitch. A beep is a single tone. Speech in this band has a
pitch and a stack of overtones, and it has to hold across several frames
before the listener accepts it.
"""

import numpy as np

from .settings import Settings


def frame_rms(frame: np.ndarray) -> float:
    audio = np.asarray(frame, dtype=np.float32).reshape(-1)
    return float(np.sqrt(np.mean(np.square(audio))))


def is_voiced(frame: np.ndarray, sample_rate: int, level_floor: float, settings: Settings) -> bool:
    """Return True when this frame looks like voiced speech."""
    audio = np.asarray(frame, dtype=np.float64).reshape(-1)
    audio = audio - float(np.mean(audio))
    level = float(np.sqrt(np.mean(np.square(audio))))
    if level < level_floor:
        return False

    harmonicity, f0 = _pitch(audio, sample_rate, settings.pitch_low_hz, settings.pitch_high_hz)
    if harmonicity < settings.min_harmonicity or not settings.min_f0_hz <= f0 <= settings.max_f0_hz:
        return False

    window = np.hanning(audio.size)
    power = np.square(np.abs(np.fft.rfft(audio * window)))
    if float(np.max(power) / np.sum(power)) > settings.max_peak_ratio:
        return False

    fund_share = _fund_share(power, audio.size, sample_rate, f0, settings.harmonic_band_hz)
    return settings.min_fund_share <= fund_share <= settings.max_fund_share


def _pitch(audio: np.ndarray, sample_rate: int, low_hz: float, high_hz: float) -> tuple[float, float]:
    """Autocorrelation peak inside the speech pitch range."""
    size = audio.size
    spectrum = np.fft.rfft(audio, n=size * 2)
    corr = np.fft.irfft(spectrum * np.conj(spectrum))[:size]
    corr = corr / (corr[0] + 1e-12)
    min_lag = int(sample_rate / high_hz)
    max_lag = int(sample_rate / low_hz)
    region = corr[min_lag:max_lag]
    offset = int(np.argmax(region))
    lag = offset + min_lag
    return float(region[offset]), float(sample_rate) / float(lag)


def _fund_share(power: np.ndarray, size: int, sample_rate: int, f0: float, band_hz: float) -> float:
    """Share of the first three partials that sits on the fundamental.

    A vowel keeps energy on the fundamental and on the overtones. A pure beep
    is only one of those.
    """
    freqs = np.fft.rfftfreq(size, 1.0 / sample_rate)
    total = 0.0
    fundamental = 0.0
    for partial in (1, 2, 3):
        center = f0 * partial
        band = power[(freqs >= center - band_hz) & (freqs <= center + band_hz)]
        energy = float(np.sum(band))
        total += energy
        if partial == 1:
            fundamental = energy
    if total <= 0.0:
        return 0.0
    return fundamental / total
