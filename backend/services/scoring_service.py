"""Deterministic hot score from observed GitHub growth."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone

from services.metric_service import trends_for_entity


def github_hot_score(stars: float | None, stars_delta: float | None, rank_change: float | None = None) -> dict | None:
    if stars is None or stars_delta is None or stars < 0 or stars_delta > stars:
        return None
    growth = max(0, stars_delta)
    baseline = max(1, stars - growth)
    relative_growth = growth / baseline
    score = min(100, round(min(50, relative_growth * 10) + min(40, growth * 0.04)
                           + min(10, max(0, rank_change or 0) * 2), 1))
    return {"value": score, "version": "github_hot_v1", "stars_delta": stars_delta,
            "relative_growth": round(relative_growth, 4), "ranking_change": rank_change}


def persist_github_hot_score(cursor, entity_key: str, event_id: int) -> dict | None:
    cursor.execute("""SELECT metric_value, observed_at FROM intelligence_metric_snapshots
        WHERE entity_key=%s AND metric_key='stars' ORDER BY observed_at DESC, id DESC LIMIT 1""", (entity_key,))
    latest = cursor.fetchone()
    if not latest:
        return None
    cursor.execute("""SELECT metric_value FROM intelligence_metric_snapshots
        WHERE entity_key=%s AND metric_key='stars'
          AND observed_at BETWEEN %s - INTERVAL '48 hours' AND %s - INTERVAL '24 hours'
        ORDER BY observed_at DESC, id DESC LIMIT 1""",
        (entity_key, latest["observed_at"], latest["observed_at"]))
    baseline = cursor.fetchone()
    if baseline:
        delta = float(latest["metric_value"] - baseline["metric_value"])
        basis = "snapshot_24h"
    else:
        cursor.execute("""SELECT metric_value FROM intelligence_metric_snapshots
            WHERE entity_key=%s AND metric_key='trending_growth_daily' AND observed_at=%s
            ORDER BY id DESC LIMIT 1""", (entity_key, latest["observed_at"]))
        reported = cursor.fetchone()
        delta = float(reported["metric_value"]) if reported else None
        basis = "github_reported_day"
    score = github_hot_score(float(latest["metric_value"]), delta)
    if score:
        score["basis"] = basis
        cursor.execute("""UPDATE intelligence_events SET scores=jsonb_set(scores, '{hot_score}', %s::jsonb, TRUE),
            updated_at=NOW() WHERE id=%s""", (json.dumps(score), event_id))
    else:
        cursor.execute("UPDATE intelligence_events SET scores=scores-'hot_score', updated_at=NOW() WHERE id=%s", (event_id,))
    return score


def signal_hot_score(metrics: dict, source_count: int, evidence_count: int, authorities: list[str],
                     last_seen_at: datetime, now: datetime | None = None) -> dict:
    """Score observed momentum and evidence quality without using absolute popularity as heat."""
    now = now or datetime.now(timezone.utc)
    changes = metrics.get("24h", {}).get("metrics", {})
    momentum, basis = 0.0, None
    for key, observation in changes.items():
        delta = float(observation["delta"])
        if delta <= 0:
            continue
        baseline = abs(float(observation["baseline"]))
        relative = min(35.0, delta / max(1.0, baseline) * 35.0)
        volume = min(15.0, math.log1p(delta) * 2.0)
        value = min(50.0, relative + volume)
        if value > momentum:
            momentum, basis = value, key
    corroboration = min(25.0, max(0, source_count - 1) * 12.0 + max(0, evidence_count - source_count) * 3.0)
    authority = max(({"P0": 15.0, "P1": 10.0, "P2": 5.0}.get(level, 0.0) for level in authorities), default=0.0)
    age_hours = max(0.0, (now - last_seen_at).total_seconds() / 3600)
    freshness = max(0.0, 20.0 - age_hours / 3.0)
    return {"value": round(min(100.0, momentum + corroboration + authority + freshness), 1),
            "version": "signal_hot_v1", "momentum": round(momentum, 1), "momentum_basis": basis,
            "corroboration": round(corroboration, 1), "authority": authority,
            "freshness": round(freshness, 1), "source_count": source_count, "evidence_count": evidence_count}


def persist_signal_hot_score(cursor, entity_key: str | None, event_id: int, last_seen_at: datetime) -> dict:
    cursor.execute("""SELECT COUNT(DISTINCT raw.source_key)::int AS source_count,
                      COUNT(DISTINCT raw.id)::int AS evidence_count,
                      ARRAY_AGG(DISTINCT source.authority) AS authorities
                      FROM intelligence_event_evidence evidence
                      JOIN intelligence_raw_items raw ON raw.id=evidence.raw_item_id
                      JOIN intelligence_sources source ON source.source_key=raw.source_key
                      WHERE evidence.event_id=%s""", (event_id,))
    evidence = cursor.fetchone()
    trend = trends_for_entity(cursor, entity_key) if entity_key else {"windows": {}}
    score = signal_hot_score(trend.get("windows", {}), evidence["source_count"], evidence["evidence_count"],
                             evidence["authorities"] or [], last_seen_at)
    cursor.execute("""UPDATE intelligence_events SET scores=jsonb_set(scores,'{hot_score}',%s::jsonb,TRUE),
                      updated_at=NOW() WHERE id=%s""", (json.dumps(score), event_id))
    return score


def persist_event_hot_score(cursor, event_id: int, entity_key: str | None, event_key: str,
                            last_seen_at: datetime) -> dict | None:
    if event_key.startswith("github-trending:"):
        return persist_github_hot_score(cursor, entity_key, event_id)
    return persist_signal_hot_score(cursor, entity_key, event_id, last_seen_at)
