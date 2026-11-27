"""Send one utterance to OpenAI and return the transcript."""

import wave
from io import BytesIO
from pathlib import Path

import numpy as np
from openai import OpenAI

MODEL = "gpt-transcribe"
ENV_FILE = Path(__file__).with_name(".env")


def transcribe(audio: np.ndarray, sample_rate: int, language: str | None = None) -> str:
    """Transcribe mono float audio. An empty language lets the model detect it."""
    env = _load_env(ENV_FILE)
    api_key = env.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in src/transcribe/.env")
    chosen = _language(language, env)
    wav = _wav_bytes(audio, sample_rate)
    kwargs: dict = {"model": MODEL, "file": wav}
    if chosen:
        kwargs["languages"] = [chosen]
    result = OpenAI(api_key=api_key).audio.transcriptions.create(**kwargs)
    return result.text


def _language(language: str | None, env: dict[str, str]) -> str:
    if language is None:
        return env.get("OPENAI_TRANSCRIBE_LANGUAGE", "").strip()
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
