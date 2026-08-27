"""One-time OpenCode SSO ticket persistence."""
from __future__ import annotations

from db import get_db


def create_ticket(token_hash: str, user_id: str, target_user_id: str | None, ttl_seconds: int) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO opencode_sso_tickets (token_hash, user_id, target_user_id, expires_at)
            VALUES (%s, %s, %s, NOW() + (%s * INTERVAL '1 second'))
            """,
            (token_hash, user_id, target_user_id, ttl_seconds),
        )
        cursor.execute("DELETE FROM opencode_sso_tickets WHERE expires_at < NOW() - INTERVAL '1 day'")


def consume_ticket(token_hash: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE opencode_sso_tickets
            SET used_at = NOW()
            WHERE token_hash = %s AND used_at IS NULL AND expires_at > NOW()
            RETURNING user_id::text, COALESCE(target_user_id, user_id)::text AS agent_user_id
            """,
            (token_hash,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def create_session(token_hash: str, user_id: str, agent_user_id: str, auth_role: str, agent_role: str, display_name: str, ttl_seconds: int) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO opencode_sso_sessions
              (token_hash, user_id, agent_user_id, auth_role, agent_role, display_name, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW() + (%s * INTERVAL '1 second'))
            """,
            (token_hash, user_id, agent_user_id, auth_role, agent_role, display_name, ttl_seconds),
        )
        cursor.execute("DELETE FROM opencode_sso_sessions WHERE expires_at < NOW() - INTERVAL '1 day'")


def get_session_user(token_hash: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id::text, agent_user_id::text, auth_role, agent_role, display_name
            FROM opencode_sso_sessions
            WHERE token_hash = %s AND revoked_at IS NULL AND expires_at > NOW()
            """,
            (token_hash,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


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
