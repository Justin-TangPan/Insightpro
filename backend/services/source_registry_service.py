"""Read and operate the database-backed source registry."""
from __future__ import annotations

import json
import re
from urllib.parse import urlparse
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

from db import get_db

SHANGHAI = timezone("Asia/Shanghai")
SHANGHAI_ZONE = ZoneInfo("Asia/Shanghai")
DISCOVERY_ADAPTERS = {"product_hunt_feed", "hacker_news_api", "hugging_face_api", "arxiv_api", "github_search_api", "rss_feed"}
BUSINESS_SCOPES = {"technology_ecosystem", "ai_applications", "solutions", "community_insights", "competitor_dynamics"}


def source_enabled(source_key: str) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT enabled FROM intelligence_sources WHERE source_key=%s", (source_key,))
        row = cursor.fetchone()
    return bool(row and row["enabled"])


def enabled_sources(source_keys: tuple[str, ...]) -> set[str]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT source_key FROM intelligence_sources WHERE source_key=ANY(%s) AND enabled", (list(source_keys),))
        return {row["source_key"] for row in cursor.fetchall()}


def list_sources() -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT source_key, name, adapter, base_url, business_scopes, authority,
                          priority, schedule, enabled, health_status, last_success_at, last_error, updated_at
                          FROM intelligence_sources ORDER BY priority, source_key""")
        return [dict(row) for row in cursor.fetchall()]


def create_source(source: dict, actor_user_id: str) -> dict:
    key, name, adapter = source["source_key"].strip(), source["name"].strip(), source["adapter"]
    url, scopes = source["base_url"].strip(), source["business_scopes"]
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,63}", key) or not name:
        raise ValueError("Source key or name is invalid")
    if adapter not in DISCOVERY_ADAPTERS:
        raise ValueError("Adapter is not supported by Discovery Sentinel")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Source URL must be an HTTPS URL without credentials")
    if not scopes or set(scopes) - BUSINESS_SCOPES:
        raise ValueError("Invalid business scopes")
    if source["authority"] not in {"P0", "P1", "P2"} or type(source["priority"]) is not int or not 0 <= source["priority"] <= 1000:
        raise ValueError("Invalid source authority or priority")
    cron = source["cron"]
    CronTrigger.from_crontab(cron, timezone=SHANGHAI)
    schedule = {"task_key": "discovery_sentinel_daily", "cron": cron, "timezone": "Asia/Shanghai"}
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO intelligence_sources
            (source_key,name,adapter,base_url,business_scopes,authority,priority,schedule,enabled)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,FALSE)
            ON CONFLICT (source_key) DO NOTHING RETURNING *""",
            (key, name, adapter, url, scopes, source["authority"], source["priority"], json.dumps(schedule)))
        created = cursor.fetchone()
        if not created:
            raise ValueError("Source key already exists")
        cursor.execute("""INSERT INTO intelligence_audit
            (actor_user_id,action,object_type,object_key,after_state)
            VALUES (%s::uuid,'source_created','source',%s,%s::jsonb)""",
            (actor_user_id, key, json.dumps({**dict(created), "schedule": schedule}, ensure_ascii=False, default=str)))
        cursor.execute("""SELECT source_key,schedule FROM intelligence_sources
                          WHERE schedule->>'task_key'=%s FOR UPDATE""", ("discovery_sentinel_daily",))
        for related in cursor.fetchall():
            previous_schedule = related["schedule"] or {}
            if previous_schedule.get("cron") == cron:
                continue
            updated_schedule = {**previous_schedule, "cron": cron}
            cursor.execute("""UPDATE intelligence_sources SET
                schedule=jsonb_set(schedule,'{cron}',to_jsonb(%s::text),TRUE),updated_at=NOW()
                WHERE source_key=%s""", (cron, related["source_key"]))
            cursor.execute("""INSERT INTO intelligence_audit
                (actor_user_id,action,object_type,object_key,before_state,after_state)
                VALUES (%s::uuid,'source_schedule_changed','source',%s,%s::jsonb,%s::jsonb)""",
                (actor_user_id, related["source_key"], json.dumps({"schedule": previous_schedule}),
                 json.dumps({"schedule": updated_schedule})))
        result = dict(created)
    return result


