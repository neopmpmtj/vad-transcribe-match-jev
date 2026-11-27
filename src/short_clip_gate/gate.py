"""Decide whether a finished clip is too short to send, and record it when logging is on."""

import sys
from collections.abc import Sized
from pathlib import Path

from .config import Config


def is_short(content_s: float | None, min_content_s: float) -> bool:
    """True when the measured sound is a real non-negative number under the cutoff.

    None, a value that is not a number, and a negative length fail open: the clip is sent.
    """
    if isinstance(content_s, bool) or content_s is None:
        return False
    try:
        value = float(content_s)
    except (TypeError, ValueError):
        return False
    if value != value or value < 0.0:
        return False
    return value < min_content_s


def _finite(value: float | None) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


class Gate:
    """Length check, with a log that stays closed unless both switches are on."""

    def __init__(self, config: Config | None = None, log_path: Path | None = None) -> None:
        self.config = Config() if config is None else config
        self.active = self.config.gate_enabled
        self._store = None
        self._insert_warned = False
        if not self.active or not self.config.log_enabled:
            return
        try:
            from .store import db_path, open_store

            path = db_path() if log_path is None else log_path
            self._store = open_store(path)
        except Exception as exc:
            print(f"WARNING: short-clip gate log unavailable ({exc})", file=sys.stderr)

    def rejects(self, content_s: float | None) -> bool:
        """True when this clip should be dropped before the API call."""
        if not self.active:
            return False
        return is_short(content_s, self.config.min_content_s)

    def note(
        self,
        reason: str,
        utterance_n: int,
        content_s: float | None,
        audio: Sized,
        sample_rate: int,
    ) -> None:
        """Write one row when the log is open. A write failure leaves the decision as it is."""
        if self._store is None:
            return
        try:
            captured_s = None
            if sample_rate:
                captured_s = float(len(audio)) / float(sample_rate)
            self._store.add(
                utterance_n=utterance_n,
                content_s=_finite(content_s),
                captured_s=_finite(captured_s),
                cutoff_s=float(self.config.min_content_s),
                reason=reason,
            )
        except Exception as exc:
            if not self._insert_warned:
                print(f"WARNING: short-clip gate log write failed ({exc})", file=sys.stderr)
                self._insert_warned = True


def load_gate() -> Gate:
    """Open the gate from the package config."""
    return Gate()
