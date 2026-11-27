"""Find a listed phrase in a transcript. No model is used."""

import re
import unicodedata

from .config import Config

_WORD = re.compile(r"[^\W_]+", flags=re.UNICODE)


def found(text: str, config: Config | None = None) -> list[str]:
    """Return each configured phrase that appears as whole words, in list order."""
    settings = Config() if config is None else config
    if not settings.enabled or not settings.phrases:
        return []
    words = _words(text)
    return [phrase for phrase in settings.phrases if _hit(words, _words(phrase))]


def _words(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFD", text.casefold())
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return _WORD.findall(stripped)


def _hit(words: list[str], phrase: list[str]) -> bool:
    if not phrase or len(phrase) > len(words):
        return False
    span = len(phrase)
    return any(words[i : i + span] == phrase for i in range(len(words) - span + 1))
