"""Repository trend reads from canonical Events, with a V1 read fallback."""
from __future__ import annotations

from zoneinfo import ZoneInfo

from db import get_db


def list_trending_repositories(period: str = "daily", date: str | None = None) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            WITH target AS (
                SELECT COALESCE(%s::date, MAX((observed_at AT TIME ZONE 'Asia/Shanghai')::date)) AS date
                FROM intelligence_raw_items
                WHERE source_key='github_trending' AND content->>'category'=%s
            ), latest AS (
                SELECT DISTINCT ON (entity.entity_key)
                       entity.entity_key,entity.canonical_name AS repo_name,entity.canonical_url AS repo_url,
                       entity.metadata->>'language' AS language,raw.content,raw.observed_at,event.id AS event_id,event.scores,
                       discovery.content AS discovery_content,metadata.content AS metadata_content
                FROM target
                JOIN intelligence_raw_items raw ON raw.source_key='github_trending'
                    AND raw.content->>'category'=%s
                    AND (raw.observed_at AT TIME ZONE 'Asia/Shanghai')::date=target.date
                JOIN intelligence_entities entity ON entity.entity_type='repository'
                    AND entity.canonical_url=raw.canonical_url
                JOIN intelligence_event_evidence evidence ON evidence.raw_item_id=raw.id
                JOIN intelligence_events event ON event.id=evidence.event_id AND event.status='active'
                    AND event.entity_key=entity.entity_key
                LEFT JOIN LATERAL (
                    SELECT candidate.content FROM intelligence_raw_items candidate
                    WHERE candidate.source_key='github_search' AND candidate.canonical_url=raw.canonical_url
                    ORDER BY candidate.observed_at DESC,candidate.id DESC LIMIT 1
                ) discovery ON TRUE
                LEFT JOIN LATERAL (
                    SELECT candidate.content FROM intelligence_raw_items candidate
                    WHERE candidate.source_key='github_trending' AND candidate.canonical_url=raw.canonical_url
                      AND candidate.content->>'kind'='repository_metadata'
                    ORDER BY candidate.observed_at DESC,candidate.id DESC LIMIT 1
                ) metadata ON TRUE
                ORDER BY entity.entity_key,raw.observed_at DESC,raw.id DESC,event.id DESC
            )
            SELECT * FROM latest ORDER BY COALESCE((content->>'rank')::int,2147483647),repo_name LIMIT 25
        """, (date, period, period))
        rows = [dict(row) for row in cursor.fetchall()]
        if rows:
            items = [{
                "repo_name": row["repo_name"], "repo_url": row["repo_url"],
                "description": row["content"].get("description") or "", "language": row["language"] or "N/A",
                "stars": str(row["content"].get("stars") or "0"), "forks": str(row["content"].get("forks") or "0"),
                "today_stars": str(row["content"].get("today_stars") or ""), "category": period,
                "entity_key": row["entity_key"], "event_id": row["event_id"],
                "scores": row.get("scores") or {},
                "pushed_at": (row.get("metadata_content") or {}).get("pushed_at") or
                             (row.get("discovery_content") or {}).get("pushed_at"),
                "topics": (row.get("metadata_content") or {}).get("topics") or
                          (row.get("discovery_content") or {}).get("topics") or [],
                "contributors_count": (row.get("metadata_content") or {}).get("contributors_count"),
                "latest_release": (row.get("metadata_content") or {}).get("latest_release"),
                "license": (row.get("metadata_content") or {}).get("license"),
                "repository_metadata_available": row.get("metadata_content") is not None,
            } for row in rows]
            snapshot_date = rows[0]["observed_at"].astimezone(ZoneInfo("Asia/Shanghai")).date().isoformat()
            return {"items": items, "source": "event_store", "count": len(items), "date": snapshot_date}

        cursor.execute("""
            SELECT DISTINCT ON (repo_name) repo_name,repo_url,description,language,stars,forks,today_stars,category,scrape_date
            FROM github_trending WHERE category=%s AND (%s::date IS NULL OR scrape_date=%s::date)
            ORDER BY repo_name,scrape_date DESC,scrape_time DESC,id DESC LIMIT 25
        """, (period, date, date))
        legacy = [dict(row) for row in cursor.fetchall()]
    return {"items": legacy, "source": "v1_compatibility" if legacy else "empty", "count": len(legacy),
            "date": legacy[0]["scrape_date"].isoformat() if legacy else date}
