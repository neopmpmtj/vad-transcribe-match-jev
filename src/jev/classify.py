"""Ask Jev whether an entry is exactly one request."""

from dataclasses import dataclass
from pathlib import Path

from typesafe_sdk import (
    Noul,
    NoulCriteria,
    RetryPolicy,
    TypeSafeAPIConnectionError,
    TypeSafeAPIError,
    TypeSafeAPIResponseValidationError,
    TypeSafeAuthenticationError,
    TypeSafeBadRequestError,
    TypeSafeClient,
    TypeSafeError,
    TypeSafeInternalServerError,
    TypeSafeNotFoundError,
    TypeSafePermissionDeniedError,
    TypeSafeRateLimitError,
    TypeSafeUnprocessableEntityError,
)

from .config import Config

TIMEOUT_S = 60.0
ENV_FILE = Path(__file__).with_name(".env")
_QUESTION = "single_request"
_MISSING_KEY = "Missing TypeSafe API key. Set TYPESAFE_API_KEY in src/jev/.env."
_REJECTED_KEY = "TypeSafe rejected the API key. Check TYPESAFE_API_KEY in src/jev/.env."
_EMPTY = "Enter the text to classify."
_NETWORK = "Could not reach TypeSafe. Check the network, then run the command again."
_RATE_LIMIT = "TypeSafe rate limit reached. Wait a moment, then run the command again."
_FORBIDDEN = "This API key is not allowed to call the model."
_SERVER = "TypeSafe had a server error. Run the command again."
_REJECTED_REQUEST = "TypeSafe rejected the request. Check the question in src/jev/config.py."
_UNREADABLE = "TypeSafe returned an answer that could not be read. Run the command again."


@dataclass(frozen=True)
class Decision:
    """The yes or no answer, the probability of yes, and the confidence score."""

    answer: str
    noul: float
    confidence: float


def classify(entry: str, config: Config | None = None) -> Decision:
    """Return yes or no for one entry. A failed call raises."""
    text = str(entry).strip()
    if not text:
        raise RuntimeError(_EMPTY)
    settings = Config() if config is None else config
    api_key = _load_env(ENV_FILE).get("TYPESAFE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(_MISSING_KEY)
    try:
        with TypeSafeClient(
            api_key=api_key,
            model=settings.model,
            retry=RetryPolicy(max_retries=0),
            timeout=TIMEOUT_S,
        ) as client:
            response = client.system_one(
                state=text,
                questions={
                    _QUESTION: Noul(
                        instructions=settings.instructions,
                        criteria=NoulCriteria(
                            true=settings.true_case,
                            false=settings.false_case,
                        ),
                    ),
                },
            )
    except TypeSafeError as exc:
        raise RuntimeError(_guide(exc, settings.model)) from exc
    return _decision(float(response.nouls[_QUESTION].noul), settings.yes_at)


def _decision(noul: float, yes_at: float) -> Decision:
    answer = "yes" if noul >= yes_at else "no"
    confidence = abs((2.0 * noul) - 1.0)
    return Decision(answer=answer, noul=noul, confidence=confidence)


def _guide(exc: TypeSafeError, model: str) -> str:
    """One instruction for a known API failure."""
    if isinstance(exc, TypeSafeAPIConnectionError):
        return _NETWORK
    if isinstance(exc, TypeSafeAuthenticationError):
        return _REJECTED_KEY
    if isinstance(exc, TypeSafePermissionDeniedError):
        return _FORBIDDEN
    if isinstance(exc, TypeSafeNotFoundError):
        return (
            "The model was not found. "
            f"The model name is {model} in src/jev/config.py."
        )
    if isinstance(exc, TypeSafeRateLimitError):
        return _RATE_LIMIT
    if isinstance(exc, TypeSafeInternalServerError):
        return _SERVER
    if isinstance(exc, (TypeSafeBadRequestError, TypeSafeUnprocessableEntityError)):
        return _REJECTED_REQUEST
    if isinstance(exc, TypeSafeAPIResponseValidationError):
        return _UNREADABLE
    if isinstance(exc, TypeSafeAPIError):
        return f"TypeSafe request failed ({exc.status})."
    return _REJECTED_KEY


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
