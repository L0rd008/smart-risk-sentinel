"""Database connection helper.

Owned by Member 1. Returns a psycopg2 connection configured from .env.
Use as a context manager so connections close cleanly:

    from app.db_connect import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM borrowers LIMIT 5")
        rows = cur.fetchall()
"""
from contextlib import contextmanager
from typing import Iterator

import psycopg2
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor

from app.config import Config


def get_raw_connection() -> PgConnection:
    """Open and return a new psycopg2 connection.

    Caller is responsible for closing it. Prefer `get_connection()` below
    for the context-manager form.
    """
    return psycopg2.connect(Config.db_dsn())


@contextmanager
def get_connection() -> Iterator[PgConnection]:
    """Context manager yielding a psycopg2 connection.

    Commits on clean exit, rolls back on exception, always closes.
    Cursors created via `conn.cursor(cursor_factory=RealDictCursor)` will
    yield dict-shaped rows, which match the API contract more directly.
    """
    conn = get_raw_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def dict_cursor(conn: PgConnection):
    """Convenience: return a RealDictCursor on the given connection."""
    return conn.cursor(cursor_factory=RealDictCursor)
