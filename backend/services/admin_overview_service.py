"""Exact daily counts for the five front-office intelligence domains."""
from __future__ import annotations

from db import get_db
from services.pipeline_service import DOMAINS
from services.task_service import list_tasks


def overview() -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT source.source_key,source.name,source.business_scopes,source.health_status,
            source.last_success_at,source.last_error,source.enabled,
            COUNT(raw.id) FILTER (WHERE (raw.observed_at AT TIME ZONE 'Asia/Shanghai')::date =
                (NOW() AT TIME ZONE 'Asia/Shanghai')::date)::int AS raw_today
            FROM intelligence_sources source LEFT JOIN intelligence_raw_items raw ON raw.source_key=source.source_key AND raw.observed_at >= NOW() - INTERVAL '2 days'
            GROUP BY source.source_key""")
        sources = [dict(row) for row in cursor.fetchall()]
        cursor.execute("""SELECT business_scopes,status,first_seen_at,published_at,id FROM intelligence_events
            WHERE first_seen_at >= NOW() - INTERVAL '2 days' OR published_at >= NOW() - INTERVAL '2 days'
               OR status='pending_review'""")
        events = [dict(row) for row in cursor.fetchall()]
    tasks = list_tasks()
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    domains = []
    for key in sorted(DOMAINS):
        own_sources = [source for source in sources if key in (source["business_scopes"] or [])]
        own_events = [event for event in events if key in (event["business_scopes"] or [])]
        own_tasks = [task for task in tasks if key in task["business_scopes"]]
        published = [event for event in own_events if event["status"] == "active" and event["published_at"]
                     and event["published_at"].astimezone(ZoneInfo("Asia/Shanghai")).date() == today]
        raw_count = sum(source["raw_today"] or 0 for source in own_sources)
        domains.append({
            "key": key,
            "raw_today": raw_count,
            "events_today": sum(event["first_seen_at"].astimezone(ZoneInfo("Asia/Shanghai")).date() == today for event in own_events),
            "published_today": len(published),
            "pending_review": sum(event["status"] == "pending_review" for event in own_events),
            "source_count": len(own_sources),
            "source_errors": sum(source["enabled"] and (source["health_status"] == "failed" or bool(source["last_error"])) for source in own_sources),
            "failed_tasks": sum(bool(task["last_run"]) and task["last_run"]["status"] == "failed" for task in own_tasks),
            "last_source_update": max((source["last_success_at"] for source in own_sources if source["last_success_at"]), default=None),
            "publication_status": "published_today" if published else "no_publication_today",
            "last_published_id": max(published, key=lambda event: event["published_at"])["id"] if published else None,
        })
    return {"domains": domains, "raw_today": sum(source["raw_today"] or 0 for source in sources),
            "events_today": sum(event["first_seen_at"].astimezone(ZoneInfo("Asia/Shanghai")).date() == today for event in events),
            "published_today": sum(event["status"] == "active" and event["published_at"] is not None
                                   and event["published_at"].astimezone(ZoneInfo("Asia/Shanghai")).date() == today
                                   for event in events),
            "pending_review": sum(event["status"] == "pending_review" for event in events),
            "failed_tasks": sum(bool(task["last_run"]) and task["last_run"]["status"] == "failed" for task in tasks)}