def set_source_enabled(source_key: str, enabled: bool, actor_user_id: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT enabled FROM intelligence_sources WHERE source_key=%s FOR UPDATE", (source_key,))
        previous = cursor.fetchone()
        if not previous:
            return None
        cursor.execute("""UPDATE intelligence_sources SET enabled=%s, updated_at=NOW()
                          WHERE source_key=%s RETURNING source_key, enabled, updated_at""", (enabled, source_key))
        row = cursor.fetchone()
        if previous["enabled"] != enabled:
            cursor.execute("""INSERT INTO intelligence_audit
                (actor_user_id, action, object_type, object_key, before_state, after_state)
                VALUES (%s::uuid, 'source_enabled_changed', 'source', %s, %s::jsonb, %s::jsonb)""",
                (actor_user_id, source_key, json.dumps({"enabled": previous["enabled"]}), json.dumps({"enabled": enabled})))
        return dict(row) if row else None


def update_source(source_key: str, changes: dict, actor_user_id: str) -> dict | None:
    allowed_scopes = {"technology_ecosystem", "ai_applications", "solutions", "community_insights", "competitor_dynamics"}
    if not changes or set(changes) - {"name", "base_url", "priority", "authority", "business_scopes"}:
        raise ValueError("No supported source fields supplied")
    if "name" in changes and (not isinstance(changes["name"], str) or not changes["name"].strip()):
        raise ValueError("Source name cannot be empty")
    if "base_url" in changes:
        parsed = urlparse(changes["base_url"] or "")
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Source URL must be an HTTPS URL without credentials")
    if "priority" in changes and (type(changes["priority"]) is not int or not 0 <= changes["priority"] <= 1000):
        raise ValueError("Priority must be between 0 and 1000")
    if "authority" in changes and changes["authority"] not in {"P0", "P1", "P2"}:
        raise ValueError("Authority must be P0, P1 or P2")
    if "business_scopes" in changes and (not changes["business_scopes"] or set(changes["business_scopes"]) - allowed_scopes):
        raise ValueError("Invalid business scopes")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name,base_url,priority,authority,business_scopes FROM intelligence_sources WHERE source_key=%s FOR UPDATE", (source_key,))
        previous = cursor.fetchone()
        if not previous:
            return None
        fields, values = [], []
        for key, value in changes.items():
            fields.append(f"{key}=%s")
            values.append(value)
        cursor.execute(f"UPDATE intelligence_sources SET {', '.join(fields)},updated_at=NOW() WHERE source_key=%s RETURNING *",
                       (*values, source_key))
        updated = dict(cursor.fetchone())
        cursor.execute("""INSERT INTO intelligence_audit
            (actor_user_id,action,object_type,object_key,before_state,after_state)
            VALUES (%s::uuid,'source_updated','source',%s,%s::jsonb,%s::jsonb)""",
            (actor_user_id, source_key, json.dumps({key: previous[key] for key in changes}, ensure_ascii=False),
             json.dumps({key: updated[key] for key in changes}, ensure_ascii=False)))
        return updated


def update_source_schedule(source_key: str, cron: str, actor_user_id: str) -> dict | None:
    CronTrigger.from_crontab(cron, timezone=SHANGHAI)
    from services.task_service import source_task_key
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT source_key,adapter,schedule FROM intelligence_sources WHERE source_key=%s FOR UPDATE", (source_key,))
        source = cursor.fetchone()
        if not source:
            return None
        source = dict(source)
        schedule = source["schedule"] or {}
        task_key = source_task_key(source)
        if not task_key:
            raise ValueError("Request-cache sources do not have a scheduled collector")
        cursor.execute("SELECT source_key,adapter,schedule FROM intelligence_sources FOR UPDATE")
        related = [dict(row) for row in cursor.fetchall() if source_task_key(dict(row)) == task_key]
        if not related:
            raise ValueError("No sources are registered for this collector task")
        for item in related:
            previous = item["schedule"] or {}
            if previous.get("cron") == cron and previous.get("task_key") == task_key:
                continue
            updated = {**previous, "task_key": task_key, "cron": cron, "timezone": "Asia/Shanghai"}
            cursor.execute("UPDATE intelligence_sources SET schedule=%s::jsonb,updated_at=NOW() WHERE source_key=%s",
                           (json.dumps(updated), item["source_key"]))
            cursor.execute("""INSERT INTO intelligence_audit
                (actor_user_id,action,object_type,object_key,before_state,after_state)
                VALUES (%s::uuid,'source_schedule_changed','source',%s,%s::jsonb,%s::jsonb)""",
                (actor_user_id, item["source_key"], json.dumps({"schedule": previous}),
                 json.dumps({"schedule": updated})))
    return {"task_key": task_key, "cron": cron, "source_keys": [item["source_key"] for item in related]}


def test_source_connection(source_key: str, actor_user_id: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name,adapter,base_url FROM intelligence_sources WHERE source_key=%s", (source_key,))
        source = cursor.fetchone()
    if not source:
        return None
    status_code, error = None, None
    if not source["base_url"]:
        error = "Source URL is not configured"
    else:
        try:
            response = requests.get(source["base_url"], timeout=8, allow_redirects=False, stream=True,
                                   headers={"User-Agent": "InsightPro Source Check/1.0"})
            status_code = response.status_code
            response.close()
            if 300 <= status_code < 400:
                error = "Source returned a redirect"
            elif status_code >= 400:
                error = f"Source returned HTTP {status_code}"
        except requests.RequestException as exc:
            error = str(exc)[:500]
    result = {"source_key": source_key, "name": source["name"], "adapter": source["adapter"],
              "ok": error is None, "status_code": status_code, "error": error,
              "checked_at": datetime.now(SHANGHAI_ZONE).isoformat(timespec="seconds")}
    with get_db() as conn:
        conn.cursor().execute("""INSERT INTO intelligence_audit
            (actor_user_id,action,object_type,object_key,after_state)
            VALUES (%s::uuid,'source_connection_tested','source',%s,%s::jsonb)""",
            (actor_user_id, source_key, json.dumps(result, ensure_ascii=False)))
    return result


def record_source_health(source_key: str, status: str, error: str | None = None) -> None:
    with get_db() as conn:
        conn.cursor().execute("""UPDATE intelligence_sources SET health_status=%s,
            last_success_at=CASE WHEN %s THEN NOW() ELSE last_success_at END,
            last_error=%s, updated_at=NOW() WHERE source_key=%s""",
            (status, status != "failed", error[:1000] if error else None, source_key))
