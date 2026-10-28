"""Manual orchestration of the existing collector and analysis task registry."""
from __future__ import annotations

import json
import logging
import zlib
from time import monotonic

from db import get_db
from services.task_service import run_task

logger = logging.getLogger(__name__)
DOMAINS = {"technology_ecosystem", "ai_applications", "solutions", "community_insights", "competitor_dynamics"}
COLLECTORS = {
    "technology_ecosystem": ("github_daily",),
    "ai_applications": ("ai_applications_daily",),
    "solutions": ("solution_catalogs_daily",),
    "community_insights": ("community_insights_daily",),
    "competitor_dynamics": ("competitor_daily",),
}


def pipeline_steps(domain: str) -> list[dict]:
    if domain not in DOMAINS:
        raise ValueError("Unknown business domain")
    steps = [
        {"key": key, "stage": "数据采集", "status": "pending"} for key in COLLECTORS[domain]
    ] + [
        {"key": "discovery_sentinel_daily", "stage": "候选发现与去重", "status": "pending"},
        {"key": "radar_event_analysis_daily", "stage": "AI 分析", "status": "pending"},
        {"key": "board_insights_daily", "stage": "聚合排序与前台摘要", "status": "pending"},
    ]
    if domain == "ai_applications":
        steps.append({"key": "daily_ai_brief", "stage": "生成每日 AI 洞察简讯", "status": "pending"})
    return steps


def start_pipeline(domain: str, resume_from: int | None = None) -> dict:
    steps = pipeline_steps(domain)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"pipeline:{domain}",))
        cursor.execute("SELECT pg_try_advisory_xact_lock(%s) AS acquired", (zlib.crc32(f"pipeline:{domain}".encode()),))
        if cursor.fetchone()["acquired"]:
            cursor.execute("""UPDATE platform_task_runs SET status='failed',finished_at=NOW(),
                error='Worker stopped before completing the pipeline'
                WHERE task_key=%s AND status='running' AND heartbeat_at < NOW()-INTERVAL '2 hours'""",
                (f"pipeline:{domain}",))
        cursor.execute("SELECT id FROM platform_task_runs WHERE task_key=%s AND status='running' LIMIT 1", (f"pipeline:{domain}",))
        if cursor.fetchone():
            raise ValueError("Pipeline is already running")
        if resume_from is not None:
            cursor.execute("SELECT status,result FROM platform_task_runs WHERE id=%s AND task_key=%s", (resume_from, f"pipeline:{domain}"))
            previous = cursor.fetchone()
            if not previous or previous["status"] != "failed":
                raise ValueError("Only a failed pipeline can be resumed")
            old_steps = (previous["result"] or {}).get("steps") or []
            if [step["key"] for step in old_steps] != [step["key"] for step in steps]:
                raise ValueError("Pipeline definition changed; start a new run")
            steps = [dict(step) if step["status"] == "success" else {**steps[index], "status": "pending"}
                     for index, step in enumerate(old_steps)]
        cursor.execute("""INSERT INTO platform_task_runs (task_key,trigger,status,started_at,result)
            VALUES (%s,%s,'running',NOW(),%s::jsonb) RETURNING id""",
            (f"pipeline:{domain}", "resume" if resume_from is not None else "manual",
             json.dumps({"domain": domain, "steps": steps}, ensure_ascii=False)))
        return {"run_id": cursor.fetchone()["id"], "domain": domain, "steps": steps}


def execute_pipeline(run_id: int, domain: str, steps: list[dict]) -> None:
    lock_id = zlib.crc32(f"pipeline:{domain}".encode())
    with get_db() as lock_conn:
        lock_conn.cursor().execute("SELECT pg_advisory_lock(%s)", (lock_id,))
        try:
            _execute_pipeline(run_id, domain, steps)
        finally:
            lock_conn.cursor().execute("SELECT pg_advisory_unlock(%s)", (lock_id,))


