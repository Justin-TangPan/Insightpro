"""Single registry and execution path for scheduled platform tasks."""
from __future__ import annotations

import importlib
import json
import logging
import zlib
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from apscheduler.triggers.cron import CronTrigger
from pytz import timezone as tz

from db import get_db

logger = logging.getLogger(__name__)
SHANGHAI = tz("Asia/Shanghai")


@dataclass(frozen=True)
class TaskDefinition:
    key: str
    name: str
    schedule: str
    cron: dict
    target: str
    uses_ai: bool = False
    record_empty: bool = True
    source_task: bool = False


TASKS = (
    TaskDefinition("github_daily", "GitHub 趋势采集", "每天 08:30", {"hour": 8, "minute": 30}, "crawlers.github_crawler:refresh_and_store", source_task=True),
    TaskDefinition("baidu_hotsearch_daily", "百度热搜采集", "每天 08:50", {"hour": 8, "minute": 50}, "services.startup_service:refresh_baidu_hotsearch_if_missing", source_task=True),
    TaskDefinition("solution_catalogs_daily", "云厂商方案采集", "每天 09:00", {"hour": 9, "minute": 0}, "services.aliyun_solution_service:refresh_solution_catalogs", source_task=True),
    TaskDefinition("daily_crawl", "行业与厂商动态采集", "每天 09:00", {"hour": 9, "minute": 0}, "crawlers:run_daily_crawl", source_task=True),
    TaskDefinition("competitor_daily", "友商动态采集", "每天 09:02", {"hour": 9, "minute": 2}, "services.competitor_news_service:refresh_competitor_news", source_task=True),
    TaskDefinition("ai_applications_daily", "AI 应用官方动态采集", "每天 09:30", {"hour": 9, "minute": 30}, "services.agent_launch_service:refresh_official_sources", source_task=True),
    TaskDefinition("discovery_sentinel_daily", "Discovery Sentinel 候选发现", "每天 09:45", {"hour": 9, "minute": 45}, "services.discovery_service:discover_candidates", source_task=True),
    TaskDefinition("trending_business_eval_daily", "项目业务价值评估", "每天 08:35", {"hour": 8, "minute": 35}, "services.evaluation_service:evaluate_trending_business", True),
    TaskDefinition("knowledge_sync_daily", "公共知识同步", "每天 09:05", {"hour": 9, "minute": 5}, "services.knowledge_service:sync_public_knowledge", True),
    TaskDefinition("project_briefs_zh_daily", "项目中文速读", "每天 08:55", {"hour": 8, "minute": 55}, "services.evaluation_service:translate_project_summaries", True),
    TaskDefinition("board_insights_daily", "板块近期情报", "每天 10:00", {"hour": 10, "minute": 0}, "services.daily_board_insight_service:refresh_all", True),
    TaskDefinition("radar_event_analysis_daily", "Radar 事件分析", "每天 10:15", {"hour": 10, "minute": 15}, "services.radar_service:analyze_radar_events", True),
    TaskDefinition("cleanup", "历史数据清理", "每天 03:00", {"hour": 3, "minute": 0}, "services.maintenance_service:cleanup_old_data"),
    TaskDefinition("scheduled_email", "订阅邮件发送", "每分钟检查", {"minute": "*", "second": 0}, "services.email_service:send_scheduled_digests", record_empty=False),
)
TASK_BY_KEY = {task.key: task for task in TASKS}
SOURCE_TASK_KEYS = tuple(task.key for task in TASKS if task.source_task)
SOURCE_TASK_BY_ADAPTER = {
    "github_trending": "github_daily",
    "aliyun_solutions": "solution_catalogs_daily",
    "huawei_solutions": "solution_catalogs_daily",
    "competitor_news": "competitor_daily",
    "ai_applications_official": "ai_applications_daily",
    "product_hunt_feed": "discovery_sentinel_daily",
    "hacker_news_api": "discovery_sentinel_daily",
    "hugging_face_api": "discovery_sentinel_daily",
    "arxiv_api": "discovery_sentinel_daily",
    "github_search_api": "discovery_sentinel_daily",
    "rss_feed": "discovery_sentinel_daily",
}
COMMUNITY_ADAPTERS = {"community_zhihu", "community_baidu", "community_tencent", "community_csdn"}


def source_task_key(source: dict) -> str | None:
    if source.get("adapter") in COMMUNITY_ADAPTERS:
        return None
    configured = (source.get("schedule") or {}).get("task_key")
    if configured in TASK_BY_KEY and TASK_BY_KEY[configured].source_task:
        return configured
    return SOURCE_TASK_BY_ADAPTER.get(source.get("adapter"))


def required_source_tasks() -> tuple[str, ...]:
    from services.source_registry_service import list_sources
    registered = {source_task_key(source) for source in list_sources() if source.get("enabled")}
    # These two legacy collectors feed business data that has no V2 source row.
    required = {"daily_crawl", "competitor_daily"} | (registered - {None})
    return tuple(key for key in SOURCE_TASK_KEYS if key in required)
_RUNTIME_CRONS: dict[str, str] = {}


