"""Persistence for private Agent work results and their reviewed publication state."""
from __future__ import annotations

from db import get_db


def create(user_id: str, session: dict, artifact_id: str, title: str, artifact_type: str, content: str, filename: str, mime_type: str) -> dict:
    snapshot = session["context_snapshot"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO agent_artifacts (id, user_id, session_id, task_key, type, title, content, filename, mime_type, source_type, source_id, requirement_id, solution_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *, octet_length(content) AS size_bytes""",
            (artifact_id, user_id, session["id"], session.get("task_key", ""), artifact_type, title, content, filename, mime_type,
             snapshot.get("context_type"), snapshot.get("context_id"), int(snapshot["context_id"]) if snapshot.get("context_type") == "requirement" and str(snapshot.get("context_id", "")).isdigit() else None,
             int(snapshot["context_id"]) if snapshot.get("context_type") == "solution" and str(snapshot.get("context_id", "")).isdigit() else None),
        )
        return dict(cursor.fetchone())


def list_for_user(user_id: str, limit: int = 30) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id::text, session_id::text, task_key, type, title, filename, mime_type, octet_length(content) AS size_bytes, source_type, source_id, knowledge_status, created_at, updated_at FROM agent_artifacts WHERE user_id=%s ORDER BY updated_at DESC LIMIT %s", (user_id, limit))
        return [dict(row) for row in cursor.fetchall()]


def get_for_user(user_id: str, artifact_id: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor(); cursor.execute("SELECT *, octet_length(content) AS size_bytes FROM agent_artifacts WHERE id=%s AND user_id=%s", (artifact_id, user_id)); row = cursor.fetchone()
        return dict(row) if row else None


def request_knowledge(user_id: str, artifact_id: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor(); cursor.execute("UPDATE agent_artifacts SET knowledge_status='requested', updated_at=NOW() WHERE id=%s AND user_id=%s AND knowledge_status='private' RETURNING *", (artifact_id, user_id)); row = cursor.fetchone()
        return dict(row) if row else None


def requested() -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor(); cursor.execute("SELECT id::text, user_id::text, title, type, content, knowledge_status, created_at FROM agent_artifacts WHERE knowledge_status='requested' ORDER BY updated_at ASC")
        return [dict(row) for row in cursor.fetchall()]


def publish(artifact_id: str, path: str, reviewer_id: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor(); cursor.execute("UPDATE agent_artifacts SET knowledge_status='published', knowledge_path=%s, reviewed_by=%s, reviewed_at=NOW(), updated_at=NOW() WHERE id=%s AND knowledge_status='requested' RETURNING *", (path, reviewer_id, artifact_id)); row = cursor.fetchone()
        return dict(row) if row else None
