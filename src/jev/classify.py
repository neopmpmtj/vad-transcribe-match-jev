"""Ask Jev whether an entry is exactly one request."""

from dataclasses import dataclass
from pathlib import Path

from typesafe_sdk import (
    Noul,
    NoulCriteria,
    RetryPolicy,
    TypeSafeAPIConnectionError,
    TypeSafeAPIError,
    TypeSafeAuthenticationError,
    TypeSafeClient,
    TypeSafeError,
    TypeSafeInternalServerError,
    TypeSafeNotFoundError,
    TypeSafePermissionDeniedError,
    TypeSafeRateLimitError,
)

from .config import Config

TIMEOUT_S = 60.0
ENV_FILE = Path(__file__).with_name(".env")
_QUESTION = "single_request"
_SYSTEM_ONE = "/v1/systemone"
_MISSING_KEY = (
    "Missing TypeSafe API key. Set TYPESAFE_API_KEY in src/jev/.env. "
    "The next run reads that file again."
)
_MISSING_URL = (
    "Missing TypeSafe API URL. Set JEV_API_URL in src/jev/.env. "
    "The next run reads that file again."
)
_BAD_URL = (
    "JEV_API_URL in src/jev/.env must be the systemone address, "
    "ending in /v1/systemone."
)
_REJECTED_KEY = (
    "TypeSafe rejected the API key. Check TYPESAFE_API_KEY in src/jev/.env. "
    "The next run reads that file again."
)
_SDK_KEY = "API key must contain only printable ASCII characters without whitespace."
_EMPTY = "Enter the text to classify."
_NO_FUNDS = (
    "TypeSafe refused the request because the account has no quota or no funds. "
    "Fix billing, then run the command again."
)
_RATE_LIMIT = "TypeSafe rate limit reached. Wait a moment, then run the command again."
_NETWORK = "Could not reach TypeSafe. Check the network, then run the command again."
_FORBIDDEN = "This API key is not allowed to call the model."
_SERVER = "TypeSafe had a server error. Run the command again."
_OVERLOADED = "TypeSafe is overloaded. Wait a moment, then run the command again."
_QUOTA_CODES = frozenset({"insufficient_quota", "billing_hard_limit_reached"})


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
    env = _load_env(ENV_FILE)
    api_key = env.get("TYPESAFE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(_MISSING_KEY)
    api_url = env.get("JEV_API_URL", "").strip()
    if not api_url:
        raise RuntimeError(_MISSING_URL)
    try:
        with TypeSafeClient(
            api_key=api_key,
            base_url=_api_root(api_url),
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
        sentence = _guide(exc, settings.model)
        if sentence is None:
            raise
        raise RuntimeError(sentence) from exc
    return _decision(float(response.nouls[_QUESTION].noul), settings.yes_at)


def _api_root(url: str) -> str:
    """Host in front of /v1/systemone. The SDK appends that path itself."""
    text = url.strip().rstrip("/")
    if not text.endswith(_SYSTEM_ONE):
        raise RuntimeError(_BAD_URL)
    root = text[: -len(_SYSTEM_ONE)]
    if not root:
        raise RuntimeError(_BAD_URL)
    return root


def _decision(noul: float, yes_at: float) -> Decision:
    answer = "yes" if noul >= yes_at else "no"
    confidence = abs((2.0 * noul) - 1.0)
    return Decision(answer=answer, noul=noul, confidence=confidence)


def _guide(exc: TypeSafeError, model: str) -> str | None:
    """One instruction for a known API failure. None leaves the error unchanged."""
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
        return _NO_FUNDS if _no_funds(exc) else _RATE_LIMIT
    if isinstance(exc, TypeSafeInternalServerError):
        if exc.status == 529:
            return _OVERLOADED
        return _SERVER
    if isinstance(exc, TypeSafeAPIError):
        if exc.status == 529:
            return _OVERLOADED
        if _no_funds(exc):
            return _NO_FUNDS
        return f"TypeSafe request failed ({exc.status})."
    if str(exc) == _SDK_KEY:
        return _REJECTED_KEY
    return None


def _no_funds(exc: TypeSafeAPIError) -> bool:
    found = {getattr(exc, "code", None), getattr(exc, "type", None)}
    body = exc.body
    if isinstance(body, dict):
        found.add(body.get("code"))
        found.add(body.get("type"))
        nested = body.get("error")
        if isinstance(nested, dict):
            found.add(nested.get("code"))
            found.add(nested.get("type"))
    return any(value in _QUOTA_CODES for value in found)


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
