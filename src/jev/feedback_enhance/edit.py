"""Ask OpenAI for new cases, and write a changed case into the classifier."""

import ast
import json
import os
from dataclasses import dataclass
from pathlib import Path

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

from jev.config import Config as Cases

from .config import Config

TIMEOUT_S = 60.0
CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.py"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
_LINE_WIDTH = 64
_MISSING_KEY = (
    "Missing OpenAI API key. Set OPENAI_API_KEY in src/jev/.env. "
    "The next run reads that file again."
)
_REJECTED_KEY = (
    "OpenAI rejected the API key. Check OPENAI_API_KEY in src/jev/.env. "
    "The next run reads that file again."
)
_NO_FUNDS = (
    "OpenAI refused the request because the account has no quota or no funds. "
    "Fix billing, then run the command again."
)
_RATE_LIMIT = "OpenAI rate limit reached. Wait a moment, then run the command again."
_NETWORK = "Could not reach OpenAI. Check the network, then run the command again."
_FORBIDDEN = "This API key is not allowed to call the model."
_SERVER = "OpenAI had a server error. Run the command again."
_BAD_REPLY = "The reply could not be read. Run the command again."
_TOO_LONG = "The proposed cases are too long. Left src/jev/config.py unchanged."
_WRITE = "Could not update src/jev/config.py. Left that file unchanged."
_ASK = (
    "Ask exactly one question that would let you make a better edit. "
    "Do not include replacement paragraphs."
)
_QUOTA_CODES = frozenset({"insufficient_quota", "billing_hard_limit_reached"})
_KEPT = ("model", "yes_at", "instructions")
_PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "note": {"type": "string"},
        "true_case": {"type": "string"},
        "false_case": {"type": "string"},
    },
    "required": ["note", "true_case", "false_case"],
    "additionalProperties": False,
}
_QUESTION_SCHEMA = {
    "type": "object",
    "properties": {"question": {"type": "string"}},
    "required": ["question"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Proposal:
    """A note and both full paragraphs."""

    note: str
    true_case: str
    false_case: str


@dataclass(frozen=True)
class WriteResult:
    """Whether each case was written."""

    true_case: bool
    false_case: bool


def current_cases() -> tuple[str, str, str]:
    """The question and the two paragraphs the classifier uses now."""
    settings = Cases()
    return settings.instructions, settings.true_case, settings.false_case


def transcript(proposal: Proposal) -> str:
    """The note and both paragraphs, as they are shown."""
    return (
        f"{proposal.note}\n\n"
        f"true case\n{proposal.true_case}\n\n"
        f"false case\n{proposal.false_case}"
    )


def propose(messages: list[dict[str, str]], config: Config) -> Proposal:
    """Return a proposal whose two paragraphs fit the cap. A failed call raises."""
    draft = list(messages)
    proposal = _proposal_call(draft, config)
    attempts = config.shrink_attempts if config.shrink_attempts > 0 else 0
    used = 0
    while not _fits(proposal, config) and used < attempts:
        draft = draft + [
            {"role": "assistant", "content": transcript(proposal)},
            {"role": "user", "content": _shrink_text(proposal, config)},
        ]
        proposal = _proposal_call(draft, config)
        used += 1
    if not _fits(proposal, config):
        raise RuntimeError(_TOO_LONG)
    return proposal


def ask(messages: list[dict[str, str]], config: Config) -> str:
    """Ask the model for one question. A failed call raises."""
    payload = _complete(
        list(messages) + [{"role": "user", "content": _ASK}],
        config,
        "case_question",
        _QUESTION_SCHEMA,
    )
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        raise RuntimeError(_BAD_REPLY)
    return question.strip()


def apply_cases(
    true_case: str,
    false_case: str,
    path: Path | None = None,
) -> WriteResult:
    """Replace a case whose words changed. The other case is left byte for byte."""
    target = CONFIG_FILE if path is None else path
    proposed = {
        "true_case": _paragraph(true_case),
        "false_case": _paragraph(false_case),
    }
    if not proposed["true_case"] or not proposed["false_case"]:
        raise RuntimeError(_WRITE)
    try:
        source = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(_WRITE) from exc
    try:
        tree = ast.parse(source)
        nodes = _case_nodes(tree)
        kept = _kept_values(tree)
        current = {name: _string_value(nodes[name].value) for name in proposed}
    except (SyntaxError, ValueError, RuntimeError) as exc:
        raise RuntimeError(_WRITE) from exc
    changed = {
        name: text
        for name, text in proposed.items()
        if not _same(current[name], text)
    }
    if not changed:
        return WriteResult(true_case=False, false_case=False)
    preserved = {
        name: _slice(source, nodes[name])
        for name in proposed
        if name not in changed
    }
    new_source = source
    ordered = sorted(changed, key=lambda name: nodes[name].lineno, reverse=True)
    for name in ordered:
        new_source = _splice(new_source, nodes[name], _assignment(name, changed[name]))
    try:
        check = ast.parse(new_source)
        checked = _case_nodes(check)
        values = {name: _string_value(checked[name].value) for name in proposed}
        if _kept_values(check) != kept:
            raise RuntimeError(_WRITE)
    except (SyntaxError, ValueError, RuntimeError) as exc:
        raise RuntimeError(_WRITE) from exc
    for name in proposed:
        expected = changed[name] if name in changed else current[name]
        if values[name] != expected:
            raise RuntimeError(_WRITE)
    for name, block in preserved.items():
        if block not in new_source or values[name] != current[name]:
            raise RuntimeError(_WRITE)
    _replace(target, new_source)
    return WriteResult(
        true_case="true_case" in changed,
        false_case="false_case" in changed,
    )


def _proposal_call(messages: list[dict[str, str]], config: Config) -> Proposal:
    payload = _complete(messages, config, "case_proposal", _PROPOSAL_SCHEMA)
    note = payload.get("note")
    true_case = payload.get("true_case")
    false_case = payload.get("false_case")
    if (
        not isinstance(note, str)
        or not isinstance(true_case, str)
        or not isinstance(false_case, str)
    ):
        raise RuntimeError(_BAD_REPLY)
    note = note.strip()
    true_case = _paragraph(true_case)
    false_case = _paragraph(false_case)
    if not note or not true_case or not false_case:
        raise RuntimeError(_BAD_REPLY)
    return Proposal(note=note, true_case=true_case, false_case=false_case)


def _complete(
    messages: list[dict[str, str]],
    config: Config,
    schema_name: str,
    schema: dict,
) -> dict:
    env = _load_env(ENV_FILE)
    api_key = env.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(_MISSING_KEY)
    client = OpenAI(
        api_key=api_key,
        base_url=config.base_url,
        timeout=TIMEOUT_S,
        max_retries=0,
    )
    try:
        response = client.chat.completions.create(
            model=config.model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
        )
    except APIError as exc:
        sentence = _guide(exc, config.model)
        if sentence is None:
            raise
        raise RuntimeError(sentence) from exc
    if not response.choices:
        raise RuntimeError(_BAD_REPLY)
    message = response.choices[0].message
    if getattr(message, "refusal", None):
        raise RuntimeError(_BAD_REPLY)
    return _object(message.content)


def _fits(proposal: Proposal, config: Config) -> bool:
    return len(proposal.true_case) + len(proposal.false_case) <= config.max_cases_chars


def _shrink_text(proposal: Proposal, config: Config) -> str:
    total = len(proposal.true_case) + len(proposal.false_case)
    return (
        "The two paragraphs together are "
        f"{total} characters. The maximum is {config.max_cases_chars}. "
        "Rewrite both paragraphs so the sum is at most that maximum. "
        "Keep the edit the report asked for. Cut examples before you cut the rule. "
        "Return the short note and both full paragraphs.\n\n"
        f"True case: {proposal.true_case}\n\n"
        f"False case: {proposal.false_case}"
    )


def _paragraph(text: str) -> str:
    return " ".join(text.split())


def _same(left: str, right: str) -> bool:
    return _paragraph(left) == _paragraph(right)


def _object(content: str | None) -> dict:
    if not content:
        raise RuntimeError(_BAD_REPLY)
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(_BAD_REPLY) from exc
    if not isinstance(value, dict):
        raise RuntimeError(_BAD_REPLY)
    return value


def _guide(exc: APIError, model: str) -> str | None:
    """One instruction for a known API failure. None leaves the error unchanged."""
    if isinstance(exc, APIConnectionError):
        return _NETWORK
    if isinstance(exc, AuthenticationError):
        return _REJECTED_KEY
    if isinstance(exc, PermissionDeniedError):
        return _FORBIDDEN
    if isinstance(exc, NotFoundError):
        return (
            "The model was not found. "
            f"The model name is {model} in src/jev/feedback_enhance/config.py."
        )
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


def _case_nodes(tree: ast.AST) -> dict[str, ast.AnnAssign]:
    found: dict[str, ast.AnnAssign] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "Config":
            continue
        for item in node.body:
            if not isinstance(item, ast.AnnAssign) or not isinstance(item.target, ast.Name):
                continue
            if item.target.id in ("true_case", "false_case") and item.value is not None:
                found[item.target.id] = item
    if set(found) != {"true_case", "false_case"}:
        raise RuntimeError(_WRITE)
    return found


def _kept_values(tree: ast.AST) -> dict[str, object]:
    found: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "Config":
            continue
        for item in node.body:
            if not isinstance(item, ast.AnnAssign) or not isinstance(item.target, ast.Name):
                continue
            if item.target.id in _KEPT and item.value is not None:
                found[item.target.id] = _literal(item.value)
    if set(found) != set(_KEPT):
        raise RuntimeError(_WRITE)
    return found


def _literal(node: ast.AST) -> object:
    if isinstance(node, ast.Constant):
        return node.value
    return _string_value(node)


def _string_value(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _string_value(node.left) + _string_value(node.right)
    raise ValueError


def _slice(source: str, node: ast.AST) -> str:
    lines = source.splitlines(keepends=True)
    return "".join(lines[node.lineno - 1 : node.end_lineno])


def _splice(source: str, node: ast.AST, replacement: str) -> str:
    lines = source.splitlines(keepends=True)
    block = replacement if replacement.endswith("\n") else replacement + "\n"
    start = node.lineno - 1
    end = node.end_lineno or node.lineno
    return "".join(lines[:start] + [block] + lines[end:])


def _assignment(name: str, paragraph: str) -> str:
    parts = _wrap(paragraph)
    quoted = []
    for index, part in enumerate(parts):
        body = part if index == len(parts) - 1 else part + " "
        quoted.append(f'        "{_escape(body)}"')
    inner = "\n".join(quoted)
    return f"    {name}: str = (\n{inner}\n    )"


def _wrap(paragraph: str) -> list[str]:
    words = paragraph.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        if not current:
            current = word
            continue
        if len(current) + 1 + len(word) <= _LINE_WIDTH:
            current = f"{current} {word}"
            continue
        lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _replace(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    except OSError as exc:
        raise RuntimeError(_WRITE) from exc
    finally:
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass
