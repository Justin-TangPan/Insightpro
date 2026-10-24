"""Calculate observed changes from historical metric snapshots."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

WINDOWS = {"1h": 1, "6h": 6, "24h": 24, "7d": 168, "30d": 720}


def _changes(latest: dict, baseline: dict, hours: int, as_of: datetime) -> dict:
    result = {"as_of": as_of, "metrics": {}}
    for key, current in latest.items():
        previous = baseline.get(key)
        if not previous or current["observed_at"] < as_of - timedelta(hours=hours):
            continue
        current_value, baseline_value = Decimal(current["metric_value"]), Decimal(previous["metric_value"])
        delta = baseline_value - current_value if key.startswith("rank_") else current_value - baseline_value
        result["metrics"][key] = {
            "current": current_value, "baseline": baseline_value,
            "baseline_at": previous["observed_at"], "delta": delta,
        }
    metrics = result["metrics"]
    result.update({
        "stars_delta": metrics.get("stars", {}).get("delta"),
        "stars_velocity": metrics["stars"]["delta"] / hours if "stars" in metrics else None,
        "mention_growth": metrics.get("mentions", {}).get("delta"),
        "comment_growth": metrics.get("comments", {}).get("delta"),
        "ranking_change": metrics.get("rank_daily", {}).get("delta"),
        "download_growth": metrics.get("downloads", {}).get("delta"),
    })
    return result


def trends_for_entity(cursor, entity_key: str, as_of: datetime | None = None) -> dict:
    as_of = as_of or datetime.now(timezone.utc)
    cursor.execute("""
        SELECT DISTINCT ON (metric_key) metric_key, metric_value, observed_at
        FROM intelligence_metric_snapshots WHERE entity_key=%s AND observed_at<=%s
        ORDER BY metric_key, observed_at DESC, id DESC
    """, (entity_key, as_of))
    latest = {row["metric_key"]: dict(row) for row in cursor.fetchall()}
    observed_at = max((row["observed_at"] for row in latest.values()), default=None)
    windows = {}
    for name, hours in WINDOWS.items():
        if not observed_at:
            windows[name] = _changes({}, {}, hours, as_of)
            continue
        cutoff = observed_at - timedelta(hours=hours)
        cursor.execute("""
            SELECT DISTINCT ON (metric_key) metric_key, metric_value, observed_at
            FROM intelligence_metric_snapshots
            WHERE entity_key=%s AND observed_at BETWEEN %s AND %s
            ORDER BY metric_key, observed_at DESC, id DESC
        """, (entity_key, cutoff - timedelta(hours=hours), cutoff))
        baseline = {row["metric_key"]: dict(row) for row in cursor.fetchall()}
        windows[name] = _changes(latest, baseline, hours, observed_at)
    return {"as_of": observed_at, "stale": observed_at is None or observed_at < as_of - timedelta(hours=24), "windows": windows}
