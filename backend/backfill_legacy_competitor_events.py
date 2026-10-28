"""Explicit, atomic import of competitor notices already public in the legacy feed."""
from __future__ import annotations

import argparse
from db import get_db
from services.intelligence_data_service import store_competitor_news


def backfill(*, apply: bool = False) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT DISTINCT ON (link,title,summary,published_date,category,vendor)
            link AS url,title,summary,published_date,category,vendor,created_at
            FROM competitor_news
            WHERE link ~* '^https?://[^/[:space:]]+' AND title IS NOT NULL AND title<>''
            ORDER BY link,title,summary,published_date,category,vendor,created_at,id""")
        rows = sorted((dict(row) for row in cursor.fetchall()),
                      key=lambda row: (str(row.get("created_at") or row.get("published_date") or ""), row["url"]))
        cursor.execute("SELECT id FROM intelligence_events WHERE 'competitor_dynamics'=ANY(business_scopes)")
        existing = {row["id"] for row in cursor.fetchall()}
        if not apply:
            return {"candidate_versions": len(rows), "distinct_urls": len({row["url"] for row in rows}), "applied": False}
        imported = set()
        for row in rows:
            event_id = store_competitor_news(cursor, {**row, "legacy_origin": "legacy_collector"})
            if event_id and event_id not in existing:
                imported.add(event_id)
        if imported:
            cursor.execute("""UPDATE intelligence_events SET status='active' WHERE id=ANY(%s)
                AND status='pending_review'""", (list(imported),))
        return {"candidate_versions": len(rows), "distinct_urls": len({row["url"] for row in rows}),
                "published_existing_legacy": len(imported), "applied": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write imported source evidence and Events")
    print(backfill(apply=parser.parse_args().apply))
