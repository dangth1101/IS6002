"""Run one SQL statement on a BIRD SQLite database, read-only, with a deadline.

One runner for the Predicted SQL and the Ground-truth SQL, used by the app,
the batch and the Subset script.
"""

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

TIMEOUT_S = 30
PROGRESS_STEPS = 10_000


@dataclass(frozen=True)
class Rows:
    columns: list[str]
    rows: list[tuple]


@dataclass(frozen=True)
class SqlError:
    message: str


@dataclass(frozen=True)
class Timeout:
    timeout_s: float


RunResult = Rows | SqlError | Timeout


def run(db_path: Path | str, sql: str, timeout_s: float = TIMEOUT_S) -> RunResult:
    # Read-only is the safety line: a Predicted DROP TABLE must not stick.
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)

    # SQLite calls the handler every N VM steps; non-zero aborts the query.
    # Set before execute so the deadline also covers fetchall, where SQLite
    # does most of its work.
    deadline = time.monotonic() + timeout_s
    conn.set_progress_handler(lambda: time.monotonic() > deadline, PROGRESS_STEPS)
    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description or []]
        return Rows(columns=columns, rows=rows)
    except sqlite3.Error as e:
        if time.monotonic() > deadline:
            return Timeout(timeout_s=timeout_s)
        return SqlError(message=str(e))
    finally:
        conn.close()
