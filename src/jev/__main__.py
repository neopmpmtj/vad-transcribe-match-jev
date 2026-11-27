"""Classify one entry from the command line."""

import sys

from .classify import classify


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    entry = " ".join(args) if args else sys.stdin.read()
    try:
        decision = classify(entry)
    except RuntimeError as exc:
        print(exc)
        raise SystemExit(1) from exc
    print(decision.answer)
    print(f"confidence {decision.confidence:.2f}")


if __name__ == "__main__":
    main()
