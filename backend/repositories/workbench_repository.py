"""PostgreSQL access for the Requirements and Solutions workbench."""
from __future__ import annotations

from db import get_db


def _rows(cursor) -> list[dict]:
    return [dict(row) for row in cursor.fetchall()]


def list_requirements(user_id: str, status: str | None = None) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT r.*, COUNT(rs.solution_id)::int AS solution_count
            FROM requirements r
            LEFT JOIN requirement_solutions rs ON rs.requirement_id = r.id
            WHERE r.user_id = %s AND (%s IS NULL OR r.status = %s)
            GROUP BY r.id
            ORDER BY r.updated_at DESC
            """,
            (user_id, status, status),
        )
        return _rows(cursor)


def get_requirement(user_id: str, requirement_id: int) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM requirements WHERE id=%s AND user_id=%s", (requirement_id, user_id))
        row = cursor.fetchone()
        if not row:
            return None
        result = dict(row)
        cursor.execute(
            """
            SELECT s.* FROM solutions s
            JOIN requirement_solutions rs ON rs.solution_id = s.id
            WHERE rs.requirement_id=%s AND s.user_id=%s
            ORDER BY s.updated_at DESC
            """,
            (requirement_id, user_id),
        )
        result["solutions"] = _rows(cursor)
        return result


def create_requirement(user_id: str, data: dict) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO requirements
              (user_id, title, description, status, priority, source_type, source_id, source_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                user_id, data["title"], data.get("description", ""), data.get("status", "draft"),
                data.get("priority", "medium"), data.get("source_type", "manual"),
                data.get("source_id"), data.get("source_url"),
            ),
        )
        result = dict(cursor.fetchone())
        result["solutions"] = []
        return result


def update_requirement(user_id: str, requirement_id: int, data: dict) -> dict | None:
    if not data:
        return get_requirement(user_id, requirement_id)
    columns = {
        "title", "description", "status", "priority", "source_type", "source_id", "source_url",
    }
    values = [(key, value) for key, value in data.items() if key in columns]
    assignments = ", ".join(f"{key}=%s" for key, _ in values)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE requirements SET {assignments}, updated_at=NOW() WHERE id=%s AND user_id=%s RETURNING id",
            [value for _, value in values] + [requirement_id, user_id],
        )
        if not cursor.fetchone():
            return None
    return get_requirement(user_id, requirement_id)


def delete_requirement(user_id: str, requirement_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM requirements WHERE id=%s AND user_id=%s", (requirement_id, user_id))
        return cursor.rowcount > 0


def list_solutions(user_id: str) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.*, COUNT(rs.requirement_id)::int AS requirement_count
            FROM solutions s
            LEFT JOIN requirement_solutions rs ON rs.solution_id = s.id
            WHERE s.user_id = %s
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            """,
            (user_id,),
        )
        return _rows(cursor)


def get_solution(user_id: str, solution_id: int) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM solutions WHERE id=%s AND user_id=%s", (solution_id, user_id))
        row = cursor.fetchone()
        if not row:
            return None
        result = dict(row)
        cursor.execute(
            """
            SELECT r.* FROM requirements r
            JOIN requirement_solutions rs ON rs.requirement_id = r.id
            WHERE rs.solution_id=%s AND r.user_id=%s
            ORDER BY r.updated_at DESC
            """,
            (solution_id, user_id),
        )
        result["requirements"] = _rows(cursor)
        return result


def create_solution(user_id: str, data: dict, requirement_id: int | None = None) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        if requirement_id is not None:
            cursor.execute("SELECT 1 FROM requirements WHERE id=%s AND user_id=%s", (requirement_id, user_id))
            if not cursor.fetchone():
                return None
        cursor.execute(
            """
            INSERT INTO solutions
              (user_id, name, description, category, status, version, reference_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                user_id, data["name"], data.get("description", ""), data.get("category", "未分类"),
                data.get("status", "draft"), data.get("version", "v0.1.0"), data.get("reference_url"),
            ),
        )
        result = dict(cursor.fetchone())
        if requirement_id is not None:
            cursor.execute(
                "INSERT INTO requirement_solutions (requirement_id, solution_id) VALUES (%s, %s)",
                (requirement_id, result["id"]),
            )
        result["requirements"] = []
        return result


def update_solution(user_id: str, solution_id: int, data: dict) -> dict | None:
    if not data:
        return get_solution(user_id, solution_id)
    columns = {"name", "description", "category", "status", "version", "reference_url"}
    values = [(key, value) for key, value in data.items() if key in columns]
    assignments = ", ".join(f"{key}=%s" for key, _ in values)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE solutions SET {assignments}, updated_at=NOW() WHERE id=%s AND user_id=%s RETURNING id",
            [value for _, value in values] + [solution_id, user_id],
        )
        if not cursor.fetchone():
            return None
    return get_solution(user_id, solution_id)


def delete_solution(user_id: str, solution_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM solutions WHERE id=%s AND user_id=%s", (solution_id, user_id))
        return cursor.rowcount > 0


def link_solution(user_id: str, requirement_id: int, solution_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM requirements WHERE id=%s AND user_id=%s",
            (requirement_id, user_id),
        )
        if not cursor.fetchone():
            return False
        cursor.execute("SELECT 1 FROM solutions WHERE id=%s AND user_id=%s", (solution_id, user_id))
        if not cursor.fetchone():
            return False
        cursor.execute(
            """
            INSERT INTO requirement_solutions (requirement_id, solution_id)
            VALUES (%s, %s) ON CONFLICT DO NOTHING
            """,
            (requirement_id, solution_id),
        )
        return True


def unlink_solution(user_id: str, requirement_id: int, solution_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM requirement_solutions rs
            USING requirements r, solutions s
            WHERE rs.requirement_id=r.id AND rs.solution_id=s.id
              AND r.id=%s AND s.id=%s AND r.user_id=%s AND s.user_id=%s
            """,
            (requirement_id, solution_id, user_id, user_id),
        )
        return cursor.rowcount > 0


def get_summary(user_id: str) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM requirements WHERE user_id=%s)::int AS requirement_count,
              (SELECT COUNT(*) FROM solutions WHERE user_id=%s)::int AS solution_count
            """,
            (user_id, user_id),
        )
        result = dict(cursor.fetchone())
        cursor.execute(
            """
            SELECT id, title, status, priority, updated_at
            FROM requirements WHERE user_id=%s ORDER BY updated_at DESC LIMIT 5
            """,
            (user_id,),
        )
        result["recent_requirements"] = _rows(cursor)
        return result
