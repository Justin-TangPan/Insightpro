"""Version and publish analysis prompts without removing the active version."""
from __future__ import annotations

import json

from db import get_db


def list_prompts() -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT id,prompt_name,scenario,version,status,system_prompt,user_prompt_template,created_at,published_at
                          FROM intelligence_prompts ORDER BY prompt_name,version DESC""")
        return [dict(row) for row in cursor.fetchall()]


def published_prompt(prompt_name: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT to_regclass('public.intelligence_prompts') AS table_name")
        table = cursor.fetchone()
        if not table or not table.get("table_name"):
            return None
        cursor.execute("""SELECT prompt_name,scenario,version,system_prompt,user_prompt_template
                          FROM intelligence_prompts WHERE prompt_name=%s AND status='published'""", (prompt_name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_draft(prompt_name: str, scenario: str, system_prompt: str, user_prompt_template: str, actor_user_id: str) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("prompt:" + prompt_name,))
        cursor.execute("SELECT COALESCE(MAX(version),0)+1 AS version FROM intelligence_prompts WHERE prompt_name=%s", (prompt_name,))
        version = cursor.fetchone()["version"]
        cursor.execute("""INSERT INTO intelligence_prompts
            (prompt_name,scenario,version,status,system_prompt,user_prompt_template,created_by)
            VALUES (%s,%s,%s,'draft',%s,%s,%s::uuid) RETURNING id,prompt_name,scenario,version,status,created_at""",
            (prompt_name, scenario, version, system_prompt, user_prompt_template, actor_user_id))
        result = dict(cursor.fetchone())
        cursor.execute("""INSERT INTO intelligence_audit
            (actor_user_id,action,object_type,object_key,after_state)
            VALUES (%s::uuid,'prompt_draft_created','prompt',%s,%s::jsonb)""",
            (actor_user_id, prompt_name, json.dumps({"version": version, "scenario": scenario})))
        return result


def publish_prompt(prompt_id: int, actor_user_id: str, rollback: bool = False) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM intelligence_prompts WHERE id=%s FOR UPDATE", (prompt_id,))
        target = cursor.fetchone()
        if not target:
            raise LookupError("Prompt version not found")
        cursor.execute("SELECT id,version FROM intelligence_prompts WHERE prompt_name=%s AND status='published' FOR UPDATE",
                       (target["prompt_name"],))
        current = cursor.fetchone()
        if current and current["id"] == prompt_id:
            return {"id": prompt_id, "version": target["version"], "status": "published"}
        if rollback and target["status"] == "draft":
            raise ValueError("A draft cannot be used as a rollback target")
        if current:
            cursor.execute("UPDATE intelligence_prompts SET status='archived' WHERE id=%s", (current["id"],))
        cursor.execute("UPDATE intelligence_prompts SET status='published',published_at=NOW() WHERE id=%s", (prompt_id,))
        action = "prompt_rolled_back" if rollback else "prompt_published"
        cursor.execute("""INSERT INTO intelligence_audit
            (actor_user_id,action,object_type,object_key,before_state,after_state)
            VALUES (%s::uuid,%s,'prompt',%s,%s::jsonb,%s::jsonb)""",
            (actor_user_id, action, target["prompt_name"],
             json.dumps({"version": current["version"] if current else None}),
             json.dumps({"version": target["version"], "rollback": rollback})))
    return {"id": prompt_id, "version": target["version"], "status": "published"}
