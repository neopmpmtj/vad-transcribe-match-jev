"""Switches for the short-clip gate and its optional log."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Gate cutoff and the separate log switch.

    gate_enabled runs the length check and the empty-transcript line.
    log_enabled writes SQLite rows. Turning the log off leaves the gate running.
    min_content_s is the sound-after-trigger length under which a clip is dropped.
    A clip of exactly this length is still sent.
    """

    gate_enabled: bool = True
    log_enabled: bool = True
    min_content_s: float = 1.0
