"""Revise the classifier cases from a report."""

import sys

from .config import Config
from .edit import Proposal, WriteResult, apply_cases, ask, current_cases, propose, transcript
from .prompt import system_prompt

_EMPTY = "Enter the report."
_NO_TERMINAL = "Run this command in a terminal to approve a change."
_UNCHANGED = "Left src/jev/config.py unchanged."
_CHOICES = "y applies, n cancels, and revise asks a question."
_ANSWER = "Answer the question, or y or n."


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    report = " ".join(args) if args else sys.stdin.read()
    report = report.strip()
    if not report:
        print(_EMPTY)
        raise SystemExit(1)
    terminal = _terminal()
    if terminal is None:
        print(_NO_TERMINAL)
        raise SystemExit(1)
    try:
        _session(report, terminal, Config())
    finally:
        terminal.close()


def _session(report: str, terminal, config: Config) -> None:
    instructions, true_case, false_case = current_cases()
    messages = [
        {"role": "system", "content": system_prompt(config.max_cases_chars)},
        {
            "role": "user",
            "content": _report_message(instructions, true_case, false_case, report),
        },
    ]
    try:
        proposal = propose(messages, config)
    except RuntimeError as exc:
        print(exc)
        raise SystemExit(1) from exc
    recorded = False
    while True:
        _show(proposal)
        choice = _read_choice(terminal)
        if choice == "yes":
            _commit(proposal)
            return
        if choice == "no":
            print(_UNCHANGED)
            return
        if not recorded:
            messages.append({"role": "assistant", "content": transcript(proposal)})
            recorded = True
        try:
            question = ask(messages, config)
        except RuntimeError as exc:
            print(exc)
            continue
        print()
        print(question)
        answer = _read_answer(terminal)
        if answer == "yes":
            _commit(proposal)
            return
        if answer == "no":
            print(_UNCHANGED)
            return
        messages.append({"role": "assistant", "content": question})
        messages.append({"role": "user", "content": answer})
        try:
            proposal = propose(messages, config)
        except RuntimeError as exc:
            print(exc)
            continue
        recorded = False


def _commit(proposal: Proposal) -> None:
    try:
        result = apply_cases(proposal.true_case, proposal.false_case)
    except RuntimeError as exc:
        print(exc)
        raise SystemExit(1) from exc
    _report_write(result)


def _report_write(result: WriteResult) -> None:
    if not result.true_case and not result.false_case:
        print(_UNCHANGED)
        return
    if result.true_case and result.false_case:
        print("Updated true case and false case in src/jev/config.py.")
        return
    if result.true_case:
        print("Updated true case in src/jev/config.py.")
        return
    print("Updated false case in src/jev/config.py.")


def _show(proposal: Proposal) -> None:
    print(proposal.note)
    print()
    print("true case")
    print(proposal.true_case)
    print()
    print("false case")
    print(proposal.false_case)
    print()
    print(_CHOICES)


def _report_message(
    instructions: str,
    true_case: str,
    false_case: str,
    report: str,
) -> str:
    return (
        f"Question: {instructions}\n\n"
        f"True case: {true_case}\n\n"
        f"False case: {false_case}\n\n"
        f"Report: {report}"
    )


def _read_choice(terminal) -> str:
    while True:
        word = _line(terminal)
        if word is None:
            return "no"
        if word in {"y", "yes"}:
            return "yes"
        if word in {"n", "no"}:
            return "no"
        if word == "revise":
            return "revise"
        print(_CHOICES)


def _read_answer(terminal) -> str:
    while True:
        line = _raw_line(terminal)
        if line is None:
            return "no"
        word = line.strip().casefold()
        if word in {"y", "yes"}:
            return "yes"
        if word in {"n", "no"}:
            return "no"
        if word:
            return line.strip()
        print(_ANSWER)


def _line(terminal) -> str | None:
    line = _raw_line(terminal)
    if line is None:
        return None
    return line.strip().casefold()


def _raw_line(terminal) -> str | None:
    line = terminal.readline()
    if line == "":
        return None
    return line


def _terminal():
    try:
        return open("/dev/tty", encoding="utf-8")
    except OSError:
        return None


if __name__ == "__main__":
    main()
