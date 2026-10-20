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


TASKS = (
    TaskDefinition("github_daily", "GitHub 趋势采集", "每天 08:30", {"hour": 8, "minute": 30}, "crawlers.github_crawler:refresh_and_store"),
    TaskDefinition("solution_catalogs_daily", "云厂商方案采集", "每天 09:00", {"hour": 9, "minute": 0}, "services.aliyun_solution_service:refresh_solution_catalogs"),
    TaskDefinition("daily_crawl", "行业与厂商动态采集", "每天 09:00", {"hour": 9, "minute": 0}, "crawlers:run_daily_crawl"),
    TaskDefinition("competitor_daily", "友商动态采集", "每天 09:02", {"hour": 9, "minute": 2}, "services.competitor_news_service:refresh_competitor_news"),
    TaskDefinition("trending_business_eval_daily", "项目业务价值评估", "每天 08:35", {"hour": 8, "minute": 35}, "services.evaluation_service:evaluate_trending_business", True),
    TaskDefinition("knowledge_sync_daily", "公共知识同步", "每天 09:05", {"hour": 9, "minute": 5}, "services.knowledge_service:sync_public_knowledge", True),
    TaskDefinition("project_briefs_zh_daily", "项目中文速读", "每天 08:55", {"hour": 8, "minute": 55}, "services.evaluation_service:translate_project_summaries", True),
    TaskDefinition("cleanup", "历史数据清理", "每天 03:00", {"hour": 3, "minute": 0}, "services.maintenance_service:cleanup_old_data"),
    TaskDefinition("scheduled_email", "订阅邮件发送", "每分钟检查", {"minute": "*", "second": 0}, "services.email_service:send_scheduled_digests", record_empty=False),
)
TASK_BY_KEY = {task.key: task for task in TASKS}


def _resolve(target: str) -> Callable:
    module_name, function_name = target.split(":", 1)
    return getattr(importlib.import_module(module_name), function_name)


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
                if not task.record_empty and not payload.get("total"):
                    with get_db() as conn:
                        conn.cursor().execute("DELETE FROM platform_task_runs WHERE id=%s", (run_id,))
                else:
                    with get_db() as conn:
                        conn.cursor().execute(
                            "UPDATE platform_task_runs SET status='success', finished_at=NOW(), result=%s::jsonb WHERE id=%s",
                            (json.dumps(payload, ensure_ascii=False, default=str), run_id),
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
    return CronTrigger(timezone=SHANGHAI, **task.cron)


def list_tasks() -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT DISTINCT ON (task_key) task_key, status, trigger, started_at, finished_at, error
                          FROM platform_task_runs ORDER BY task_key, started_at DESC""")
        latest = {row["task_key"]: dict(row) for row in cursor.fetchall()}
    now = datetime.now(SHANGHAI)
    return [{
        "key": task.key, "name": task.name, "schedule": task.schedule, "uses_ai": task.uses_ai,
        "next_run_at": task_trigger(task).get_next_fire_time(None, now), "last_run": latest.get(task.key),
    } for task in TASKS]


def recent_runs(limit: int = 50) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT id, task_key, trigger, status, started_at, finished_at, result, error
                          FROM platform_task_runs ORDER BY started_at DESC LIMIT %s""", (limit,))
        return [dict(row) for row in cursor.fetchall()]
