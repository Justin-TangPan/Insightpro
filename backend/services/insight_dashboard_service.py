"""Read-only observed history for the community and competitor dashboards."""
from db import get_db


def history(board: str, days: int = 90) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        if board == "community":
            cursor.execute("""
                WITH evidence AS (
                  SELECT DISTINCT raw.id, source.name,
                    (raw.observed_at AT TIME ZONE 'Asia/Shanghai')::date AS day
                  FROM intelligence_raw_items raw
                  JOIN intelligence_event_evidence link ON link.raw_item_id=raw.id
                  JOIN intelligence_events event ON event.id=link.event_id
                  JOIN intelligence_sources source ON source.source_key=raw.source_key
                  WHERE 'community_insights'=ANY(event.business_scopes)
                    AND raw.observed_at >= NOW() - (%s * INTERVAL '1 day')
                )
                SELECT day, name, COUNT(*)::int AS count FROM evidence
                GROUP BY day, name ORDER BY day, name
            """, (days,))
            metric = "新增采集话题"
        elif board == "competitors":
            cursor.execute("""
                WITH unique_news AS (
                  SELECT vendor AS name,
                    COALESCE(published_date, MIN(scrape_date)::date) AS day
                  FROM competitor_news
                  WHERE vendor <> 'Huawei Cloud'
                  GROUP BY vendor, COALESCE(link,''), title, published_date
                )
                SELECT day, name, COUNT(*)::int AS count FROM unique_news
                WHERE day >= (NOW() AT TIME ZONE 'Asia/Shanghai')::date - %s
                GROUP BY day, name ORDER BY day, name
            """, (days,))
            metric = "官方动态数"
        else:
            raise ValueError("Unknown dashboard")
        rows = [dict(row) for row in cursor.fetchall()]
    totals = {}
    groups = {}
    for row in rows:
        day = row["day"].isoformat()
        totals[day] = totals.get(day, 0) + row["count"]
        groups.setdefault(row["name"], []).append({"date": day, "count": row["count"]})
    return {"metric": metric, "points": [{"date": day, "count": count} for day, count in totals.items()],
            "groups": [{"name": name, "points": points} for name, points in groups.items()]}