def load_source_schedules() -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT source_key,adapter,schedule,enabled FROM intelligence_sources")
        rows = cursor.fetchall()
    grouped: dict[str, set[str]] = {}
    for row in rows:
        source = dict(row)
        key = source_task_key(source)
        cron = (source.get("schedule") or {}).get("cron")
        if key and source.get("enabled") and cron:
            grouped.setdefault(key, set()).add(cron)
    _RUNTIME_CRONS.clear()
    for key, expressions in grouped.items():
        if len(expressions) != 1:
            logger.warning("Ignoring conflicting Source schedules for %s", key)
            continue
        expression = next(iter(expressions))
        try:
            CronTrigger.from_crontab(expression, timezone=SHANGHAI)
        except ValueError:
            logger.warning("Ignoring invalid Source schedule for %s: %s", key, expression)
            continue
        _RUNTIME_CRONS[key] = expression


def set_task_schedule(task_key: str, expression: str) -> None:
    if task_key not in TASK_BY_KEY:
        raise KeyError(task_key)
    CronTrigger.from_crontab(expression, timezone=SHANGHAI)
    _RUNTIME_CRONS[task_key] = expression


def _resolve(target: str) -> Callable:
    module_name, function_name = target.split(":", 1)
    return getattr(importlib.import_module(module_name), function_name)


def recover_orphaned_runs() -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT task_key FROM platform_task_runs WHERE status='running'")
        task_keys = [row["task_key"] for row in cursor.fetchall()]

    recovered = 0
    for key in task_keys:
        lock_id = zlib.crc32(key.encode())
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pg_try_advisory_lock(%s) AS acquired", (lock_id,))
            if not cursor.fetchone()["acquired"]:
                continue
            try:
                cursor.execute(
                    """UPDATE platform_task_runs
                       SET status='failed', finished_at=NOW(),
                           error=COALESCE(error, 'Task process exited without recording completion')
                       WHERE task_key=%s AND status='running'""",
                    (key,),
                )
                recovered += cursor.rowcount
            finally:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (lock_id,))
    if recovered:
        logger.warning("Marked %s orphaned task runs as failed", recovered)
    return recovered


def run_task(key: str, trigger: str = "scheduled", function: Callable | None = None):
    task = TASK_BY_KEY[key]
    lock_id = zlib.crc32(key.encode())
    with get_db() as lock_conn:
        lock_cursor = lock_conn.cursor()
        lock_cursor.execute("SELECT pg_try_advisory_lock(%s) AS acquired", (lock_id,))
        if not lock_cursor.fetchone()["acquired"]:
            return {"status": "skipped", "reason": "already_running"}
        run_id = None
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO platform_task_runs (task_key, trigger, status, started_at) VALUES (%s,%s,'running',NOW()) RETURNING id",
                    (key, trigger),
                )
                run_id = cursor.fetchone()["id"]
            try:
                result = (function or _resolve(task.target))()
                payload = result if isinstance(result, dict) else {"result": result}
                task_failed = payload.get("status") in {"partial", "partial_success", "failed"}
                error = payload.get("error") or (json.dumps(payload.get("source_errors"), ensure_ascii=False)
                                                   if payload.get("source_errors") else
                                                   f"Task returned {payload.get('status')}" if task_failed else None)
                if not task.record_empty and not payload.get("total"):
                    with get_db() as conn:
                        conn.cursor().execute("DELETE FROM platform_task_runs WHERE id=%s", (run_id,))
                else:
                    with get_db() as conn:
                        conn.cursor().execute(
                            "UPDATE platform_task_runs SET status=%s, finished_at=NOW(), result=%s::jsonb, error=%s WHERE id=%s",
                            ("failed" if task_failed else "success", json.dumps(payload, ensure_ascii=False, default=str),
                             str(error)[:1000] if error else None, run_id),
                        )
                return result
            except Exception as exc:
                with get_db() as conn:
                    conn.cursor().execute(
                        "UPDATE platform_task_runs SET status='failed', finished_at=NOW(), error=%s WHERE id=%s",
                        (str(exc)[:1000], run_id),
                    )
                logger.exception("Task %s failed", key)
                raise
        finally:
            lock_cursor.execute("SELECT pg_advisory_unlock(%s)", (lock_id,))


def task_trigger(task: TaskDefinition) -> CronTrigger:
    expression = _RUNTIME_CRONS.get(task.key)
    return CronTrigger.from_crontab(expression, timezone=SHANGHAI) if expression else CronTrigger(timezone=SHANGHAI, **task.cron)


def list_tasks() -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT DISTINCT ON (task_key) task_key, status, trigger, started_at, finished_at, error
                          FROM platform_task_runs ORDER BY task_key, started_at DESC""")
        latest = {row["task_key"]: dict(row) for row in cursor.fetchall()}
    now = datetime.now(SHANGHAI)
    return [{
        "key": task.key, "name": task.name, "schedule": _RUNTIME_CRONS.get(task.key, task.schedule), "uses_ai": task.uses_ai,
        "next_run_at": task_trigger(task).get_next_fire_time(None, now), "last_run": latest.get(task.key),
    } for task in TASKS]


def recent_runs(limit: int = 50) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT id, task_key, trigger, status, started_at, finished_at, result, error
                          FROM platform_task_runs ORDER BY started_at DESC LIMIT %s""", (limit,))
        return [dict(row) for row in cursor.fetchall()]
