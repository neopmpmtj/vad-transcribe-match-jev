"""Level of a captured utterance."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """How loud the captured audio is before it is sent on.

    preroll_s is how much audio from before speech was detected is kept.
    gain multiplies every sample. target_peak, when above zero, then
    scales that result so the loudest sample equals target_peak.
    """

    preroll_s: float = 1.5
    gain: float = 1.0
    target_peak: float = 0.45
