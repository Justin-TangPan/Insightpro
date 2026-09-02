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


def create_agent_session(session_id: str, user_id: str, context: dict, task_key: str = "", task_title: str = "", task_status: str = "ready", default_prompt: str = "") -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO agent_sessions (id, user_id, context_type, context_id, context_title, context_snapshot, title, task_key, task_title, task_status, default_prompt)
               VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s) RETURNING *""",
            (session_id, user_id, context["context_type"], context["context_id"], context["title"], __import__("json").dumps(context), task_title or context["title"], task_key, task_title, task_status, default_prompt),
        )
        return dict(cursor.fetchone())


def get_agent_session(user_id: str, session_id: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agent_sessions WHERE id=%s AND user_id=%s", (session_id, user_id))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_chat_session(session_id: str, user_id: str, page_title: str = "", page_path: str = "") -> dict:
    context = {"page_title": page_title, "page_path": page_path} if page_title else {}
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO agent_sessions (id, user_id, context_type, context_id, context_title, context_snapshot, task_key, task_title, task_status)
               VALUES (%s,%s,'chat',%s,%s,%s::jsonb,%s,%s,'ready') RETURNING *""",
            (session_id, user_id, session_id, page_title, __import__("json").dumps(context), "page_analysis" if page_title else "free_chat", "分析当前页面" if page_title else "自由讨论"),
        )
        return dict(cursor.fetchone())


def list_agent_sessions(user_id: str) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id::text, title, context_type, context_title, task_key, task_title, task_status, updated_at FROM agent_sessions WHERE user_id=%s ORDER BY updated_at DESC LIMIT 30", (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def delete_agent_session(user_id: str, session_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM agent_sessions WHERE id=%s AND user_id=%s", (session_id, user_id))
        return cursor.rowcount == 1


def set_hermes_session(user_id: str, session_id: str, hermes_session_id: str) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE agent_sessions SET hermes_session_id=%s WHERE id=%s AND user_id=%s", (hermes_session_id, session_id, user_id))


def append_conversation(user_id: str, session_id: str, user_message: str, assistant_message: str) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        title = user_message.strip().replace("\n", " ")[:40] or "新对话"
        cursor.execute(
            """UPDATE agent_sessions
               SET conversation=conversation || %s::jsonb,
                   title=CASE WHEN title='新对话' THEN %s ELSE title END,
                   task_status=CASE WHEN task_status='ready' THEN 'working' ELSE task_status END, updated_at=NOW()
               WHERE id=%s AND user_id=%s""",
            (__import__("json").dumps([{"role": "user", "content": user_message}, {"role": "assistant", "content": assistant_message}]), title, session_id, user_id),
        )


def update_context_snapshot(user_id: str, session_id: str, snapshot: dict) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE agent_sessions SET context_snapshot=%s::jsonb, updated_at=NOW() WHERE id=%s AND user_id=%s RETURNING *", (__import__("json").dumps(snapshot), session_id, user_id))
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
