"""AI usage tracking — token counts per model/feature."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from db import get_db

logger = logging.getLogger(__name__)


def _token_counts(usage: dict | None) -> tuple[int, int]:
    usage = usage or {}
    return (
        int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
        int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
    )


def record(user_id: str | None, model: str, feature: str, usage: dict | None = None) -> None:
    try:
        input_tokens, output_tokens = _token_counts(usage)
        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO ai_usage_records (user_id, model, feature, input_tokens, output_tokens, usage_reported, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (user_id, model[:100], feature[:80], input_tokens, output_tokens, _has_usage(usage), datetime.now(timezone.utc)),
            )
    except Exception as e:
        logger.debug("AI usage record failed: %s", e)


def start(user_id: str, model: str, feature: str) -> int | None:
    """Create the request row before streaming so cancelled calls are counted."""
    if not user_id:
        return None
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ai_usage_records (user_id, model, feature, created_at) VALUES (%s,%s,%s,%s) RETURNING id",
                (user_id, model[:100], feature[:80], datetime.now(timezone.utc)),
            )
            row = cursor.fetchone()
            return int(row["id"] if isinstance(row, dict) else row[0])
    except Exception as e:
        logger.debug("AI usage start record failed: %s", e)
        return None


def finish(record_id: int | None, usage: dict | None = None) -> None:
    if not record_id:
        return
    try:
        input_tokens, output_tokens = _token_counts(usage)
        with get_db() as conn:
            conn.cursor().execute(
                "UPDATE ai_usage_records SET input_tokens=%s, output_tokens=%s, usage_reported=%s WHERE id=%s",
                (input_tokens, output_tokens, _has_usage(usage), record_id),
            )
    except Exception as e:
        logger.debug("AI usage finish record failed: %s", e)


def summary() -> dict:
    today_start = datetime.now(ZoneInfo("Asia/Shanghai")).replace(hour=0, minute=0, second=0, microsecond=0)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS requests, COALESCE(SUM(input_tokens),0) AS input_tokens, COALESCE(SUM(output_tokens),0) AS output_tokens, COUNT(*) FILTER (WHERE usage_reported) AS token_requests FROM ai_usage_records WHERE created_at >= %s",
            (today_start,),
        )
        today = dict(cursor.fetchone())
        cursor.execute(
            "SELECT model, COUNT(*) AS requests, COALESCE(SUM(input_tokens),0) AS input_tokens, COALESCE(SUM(output_tokens),0) AS output_tokens, COUNT(*) FILTER (WHERE usage_reported) AS token_requests FROM ai_usage_records WHERE created_at >= %s GROUP BY model ORDER BY requests DESC",
            (today_start - timedelta(days=6),),
        )
        return {"today": today, "models": [dict(row) for row in cursor.fetchall()]}


def _has_usage(usage: dict | None) -> bool:
    return isinstance(usage, dict) and any(usage.get(key) is not None for key in ("prompt_tokens", "completion_tokens", "input_tokens", "output_tokens"))
