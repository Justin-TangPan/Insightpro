"""
Database seam for InsightPro backend.

Primary store is Supabase Postgres (via DIRECT_URL / DATABASE_URL).
This module replaces the old SQLite `get_db()` context manager with a
psycopg2 connection yielding RealDictCursor rows, so existing call sites
that do `with get_db() as conn: c = conn.cursor(); ... dict(r)` work
with minimal SQL-syntax porting.

SQLite is no longer the primary store; trending.db is kept only as a
one-time migration source.
"""
import os
from pathlib import Path
from contextlib import contextmanager
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor, RealDictRow

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)


def _dsn() -> str:
    """Pick the best Postgres DSN: prefer DIRECT_URL (no pooler, for DDL),
    fall back to DATABASE_URL (pooler). Strip libpq-unrecognized params."""
    raw = os.getenv("DIRECT_URL", "") or os.getenv("DATABASE_URL", "")
    if not raw:
        raise RuntimeError("Neither DIRECT_URL nor DATABASE_URL is set in .env")
    if "?" in raw:
        base, query = raw.split("?", 1)
        kept = [
            p for p in query.split("&")
            if not p.startswith("pgbouncer=") and not p.startswith("statement_timeout=")
        ]
        raw = base + ("?" + "&".join(kept) if kept else "")
    return raw


@contextmanager
def get_db():
    """Context manager yielding a psycopg2 connection (RealDictCursor default).
    Commits on clean exit, rolls back on exception, always closes."""
    conn = psycopg2.connect(_dsn(), cursor_factory=RealDictCursor)
    conn.autocommit = False
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def dict_row(row: RealDictRow) -> dict:
    """Normalize a RealDictRow to a plain dict (RealDictRow is already dict-like,
    but this makes JSON serialization and downstream code explicit)."""
    return dict(row) if row is not None else {}
