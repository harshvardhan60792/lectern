"""The only place that opens database connections.

Every query in the project goes through a connection from here, and every value
is passed as a parameter (``?``), never pasted into the SQL text.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import config

SCHEMA = Path(__file__).with_name("schema.sql")


def _setup(conn: sqlite3.Connection) -> sqlite3.Connection:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(path or config.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)  # autocommit; we open transactions explicitly
    conn.execute("PRAGMA journal_mode = WAL")
    return _setup(conn)


def read_only(path: Path | str | None = None) -> sqlite3.Connection:
    """A connection that cannot change anything, used by "Ask the data"."""
    path = Path(path or config.db_path).resolve()
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    return _setup(conn)


@contextmanager
def transaction(conn: sqlite3.Connection):
    """All statements inside succeed together or are all undone."""
    conn.execute("BEGIN")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))


def set_current_user(conn: sqlite3.Connection, user_id: int | None) -> None:
    """Lets database triggers know who is making changes (see trg_grade_audit)."""
    conn.execute("UPDATE app_session SET user_id = ? WHERE id = 1", (user_id,))