def _execute_pipeline(run_id: int, domain: str, steps: list[dict]) -> None:
    for step in steps:
        if step["status"] == "success":
            continue
        step["status"] = "running"
        started = monotonic()
        _save(run_id, domain, steps)
        try:
            result = run_task(step["key"], "pipeline")
            if isinstance(result, dict) and result.get("status") in {"failed", "partial", "partial_success", "skipped"}:
                raise RuntimeError(json.dumps(result, ensure_ascii=False, default=str)[:1000])
            step["status"] = "success"
            step["result"] = result if isinstance(result, dict) else {"result": result}
            step["output_count"] = _output_count(step["key"], domain, step["result"])
            step["failed_count"] = 0
        except Exception as exc:
            logger.exception("Pipeline %s failed at %s", run_id, step["key"])
            step["status"] = "failed"
            step["failed_count"] = 1
            step["duration_ms"] = round((monotonic() - started) * 1000)
            step["error"] = str(exc)[:1000]
            _save(run_id, domain, steps, "failed", step["error"])
            return
        step["duration_ms"] = round((monotonic() - started) * 1000)
        _save(run_id, domain, steps)
    try:
        from services.page_snapshot_service import publish_page_snapshots_sync
        publish_page_snapshots_sync()
    except Exception as exc:
        logger.exception("Pipeline %s could not publish page snapshots", run_id)
        _save(run_id, domain, steps, "failed", str(exc)[:1000])
        return
    _save(run_id, domain, steps, "success")


def _output_count(key: str, domain: str, result: dict) -> int | None:
    if key == "discovery_sentinel_daily":
        value = result.get("discovered")
    elif key == "radar_event_analysis_daily":
        value = result.get("processed")
    elif key == "board_insights_daily":
        board = {"technology_ecosystem": "github", "ai_applications": "apps", "solutions": "solutions",
                 "community_insights": "community", "competitor_dynamics": "competitors"}[domain]
        value = result.get(board)
    elif key == "daily_ai_brief":
        value = result.get("selected_count")
    else:
        value = next((result[name] for name in ("count", "total", "new_items", "collected") if name in result), None)
    return value if type(value) is int and value >= 0 else None


def _save(run_id: int, domain: str, steps: list[dict], status: str = "running", error: str | None = None) -> None:
    counts = {name: 0 for name in ("input_count", "new_count", "changed_count", "skipped_count", "failed_count")}
    for step in steps:
        result = step.get("result") or {}
        for name, keys in {"input_count": ("input_count", "collected", "total"),
                           "new_count": ("new_count", "new_items", "inserted"),
                           "changed_count": ("changed_count", "updated"),
                           "skipped_count": ("skipped_count", "unchanged")}.items():
            value = next((result[key] for key in keys if type(result.get(key)) is int), 0)
            counts[name] += max(0, value)
        counts["failed_count"] += step.get("failed_count", 0)
    with get_db() as conn:
        conn.cursor().execute("""UPDATE platform_task_runs SET status=%s,result=%s::jsonb,error=%s,heartbeat_at=NOW(),
            finished_at=CASE WHEN %s='running' THEN NULL ELSE NOW() END,
            input_count=%s,new_count=%s,changed_count=%s,skipped_count=%s,failed_count=%s
            WHERE id=%s AND task_key=%s""",
            (status, json.dumps({"domain": domain, "steps": steps}, ensure_ascii=False, default=str),
             error, status, *(counts[name] for name in counts), run_id, f"pipeline:{domain}"))


def recent_pipelines(limit: int = 20) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT id,task_key,trigger,status,started_at,finished_at,result,error,
            input_count,new_count,changed_count,skipped_count,failed_count
            FROM platform_task_runs WHERE task_key LIKE 'pipeline:%%' ORDER BY started_at DESC LIMIT %s""", (limit,))
        return [dict(row) for row in cursor.fetchall()]
