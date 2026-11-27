"""Print short-clip gate totals and the latest rows."""

import sys

_RECENT = 20


def main() -> None:
    from .config import Config

    if not Config().log_enabled:
        print("No log.")
        return
    from .store import db_path, render

    path = db_path()
    if not path.is_file():
        print("No log.")
        return
    try:
        print(render(path, _RECENT))
    except Exception as exc:
        print(f"WARNING: short-clip gate log unreadable ({exc})", file=sys.stderr)


if __name__ == "__main__":
    main()
