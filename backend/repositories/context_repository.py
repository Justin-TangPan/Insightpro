"""Read-only data access for normalized InsightPro business context."""
from __future__ import annotations

from db import get_db


def github_project(repo_name: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT g.*, e.summary AS evaluation_summary, e.total AS evaluation_score,
                   e.level AS evaluation_level, e.recommendation, e.reasoning
            FROM github_trending g
            LEFT JOIN trending_business_eval e
              ON e.scrape_date=g.scrape_date AND e.repo_name=g.repo_name
            WHERE g.repo_name=%s
            ORDER BY g.scrape_date DESC, g.id DESC LIMIT 1
            """,
            (repo_name,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def cloud_solution(solution_id: int) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM aliyun_solutions WHERE id=%s AND is_active=TRUE", (solution_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def vendor_update(update_id: int) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cloud_vendor_news WHERE id=%s", (update_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def related_requirements(user_id: str, source_type: str, source_id: str) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, title, status, priority, updated_at FROM requirements
               WHERE user_id=%s AND source_id=%s AND (source_type=%s OR (%s='cloud_solution' AND source_type='aliyun_solution') OR (%s='github_project' AND source_type='github_trending'))
               ORDER BY updated_at DESC LIMIT 8""",
            (user_id, source_id, source_type, source_type, source_type),
        )
        return [dict(row) for row in cursor.fetchall()]


def create_agent_session(session_id: str, user_id: str, context: dict) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO agent_sessions (id, user_id, context_type, context_id, context_title, context_snapshot)
               VALUES (%s,%s,%s,%s,%s,%s::jsonb) RETURNING *""",
            (session_id, user_id, context["context_type"], context["context_id"], context["title"], __import__("json").dumps(context)),
        )
        return dict(cursor.fetchone())


def get_agent_session(user_id: str, session_id: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agent_sessions WHERE id=%s AND user_id=%s", (session_id, user_id))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_agent_action(action_id: str, session_id: str, user_id: str, action: str, payload: dict) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO agent_actions (id, session_id, user_id, action, payload)
               VALUES (%s,%s,%s,%s,%s::jsonb) RETURNING *""",
            (action_id, session_id, user_id, action, __import__("json").dumps(payload)),
        )
        return dict(cursor.fetchone())


def get_agent_action(user_id: str, action_id: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agent_actions WHERE id=%s AND user_id=%s", (action_id, user_id))
        row = cursor.fetchone()
        return dict(row) if row else None


def confirm_agent_action(action_id: str, result: dict) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE agent_actions SET status='confirmed', result=%s::jsonb, confirmed_at=NOW() WHERE id=%s AND status='proposed'",
            (__import__("json").dumps(result), action_id),
        )
