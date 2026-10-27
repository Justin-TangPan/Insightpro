"""Publish page data once after the daily pipeline; page requests only read published rows."""
from __future__ import annotations

import asyncio
import json
import logging
from contextvars import ContextVar
from datetime import datetime
from zoneinfo import ZoneInfo

from db import get_db

logger = logging.getLogger(__name__)
BUILDING = ContextVar("building_page_snapshot", default=False)
PAGE_PATHS = {
    "home": ["/api/radar/intelligence"],
    "technology": ["/api/v2/repositories/trending?period=daily",
                   "/api/v2/repositories/trending?period=weekly", "/api/v2/repositories/trending?period=monthly",
                   "/api/github-trending/business-eval",
                   "/api/github-trending/business-eval?locale=zh", "/api/github-trending/business-eval?locale=en",
                   *[f"/api/github-trending/history?days=14&category={period}&locale={locale}"
                     for period in ("daily", "weekly", "monthly") for locale in ("zh", "en")],
                   "/api/boards/github/daily-insight"],
    "applications": ["/api/agent-launches", "/api/boards/apps/daily-insight",
                     "/api/v2/events?business_scope=ai_applications&limit=8",
                     "/api/v2/events?business_scope=ai_applications&limit=100"],
    "solutions": ["/api/solutions/catalog", "/api/boards/solutions/daily-insight",
                  "/api/v2/events?business_scope=solutions&limit=100"],
    "community": ["/api/community/insights", "/api/boards/community/daily-insight",
                  "/api/community/insights/history", "/api/v2/events?business_scope=community_insights&limit=100"],
    "competitors": ["/api/competitors", "/api/competitors/summary?limit_per_vendor=100",
                    "/api/boards/competitors/daily-insight", "/api/competitors/history",
                    "/api/v2/events?business_scope=competitor_dynamics&limit=100"],
}
PATH_TO_PAGE = {path: page for page, paths in PAGE_PATHS.items() for path in paths}


def get_page_snapshot(path: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT id,snapshot_date,content,generated_at,version FROM page_snapshots
            WHERE page=%s ORDER BY snapshot_date DESC LIMIT 1""", (path,))
        row = cursor.fetchone()
    return dict(row) if row else None


async def publish_page_snapshots() -> dict:
    import httpx
    from main import app

    token = BUILDING.set(True)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://snapshot.local", timeout=90) as client:
            responses = await asyncio.gather(*(client.get(path) for path in PATH_TO_PAGE))
        contents = {}
        for path, response in zip(PATH_TO_PAGE, responses):
            response.raise_for_status()
            contents[path] = response.json()
        today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
        with get_db() as conn:
            cursor = conn.cursor()
            for path, content in contents.items():
                cursor.execute("""INSERT INTO page_snapshots (snapshot_date,page,content)
                    VALUES (%s,%s,%s::jsonb) ON CONFLICT (snapshot_date,page) DO UPDATE
                    SET content=EXCLUDED.content,generated_at=NOW(),version=page_snapshots.version+1""",
                    (today, path, json.dumps(content, ensure_ascii=False, default=str)))
        return {"date": today.isoformat(), "pages": list(PAGE_PATHS), "endpoints": len(contents)}
    finally:
        BUILDING.reset(token)


def publish_page_snapshots_sync() -> dict:
    return asyncio.run(publish_page_snapshots())


def bootstrap_page_snapshots_sync() -> dict | None:
    if all(get_page_snapshot(path) for path in PATH_TO_PAGE):
        return None
    return publish_page_snapshots_sync()
