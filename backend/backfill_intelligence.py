"""Idempotently copy historical GitHub snapshots into the V2 intelligence tables."""
from __future__ import annotations

from db import get_db
from services.intelligence_data_service import store_github_signal


def backfill_github() -> int:
    last_id = 0
    copied = 0
    while True:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM (
                    SELECT id, scrape_date, scrape_time, repo_name, repo_url, description,
                           language, stars, forks, today_stars, category,
                           ROW_NUMBER() OVER (PARTITION BY scrape_date, category ORDER BY id) AS rank
                    FROM github_trending
                ) history
                WHERE id > %s ORDER BY id LIMIT 250
            """, (last_id,))
            rows = [dict(row) for row in cursor.fetchall()]
            if not rows:
                return copied
            for row in rows:
                last_id = row["id"]
                if not row["repo_name"] or not row["scrape_date"]:
                    continue
                item = {key: row[key] for key in ("repo_name", "repo_url", "description", "language", "stars", "forks", "today_stars", "category")}
                item["repo_url"] = item["repo_url"] or f"https://github.com/{item['repo_name']}"
                item["category"] = item["category"] or "daily"
                store_github_signal(cursor, item, row["scrape_date"], row["scrape_time"] or "00:00:00", row["rank"])
                copied += 1


if __name__ == "__main__":
    print(f"Backfilled {backfill_github()} historical GitHub snapshots")
