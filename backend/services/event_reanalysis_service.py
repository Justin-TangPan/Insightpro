"""Explicitly reanalyze a bounded Event selection after a prompt or rule change."""
from __future__ import annotations

import json

from db import get_db
from services.event_service import analyze_event_for_review


SCOPES = {"new_event", "recent_7_days", "pending_review", "active", "selected"}


def start_reanalysis(scope: str, actor_user_id: str, business_scope: str | None = None,
                     event_ids: list[int] | None = None) -> dict:
    if scope not in SCOPES or (scope == "selected" and not event_ids):
        raise ValueError("Choose a supported nonempty Event selection")
    if event_ids and (scope != "selected" or len(event_ids) > 500):
        raise ValueError("Selected Event IDs require the selected scope and a maximum of 500 IDs")
    where = {"new_event": "e.analysis_version=0", "recent_7_days": "e.created_at >= NOW()-INTERVAL '7 days'",
             "pending_review": "e.status='pending_review'", "active": "e.status='active'",
             "selected": "e.id=ANY(%s)"}[scope]
    params = ([event_ids] if scope == "selected" else []) + [business_scope, business_scope]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""SELECT e.id FROM intelligence_events e WHERE {where}
            AND e.status IN ('active','pending_review')
            AND (%s::text IS NULL OR %s=ANY(e.business_scopes))
            ORDER BY e.id DESC LIMIT 500""", params)
        ids = [row["id"] for row in cursor.fetchall()]
        cursor.execute("""INSERT INTO platform_task_runs
            (task_key,trigger,status,started_at,input_count,result)
            VALUES ('event_analysis_recompute','manual','running',NOW(),%s,%s::jsonb) RETURNING id""",
            (len(ids), json.dumps({"scope": scope, "business_scope": business_scope, "event_ids": ids})))
        return {"run_id": cursor.fetchone()["id"], "event_ids": ids}


def execute_reanalysis(run_id: int, event_ids: list[int], actor_user_id: str) -> None:
    succeeded, failures = 0, []
    for event_id in event_ids:
        try:
            analyze_event_for_review(event_id, actor_user_id)
            succeeded += 1
        except Exception as exc:
            failures.append({"event_id": event_id, "error": str(exc)[:300]})
        with get_db() as conn:
            conn.cursor().execute("""UPDATE platform_task_runs SET heartbeat_at=NOW(),
                new_count=%s,failed_count=%s,result=jsonb_set(COALESCE(result,'{}'::jsonb),
                '{failures}',%s::jsonb,true) WHERE id=%s""",
                (succeeded, len(failures), json.dumps(failures, ensure_ascii=False), run_id))
    with get_db() as conn:
        conn.cursor().execute("""UPDATE platform_task_runs SET status=%s,finished_at=NOW(),
            error=%s WHERE id=%s""",
            ("failed" if failures else "success", f"{len(failures)} Event analyses failed" if failures else None, run_id))
