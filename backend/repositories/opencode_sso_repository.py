"""One-time OpenCode SSO ticket persistence."""
from __future__ import annotations

from db import get_db


def create_ticket(token_hash: str, user_id: str, ttl_seconds: int) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO opencode_sso_tickets (token_hash, user_id, expires_at)
            VALUES (%s, %s, NOW() + (%s * INTERVAL '1 second'))
            """,
            (token_hash, user_id, ttl_seconds),
        )
        cursor.execute("DELETE FROM opencode_sso_tickets WHERE expires_at < NOW() - INTERVAL '1 day'")


def consume_ticket(token_hash: str) -> str | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE opencode_sso_tickets
            SET used_at = NOW()
            WHERE token_hash = %s AND used_at IS NULL AND expires_at > NOW()
            RETURNING user_id::text
            """,
            (token_hash,),
        )
        row = cursor.fetchone()
        return row["user_id"] if row else None


def create_session(token_hash: str, user_id: str, ttl_seconds: int) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO opencode_sso_sessions (token_hash, user_id, expires_at)
            VALUES (%s, %s, NOW() + (%s * INTERVAL '1 second'))
            """,
            (token_hash, user_id, ttl_seconds),
        )
        cursor.execute("DELETE FROM opencode_sso_sessions WHERE expires_at < NOW() - INTERVAL '1 day'")


def get_session_user(token_hash: str) -> str | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id::text FROM opencode_sso_sessions
            WHERE token_hash = %s AND revoked_at IS NULL AND expires_at > NOW()
            """,
            (token_hash,),
        )
        row = cursor.fetchone()
        return row["user_id"] if row else None


def revoke_user_sessions(user_id: str) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE opencode_sso_sessions SET revoked_at = NOW()
            WHERE user_id = %s AND revoked_at IS NULL
            """,
            (user_id,),
        )
