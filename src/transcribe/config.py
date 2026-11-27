"""Language hint sent with each transcription."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Language code for the transcription request.

    Leave language empty to let the model choose. A set code is sent as the hint.
    en english, pt portuguese, es spanish, fr french, nl dutch, de german,
    no norwegian, it italian.
    """

    language: str = "en"
