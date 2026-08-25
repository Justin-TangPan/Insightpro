"""Cloud-vendor and homepage data collection for InsightPro."""
from __future__ import annotations

import re
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from db import get_db

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


class CrawlerMonitor:
    def __init__(self):
        self.history: list[dict] = []

    def record(self, name: str, success: bool, items_count: int, duration_ms: int, error: str = ""):
        self.history.append({
            "name": name, "timestamp": datetime.now().isoformat(), "success": success,
            "items_count": items_count, "duration_ms": duration_ms, "error": error[:200],
        })
        self.history = self.history[-500:]

    def health_report(self) -> dict:
        if not self.history:
            return {"status": "no_data", "total_crawls": 0}
        recent = self.history[-100:]
        rate = sum(item["success"] for item in recent) / len(recent) * 100
        return {
            "status": "healthy" if rate >= 80 else "degraded" if rate >= 50 else "unhealthy",
            "total_crawls": len(self.history), "recent_success_rate": f"{rate:.0f}%",
        }


crawler_monitor = CrawlerMonitor()


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _is_quality_item(item: dict) -> bool:
    title = _clean(str(item.get("title") or ""))
    url = str(item.get("url") or item.get("link") or "")
    mojibake = ("ä¸", "å®", "æ", "è", "é", "ï¿½", "�")
    return len(title) >= 6 and url.startswith(("http://", "https://")) and not any(mark in title for mark in mojibake)


def _safe_get(url: str) -> requests.Response | None:
    started = time.time()
    try:
        response = requests.get(url, headers=HEADERS, timeout=12)
        response.raise_for_status()
        crawler_monitor.record(url.split("/")[2], True, 1, int((time.time() - started) * 1000))
        return response
    except Exception as error:
        crawler_monitor.record(url.split("/")[2], False, 0, int((time.time() - started) * 1000), str(error))
        return None


def _is_news_like(title: str, href: str) -> bool:
    if len(title) < 10:
        return False
    ignored = ("登录", "注册", "产品", "解决方案", "定价", "文档", "控制台", "首页", "关于", "招聘", "隐私", "条款", "Sign in", "Sign up")
    if any(word in title for word in ignored):
        return False
    href = href.lower()
    return any(word in href for word in ("news", "blog", "article", "release", "update", "case", "customer")) or any(
        word in title for word in ("发布", "上线", "推出", "更新", "升级", "合作", "签约", "案例", "开源", "新增", "集成", "Launch", "Release", "Update")
    )


def _crawl_vendor_news(vendor: str, source: str, urls: list[str], base: str, limit: int) -> list[dict]:
    for url in urls:
        response = _safe_get(url)
        if not response:
            continue
        response.encoding = "utf-8"
        items, seen = [], set()
        for link in BeautifulSoup(response.text, "html.parser").select("a[href]")[:120]:
            title, href = _clean(link.get_text()), link.get("href", "")
            if title in seen or not _is_news_like(title, href):
                continue
            seen.add(title)
            if not href.startswith("http"):
                href = f"{base}{href}"
            cooperation = any(word in title.lower() for word in ("合作", "携手", "联合", "签约", "客户", "案例", "partner", "customer"))
            items.append({
                "vendor": vendor, "source": source, "title": title, "summary": "", "url": href,
                "category": "合作案例" if cooperation else "产品动态",
            })
            if len(items) >= limit:
                break
        if items:
            return items
    return []


def crawl_cloud_vendors() -> list[dict]:
    sources = [
        ("阿里云", "阿里云", ["https://www.alibabacloud.com/blog", "https://www.alibabacloud.com/zh/news"], "https://www.alibabacloud.com", 6),
        ("腾讯云", "腾讯云", ["https://cloud.tencent.com/developer/news", "https://cloud.tencent.com/product/news"], "https://cloud.tencent.com", 6),
        ("火山云", "火山云", ["https://www.volcengine.com/"], "https://www.volcengine.com", 4),
        ("AWS", "AWS", ["https://aws.amazon.com/cn/about-aws/whats-new/", "https://aws.amazon.com/cn/blogs/china/"], "https://aws.amazon.com", 6),
        ("Azure", "Microsoft Azure", ["https://www.microsoft.com/en-us/customers", "https://azure.microsoft.com/en-us/blog/"], "https://www.microsoft.com", 6),
    ]
    return [item for args in sources for item in _crawl_vendor_news(*args)]


