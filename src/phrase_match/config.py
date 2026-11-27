"""Toggle and phrase list for matching phrases in a transcript."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Whether to look for phrases in a transcript, and which phrases count.

    Add phrases in the tuple. A single phrase still needs a comma:
    ("okay go",). "turn on" matches "Turn   on!" and not "turnover".
    """

    enabled: bool = True
    phrases: tuple[str, ...] = ("okay go", "Pamela off,", "OK Go,", "OK Vai", "okay vai",)
