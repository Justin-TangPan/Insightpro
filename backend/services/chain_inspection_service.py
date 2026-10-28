"""Inspect the collected fact through its published consumers."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import requests

from db import get_db
from services.task_service import source_task_key
from settings import settings


def _recent(value, days: int = 2) -> bool:
    return bool(value and value >= datetime.now(timezone.utc) - timedelta(days=days))


def _frontend_status() -> str:
    try:
        response = requests.get("http://frontend:3000/api/home-email-snapshot",
                                headers={"x-insight-internal-key": settings.HERMES_SSO_SECRET}, timeout=8)
        response.raise_for_status()
        payload = response.json()
        as_of = datetime.fromisoformat(str(payload["as_of"]).replace("Z", "+00:00"))
        if not as_of.tzinfo or not isinstance(payload.get("boards"), list):
            return "FAILED"
        return "HEALTHY" if _recent(as_of) else "STALE"
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return "FAILED"


def inspect_chain(*, persist: bool = True, frontend_status: str | None = None) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT source_key,name,adapter,schedule,enabled,health_status,last_success_at,last_error
            FROM intelligence_sources ORDER BY source_key""")
        sources = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT MAX(generated_at) AS latest FROM page_snapshots")
        snapshot_at = cursor.fetchone()["latest"]
        cursor.execute("""SELECT status,sent_at,updated_at FROM email_delivery_attempts
            ORDER BY updated_at DESC LIMIT 1""")
        delivery = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) AS count FROM email_subscriptions WHERE enabled")
        subscriptions = cursor.fetchone()["count"]
    frontend = frontend_status or _frontend_status()
    snapshot = "HEALTHY" if _recent(snapshot_at) else "STALE"
    email = ("DISABLED" if subscriptions == 0 else "UNKNOWN" if not delivery else
             "FAILED" if delivery["status"] == "failed" else
             "HEALTHY" if delivery["status"] == "sent" and _recent(delivery["sent_at"]) else "STALE")
    results = []
    for source in sources:
        key = source["source_key"]
        if not source["enabled"]:
            stages = {stage: "DISABLED" for stage in
                      ("Source", "Collector", "Raw", "Candidate", "Event", "AI", "Snapshot", "Frontend", "Email")}
        else:
            task = source_task_key(source)
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""SELECT status,started_at FROM platform_task_runs
                    WHERE task_key=%s ORDER BY started_at DESC LIMIT 1""", (task,))
                run = cursor.fetchone()
                cursor.execute("""SELECT MAX(observed_at) AS latest,COUNT(*)::int AS count
                    FROM intelligence_raw_items WHERE source_key=%s""", (key,))
                raw = cursor.fetchone()
                cursor.execute("""SELECT COUNT(DISTINCT candidate.id)::int AS backlog,
                    MIN(candidate.created_at) AS oldest FROM intelligence_candidates candidate
                    JOIN intelligence_candidate_evidence evidence ON evidence.candidate_id=candidate.id
                    JOIN intelligence_raw_items raw ON raw.id=evidence.raw_item_id
                    WHERE raw.source_key=%s AND candidate.status='pending'""", (key,))
                candidate = cursor.fetchone()
                cursor.execute("""SELECT COUNT(DISTINCT event.id)::int AS total,
                    MAX(event.last_seen_at) AS latest,
                    COUNT(DISTINCT event.id) FILTER (WHERE event.analysis_status='stale')::int AS stale,
                    COUNT(DISTINCT event.id) FILTER (WHERE event.analysis_status='failed')::int AS failed
                    FROM intelligence_events event
                    JOIN intelligence_event_evidence evidence ON evidence.event_id=event.id
                    JOIN intelligence_raw_items raw ON raw.id=evidence.raw_item_id
                    WHERE raw.source_key=%s AND event.status IN ('active','pending_review')""", (key,))
                event = cursor.fetchone()
            source_status = ("FAILED" if source["last_error"] or source["health_status"] in ("failed", "HTTP_ERROR") else
                             "HEALTHY" if _recent(source["last_success_at"]) else "STALE")
            collector_status = ("UNKNOWN" if not run else "FAILED" if run["status"] in ("failed", "blocked") else
                                "HEALTHY" if run["status"] == "success" and _recent(run["started_at"]) else "STALE")
            raw_status = "HEALTHY" if _recent(raw["latest"], 7) else "STALE" if raw["count"] else "UNKNOWN"
            candidate_status = ("STALE" if candidate["oldest"] and not _recent(candidate["oldest"], 7) else
                                "DEGRADED" if candidate["backlog"] > 100 else "HEALTHY")
            event_status = ("UNKNOWN" if not raw["count"] else "DEGRADED" if not event["total"] else
                            "HEALTHY" if _recent(event["latest"], 7) else "STALE")
            ai_status = "FAILED" if event["failed"] else "STALE" if event["stale"] else "HEALTHY" if event["total"] else "UNKNOWN"
            stages = dict(zip(("Source", "Collector", "Raw", "Candidate", "Event", "AI", "Snapshot", "Frontend", "Email"),
                              (source_status, collector_status, raw_status, candidate_status, event_status,
                               ai_status, snapshot, frontend, email)))
        overall = ("DISABLED" if not source["enabled"] else "FAILED" if "FAILED" in stages.values() else
                   "DEGRADED" if any(value in ("DEGRADED", "STALE") for value in stages.values()) else
                   "UNKNOWN" if "UNKNOWN" in stages.values() else "HEALTHY")
        results.append({"source_key": key, "name": source["name"], "status": overall, "stages": stages})
    if persist:
        with get_db() as conn:
            cursor = conn.cursor()
            for row in results:
                cursor.execute("""INSERT INTO intelligence_inspection_results(source_key,status,stages)
                    VALUES (%s,%s,%s::jsonb)""", (row["source_key"], row["status"],
                                                   json.dumps(row["stages"])))
    return {"items": results, "checked_at": datetime.now(timezone.utc).isoformat()}


def recent_inspections() -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT DISTINCT ON (result.source_key) result.source_key,source.name,
            result.status,result.stages,result.checked_at
            FROM intelligence_inspection_results result
            JOIN intelligence_sources source ON source.source_key=result.source_key
            ORDER BY result.source_key,result.checked_at DESC,result.id DESC""")
        rows = [dict(row) for row in cursor.fetchall()]
    return {"items": rows}
