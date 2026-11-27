"""Keep microphone audio from just before speech is detected until silence."""

from collections import deque

import numpy as np

from .config import Config


class Recorder:
    """Collect microphone hops and return one utterance.

    Before start(), hops are kept in a short lead-in. start() makes that
    lead-in the beginning of the utterance.
    """

    def __init__(self, sample_rate: int, config: Config | None = None) -> None:
        self.sample_rate = sample_rate
        self.config = Config() if config is None else config
        self._chunks: list[np.ndarray] = []
        self._preroll: deque[np.ndarray] = deque()
        self._preroll_n = 0
        self._recording = False

    @property
    def recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        self._chunks = list(self._preroll)
        self._preroll.clear()
        self._preroll_n = 0
        self._recording = True

    def write(self, samples: np.ndarray) -> None:
        audio = np.asarray(samples, dtype=np.float32).reshape(-1).copy()
        if self._recording:
            self._chunks.append(audio)
            return
        self._preroll.append(audio)
        self._preroll_n += int(audio.size)
        self._trim_preroll()

    def _trim_preroll(self) -> None:
        limit = int(round(self.sample_rate * self.config.preroll_s))
        if limit <= 0:
            self._preroll.clear()
            self._preroll_n = 0
            return
        while self._preroll_n > limit and self._preroll:
            extra = self._preroll_n - limit
            head = self._preroll[0]
            if head.size <= extra:
                self._preroll.popleft()
                self._preroll_n -= int(head.size)
                continue
            self._preroll[0] = head[extra:]
            self._preroll_n -= extra
            break

    def finish(self) -> np.ndarray | None:
        """Stop and return the utterance, or None when nothing was captured."""
        self._recording = False
        self._preroll.clear()
        self._preroll_n = 0
        if not self._chunks:
            return None
        audio = np.concatenate(self._chunks)
        self._chunks = []
        return _scale(audio, self.config)


def _scale(audio: np.ndarray, config: Config) -> np.ndarray:
    scaled = np.asarray(audio, dtype=np.float32) * np.float32(config.gain)
    if config.target_peak > 0.0:
        peak = float(np.max(np.abs(scaled)))
        if peak > 0.0:
            scaled = scaled * (np.float32(config.target_peak) / np.float32(peak))
    return scaled
