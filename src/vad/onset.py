"""Activation gate for voiced frames.

Voiced frames have to hold for a short run before this counts as speech
starting. The gate then stays shut until the voice is gone.
"""


class OnsetDetector:
    def __init__(self, consecutive: int = 5, release_consecutive: int = 6, gap_frames: int = 1):
        self.consecutive = consecutive
        self.release_consecutive = release_consecutive
        self.gap_frames = gap_frames
        self._hits = 0
        self._quiet = 0
        self._gap = 0
        self._active = False

    def reset(self) -> None:
        self._hits = 0
        self._quiet = 0
        self._gap = 0
        self._active = False

    def update(self, voiced: bool) -> bool:
        """Consume one frame. Return True on the frame voice starts."""
        if self._active:
            if not voiced:
                self._quiet += 1
                if self._quiet >= self.release_consecutive:
                    self._active = False
                    self._hits = 0
                    self._quiet = 0
                    self._gap = 0
            else:
                self._quiet = 0
            return False
        if voiced:
            self._hits += 1
            self._gap = 0
        else:
            self._gap += 1
            if self._hits > 0 and self._gap <= self.gap_frames:
                return False
            self._hits = 0
            self._gap = 0
            return False
        if self._hits < self.consecutive:
            return False
        self._active = True
        self._hits = 0
        self._quiet = 0
        self._gap = 0
        return True
