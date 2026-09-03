from datetime import datetime, timezone

from db import get_db


def record(user_id: str, model: str, feature: str, usage: dict | None = None) -> None:
    usage = usage or {}
    try:
        with get_db() as conn:
            conn.cursor().execute("INSERT INTO ai_usage_records (user_id, model, feature, input_tokens, output_tokens, created_at) VALUES (%s,%s,%s,%s,%s,%s)", (user_id, model[:100], feature[:80], int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0), datetime.now(timezone.utc)))
    except Exception:
        pass


def summary() -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS requests, COALESCE(SUM(input_tokens),0) AS input_tokens, COALESCE(SUM(output_tokens),0) AS output_tokens FROM ai_usage_records WHERE created_at >= CURRENT_DATE")
        today = dict(cursor.fetchone())
        cursor.execute("SELECT model, COUNT(*) AS requests, COALESCE(SUM(input_tokens),0) AS input_tokens, COALESCE(SUM(output_tokens),0) AS output_tokens FROM ai_usage_records WHERE created_at >= CURRENT_DATE - INTERVAL '6 days' GROUP BY model ORDER BY requests DESC")
        return {"today": today, "models": [dict(row) for row in cursor.fetchall()]}
