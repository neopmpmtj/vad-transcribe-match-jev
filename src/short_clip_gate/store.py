"""SQLite log of finished clips. Import this only while logging is on."""

import sqlite3
from datetime import datetime
from pathlib import Path

_CREATE = """
CREATE TABLE IF NOT EXISTS clips (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    utterance_n INTEGER NOT NULL,
    content_s REAL,
    captured_s REAL,
    cutoff_s REAL NOT NULL,
    reason TEXT NOT NULL CHECK (reason IN ('short', 'empty', 'sent'))
)
"""

_COUNTS = """
SELECT
    COUNT(*) AS clips,
    COALESCE(SUM(reason = 'sent'), 0) AS sent,
    COALESCE(SUM(reason = 'short'), 0) AS short,
    COALESCE(SUM(reason = 'empty'), 0) AS empty
FROM clips
"""

_RECENT = """
SELECT created_at, utterance_n, reason, content_s, captured_s, cutoff_s
FROM clips
ORDER BY id DESC
LIMIT ?
"""


def db_path() -> Path:
    """Database file beside this module, independent of the working directory."""
    return Path(__file__).resolve().parent / "short_clip_gate.sqlite"


class Store:
    """One open database for the life of the listener."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(
        self,
        utterance_n: int,
        content_s: float | None,
        captured_s: float | None,
        cutoff_s: float,
        reason: str,
    ) -> None:
        created_at = datetime.now().astimezone().isoformat(timespec="seconds")
        self._connection.execute(
            """
            INSERT INTO clips (
                created_at, utterance_n, content_s, captured_s, cutoff_s, reason
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (created_at, utterance_n, content_s, captured_s, cutoff_s, reason),
        )
        self._connection.commit()


def open_store(path: Path) -> Store:
    """Create the file and table, then return an open store."""
    connection = sqlite3.connect(path)
    connection.execute(_CREATE)
    connection.commit()
    return Store(connection)


def render(path: Path, limit: int = 20) -> str:
    """Totals for the whole table, then the latest rows."""
    uri = f"{path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        clips, sent, short, empty = (
            int(value) for value in connection.execute(_COUNTS).fetchone()
        )
        rows = connection.execute(_RECENT, (limit,)).fetchall()
    finally:
        connection.close()
    lines = [
        f"clips {clips}",
        f"sent {sent} ({_pct(sent, clips)})",
        f"short {short} ({_pct(short, clips)})",
        f"empty {empty} ({_pct(empty, clips)})",
        f"fails {short + empty} ({_pct(short + empty, clips)})",
    ]
    if rows:
        lines.append("")
        lines.extend(_row(row) for row in rows)
    return "\n".join(lines)


def _pct(part: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{(100.0 * part / total):.1f}%"


def _seconds(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):.3f}s"


def _row(row: tuple) -> str:
    created_at, utterance_n, reason, content_s, captured_s, cutoff_s = row
    return (
        f"{created_at} [{utterance_n}] {reason} "
        f"content {_seconds(content_s)} captured {_seconds(captured_s)} "
        f"cutoff {_seconds(cutoff_s)}"
    )