def crawl_all_news() -> dict:
    return {"cloud_vendors": crawl_cloud_vendors()}


def init_crawler_tables():
    pass


def store_crawl_results(results: dict) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    items = [{**item, "crawl_date": today} for item in results.get("cloud_vendors", []) if _is_quality_item(item)]
    count = 0
    with get_db() as conn:
        cursor = conn.cursor()
        for item in items:
            cursor.execute(
                """INSERT INTO cloud_vendor_news (crawl_date, vendor, title, summary, url, category)
                   VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                tuple(item.get(key, "") for key in ("crawl_date", "vendor", "title", "summary", "url", "category")),
            )
            count += cursor.rowcount > 0
    return {"cloud_vendor_news": count}


def run_daily_crawl() -> dict:
    now = datetime.now()
    stats = store_crawl_results(crawl_all_news())
    total = sum(stats.values())
    with get_db() as conn:
        conn.cursor().execute(
            "INSERT INTO scrape_log (scrape_date, scrape_time, status, items_count) VALUES (%s, %s, %s, %s)",
            (now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), "success" if total else "empty", total),
        )
    return stats


def get_cloud_vendor_news(days: int = 7, vendor: str | None = None, limit: int = 50) -> list[dict]:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    query, params = "SELECT * FROM cloud_vendor_news WHERE crawl_date >= %s", [cutoff]
    if vendor:
        query, params = query + " AND vendor = %s", params + [vendor]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query + " ORDER BY crawl_date DESC, id DESC LIMIT %s", params + [limit])
        return [dict(row) for row in cursor.fetchall()]


def get_homepage_stats() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
              (SELECT COUNT(*) FROM github_trending WHERE scrape_date=%s) AS trending_today,
              (SELECT COUNT(*) FROM trending_business_eval WHERE scrape_date=%s) AS evaluation_today,
              (SELECT COUNT(*) FROM aliyun_solutions WHERE is_active=TRUE) AS solution_count,
              (SELECT COUNT(*) FROM aliyun_solutions WHERE is_active=TRUE AND NOT is_baseline AND last_changed_date >= %s) AS solution_recent_count,
              (SELECT COUNT(*) FROM competitor_news WHERE scrape_date >= %s) AS competitor_count,
              (SELECT COUNT(*) FROM cloud_vendor_news WHERE crawl_date >= %s) AS cloud_news_count
        """, (today, today, week_ago, week_ago, week_ago))
        return dict(cursor.fetchone())


def get_homepage_modules() -> list[dict]:
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT repo_name, language FROM github_trending WHERE scrape_date=%s AND category='daily' ORDER BY id LIMIT 3", (today,))
        hotspots = [{"title": row["repo_name"], "tag": row["language"] or "Trending"} for row in cursor.fetchall()]
        cursor.execute("""
            SELECT title, category, first_seen_date, is_baseline
            FROM aliyun_solutions WHERE is_active=TRUE
            ORDER BY CASE WHEN NOT is_baseline AND first_seen_date=%s THEN 0 ELSE 1 END, menu_order, id
            LIMIT 3
        """, (today,))
        solutions = [{"title": row["title"], "tag": "NEW" if not row["is_baseline"] and row["first_seen_date"] == today else row["category"]} for row in cursor.fetchall()]
        cursor.execute("SELECT title, vendor FROM cloud_vendor_news WHERE crawl_date >= %s ORDER BY id DESC LIMIT 3", (week_ago,))
        competitors = [{"title": row["title"], "tag": row["vendor"]} for row in cursor.fetchall()]
    return [
        {"id": "hotspots", "label": "技术热点", "href": "/insights/hotspots", "items": hotspots},
        {"id": "solutions", "label": "解决方案洞察", "href": "/insights/solutions", "items": solutions},
        {"id": "competitors", "label": "友商洞察", "href": "/insights/competitors", "items": competitors},
    ]
