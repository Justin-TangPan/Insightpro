"""Competitor news retrieval and refresh."""
import logging
import json
from concurrent.futures import ThreadPoolExecutor

from datetime import datetime
from db import get_db
from services.intelligence_format import competitor as format_competitor
from settings import settings
from services import ai_service

logger = logging.getLogger(__name__)


def _source_key(item: dict) -> str:
    return f"{item['url']}::{item['title']}"


def get_competitor_news(date: str = None) -> list:
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM competitor_news WHERE scrape_date = %s ORDER BY id", (date,))
        return [dict(r) for r in c.fetchall()]


def get_competitor_summary(limit_per_vendor: int = 3) -> dict:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY vendor ORDER BY COALESCE(published_date, scrape_date::date) DESC, id DESC) AS rn
            FROM competitor_news news
            WHERE scrape_date=(SELECT MAX(latest.scrape_date) FROM competitor_news latest WHERE latest.vendor=news.vendor)
        ) ranked WHERE rn <= %s ORDER BY vendor, rn""", (limit_per_vendor,))
        rows = [dict(r) for r in c.fetchall()]
        c.execute("SELECT id, source_key, analysis FROM intelligence_analysis WHERE kind='competitor_update' AND source_key=ANY(%s)",
                  ([_source_key({"url": row["link"], "title": row["title"]}) for row in rows if row.get("link")],))
        analyses = {row["source_key"]: row for row in c.fetchall()}
        grouped = {}
        for row in rows:
            v = row["vendor"]
            if v not in grouped:
                grouped[v] = []
            item = {"id": row["id"], "vendor": v, "title": row["title"], "summary": row["summary"], "link": row["link"], "category": row["category"], "date": row.get("published_date") or row["scrape_date"]}
            analysis = analyses.get(_source_key({"url": item["link"], "title": item["title"]})) if item.get("link") else None
            item["analysis"] = analysis["analysis"] if analysis else None
            item["analysis_id"] = analysis["id"] if analysis else None
            item["intelligence"] = format_competitor(item)
            grouped[v].append(item)
        return grouped


def _ensure_analyses(items: list[dict]) -> int:
    if not settings.CHAT_API_KEY:
        return 0
    sources = {_source_key(item): item for item in items if item.get("url") and item.get("title")}
    if not sources:
        return 0
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT source_key FROM intelligence_analysis WHERE kind='competitor_update' AND source_key=ANY(%s)", (list(sources),))
        analyzed = {row["source_key"] for row in cursor.fetchall()}
        missing = [sources[key] for key in sources if key not in analyzed]

    def analyze(batch: list[dict]) -> list[dict]:
        prompt = "仅依据各条厂商官方来源的标题和摘要（摘要可能为空），写一到两句简体中文技术情报分析：说明实际变化及其对方案选型的影响。只有标题时不得推断细节，并明确标注需核实。只返回 JSON 数组，每项包含原样数字 index 和 analysis；不得补充来源之外的事实。\n" + json.dumps(
            [{"index": index, "title": item["title"], "summary": item.get("summary") or ""} for index, item in enumerate(batch)], ensure_ascii=False)
        return ai_service.extract_json_array(ai_service.chat_complete(user_prompt=prompt, temperature=0.2, max_tokens=1600, timeout=60))

    batches = [missing[offset:offset + 8] for offset in range(0, len(missing), 8)]
    saved = 0
    with ThreadPoolExecutor(max_workers=3) as pool:
        for batch, future in zip(batches, [pool.submit(analyze, batch) for batch in batches]):
            try:
                results = future.result()
            except Exception as exc:
                logger.warning("competitor analysis failed: %s", exc)
                continue
            with get_db() as conn:
                cursor = conn.cursor()
                for row in results:
                    index = row.get("index")
                    if isinstance(index, int) and not isinstance(index, bool) and 0 <= index < len(batch) and isinstance(row.get("analysis"), str) and row["analysis"].strip():
                        cursor.execute("INSERT INTO intelligence_analysis (kind, source_key, analysis) VALUES ('competitor_update',%s,%s) ON CONFLICT (kind, source_key) DO NOTHING",
                                       (_source_key(batch[index]), row["analysis"].strip()))
                        saved += cursor.rowcount
    return saved


def backfill_competitor_analyses(limit: int = 500) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT url, title, summary FROM (
                            SELECT DISTINCT ON (link, title) link AS url, title, summary, scrape_date
                            FROM competitor_news WHERE link IS NOT NULL AND title IS NOT NULL
                            ORDER BY link, title, scrape_date DESC, id DESC
                          ) sources ORDER BY scrape_date DESC LIMIT %s""", (limit,))
        rows = [dict(row) for row in cursor.fetchall()]
    saved = _ensure_analyses(rows)
    return {"sources": len(rows), "new_analyses": saved}


def refresh_competitor_news():
    today = datetime.now().strftime("%Y-%m-%d")
    from services.source_registry_service import record_source_health, source_enabled
    if not source_enabled("competitor_news"):
        return []
    from crawlers import crawl_cloud_vendors, store_crawl_results
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT result ? 'competitor_news' AS collected
                          FROM platform_task_runs
                          WHERE task_key='daily_crawl' AND status='success'
                            AND (started_at AT TIME ZONE 'Asia/Shanghai')::date=%s
                          ORDER BY started_at DESC LIMIT 1""", (today,))
        daily_crawl_collected = bool((cursor.fetchone() or {}).get("collected"))
    if daily_crawl_collected:
        items = get_competitor_news(today)
        for item in items:
            item.setdefault("url", item.get("link"))
    else:
        try:
            items = crawl_cloud_vendors()
        except Exception as exc:
            record_source_health("competitor_news", "failed", str(exc))
            raise
    if not items:
        logger.info("cloud vendor crawl returned no data for %s", today)
        record_source_health("competitor_news", "empty")
        return []
    if not daily_crawl_collected:
        store_crawl_results({"cloud_vendors": items})
    from services.intelligence_data_service import store_competitor_news
    with get_db() as conn:
        cursor = conn.cursor()
        for item in items:
            store_competitor_news(cursor, item)
    record_source_health("competitor_news", "healthy")
    try:
        _ensure_analyses(items)
    except Exception as exc:
        logger.warning("competitor analysis postponed: %s", exc)
    return get_competitor_news(today)
