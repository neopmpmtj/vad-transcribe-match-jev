"""Send one utterance to OpenAI and return the transcript."""

import wave
from io import BytesIO
from pathlib import Path

import numpy as np
from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    AuthenticationError,
    InternalServerError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from .config import Config

MODEL = "gpt-transcribe"
TIMEOUT_S = 60.0
ENV_FILE = Path(__file__).with_name(".env")
_MISSING_KEY = (
    "Missing OpenAI API key. Set OPENAI_API_KEY in src/transcribe/.env. "
    "The next phrase reads that file again."
)
_REJECTED_KEY = (
    "OpenAI rejected the API key. Check OPENAI_API_KEY in src/transcribe/.env. "
    "The next phrase reads that file again."
)
_NO_FUNDS = (
    "OpenAI refused the request because the account has no quota or no funds. "
    "Fix billing, then speak again."
)
_RATE_LIMIT = "OpenAI rate limit reached. Wait a moment, then speak again."
_NETWORK = "Could not reach OpenAI. Check the network, then speak again."
_FORBIDDEN = "This API key is not allowed to call the transcription model."
_NOT_FOUND = (
    "The transcription model was not found. "
    "The model name is gpt-transcribe in src/transcribe/transcribe.py."
)
_SERVER = "OpenAI had a server error. Speak again."
_QUOTA_CODES = frozenset({"insufficient_quota", "billing_hard_limit_reached"})


def transcribe(audio: np.ndarray, sample_rate: int, language: str | None = None) -> str:
    """Transcribe mono float audio. An empty language lets the model detect it."""
    env = _load_env(ENV_FILE)
    api_key = env.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(_MISSING_KEY)
    chosen = _language(language)
    wav = _wav_bytes(audio, sample_rate)
    kwargs: dict = {"model": MODEL, "file": wav}
    if chosen:
        kwargs["languages"] = [chosen]
    client = OpenAI(api_key=api_key, timeout=TIMEOUT_S, max_retries=0)
    try:
        result = client.audio.transcriptions.create(**kwargs)
    except APIError as exc:
        sentence = _guide(exc)
        if sentence is None:
            raise
        raise RuntimeError(sentence) from exc
    return result.text


def _guide(exc: APIError) -> str | None:
    """One instruction for a known API failure. None leaves the error unchanged."""
    if isinstance(exc, APIConnectionError):
        return _NETWORK
    if isinstance(exc, AuthenticationError):
        return _REJECTED_KEY
    if isinstance(exc, PermissionDeniedError):
        return _FORBIDDEN
    if isinstance(exc, NotFoundError):
        return _NOT_FOUND
    if isinstance(exc, RateLimitError):
        return _NO_FUNDS if _no_funds(exc) else _RATE_LIMIT
    if isinstance(exc, InternalServerError):
        return _SERVER
    if isinstance(exc, APIStatusError):
        if _no_funds(exc):
            return _NO_FUNDS
        return f"OpenAI request failed ({exc.status_code})."
    return None


def _no_funds(exc: APIError) -> bool:
    found = {exc.code, exc.type}
    body = exc.body
    if isinstance(body, dict):
        found.add(body.get("code"))
        found.add(body.get("type"))
        nested = body.get("error")
        if isinstance(nested, dict):
            found.add(nested.get("code"))
            found.add(nested.get("type"))
    return any(value in _QUOTA_CODES for value in found)


def _language(language: str | None) -> str:
    if language is None:
        return Config().language.strip()
    return language.strip()


def _load_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _wav_bytes(audio: np.ndarray, sample_rate: int) -> BytesIO:
    pcm = np.clip(np.asarray(audio, dtype=np.float32), -1.0, 1.0)
    pcm = (pcm * 32767.0).astype(np.int16)
    buf = BytesIO()
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())
    buf.seek(0)
    buf.name = "utterance.wav"
    return buf
