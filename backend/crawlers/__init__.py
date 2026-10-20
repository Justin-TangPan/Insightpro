"""Cloud-vendor and homepage data collection for InsightPro."""
from __future__ import annotations

import re
import time
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

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

VENDOR_SOURCES = [
    ("Alibaba Cloud", "Alibaba Cloud China Official", ["https://cn.aliyun.com/product/news?category=21", "https://www.aliyun.com/notice/"], 12),
    ("Tencent Cloud", "Tencent Cloud China Official", ["https://cloud.tencent.com/product/events", "https://cloud.tencent.com/announce"], 12),
    ("Volcengine", "Volcengine Official", [
        "https://docs.volcengine.com/docs/ark/coding-plan-personal-feature-release?lang=zh",
        "https://docs.volcengine.com/docs/cache/feature-release-note?lang=zh",
        "https://docs.volcengine.com/docs/RDS_for_MySQL/release_notes?lang=zh",
    ], 8),
    ("AWS", "AWS Official", ["https://aws.amazon.com/about-aws/whats-new/recent/feed/"], 8),
    ("Microsoft Azure", "Microsoft Official", ["https://azure.microsoft.com/en-us/blog/feed/"], 8),
]


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
    ignored = ("登录", "注册", "产品", "解决方案", "定价", "文档", "控制台", "首页", "关于", "招聘", "隐私", "条款", "Sign in", "Sign up", "Skip to", "Manage cookies", "Learn more", "Create Account", "Customer stories", "Case Studies", "Login", "Register", "Products", "Solutions", "Pricing", "Docs", "Console", "Home", "About", "Careers", "Privacy", "Terms")
    if any(word in title for word in ignored):
        return False
    href = href.lower()
    return any(word in href for word in ("news", "blog", "article", "release", "update", "case", "customer")) or any(
        word in title for word in ("发布", "上线", "推出", "更新", "升级", "合作", "签约", "案例", "开源", "新增", "集成", "Launch", "Release", "Update", "Announce", "GA", "Upgrade", "Partnership", "Open Source", "Integrate")
    )


def _crawl_vendor_news(vendor: str, source: str, urls: list[str], limit: int) -> list[dict]:
    if vendor == "Alibaba Cloud":
        return _crawl_aliyun_updates(urls[0], limit)
    if vendor == "Tencent Cloud":
        return _crawl_tencent_updates(urls[0], limit)
    if vendor == "Volcengine":
        return _crawl_volcengine_updates(urls, limit)
    if urls[0].endswith("/feed/"):
        return _crawl_rss(vendor, source, urls[0], limit)
    items, seen = [], set()
    for url in urls:
        response = _safe_get(url)
        if not response:
            continue
        response.encoding = "utf-8"
        for link in BeautifulSoup(response.text, "html.parser").select("a[href]")[:240]:
            title, href = _clean(link.get_text()), link.get("href", "")
            absolute_url = urljoin(url, href)
            key = (title.casefold(), absolute_url.split("#", 1)[0])
            if key in seen or not _is_news_like(title, absolute_url):
                continue
            seen.add(key)
            cooperation = any(word in title.lower() for word in ("合作", "携手", "联合", "签约", "客户", "案例", "partner", "customer", "collaborate", "sign", "client", "case"))
            detail = _safe_get(absolute_url)
            detail_soup = BeautifulSoup(detail.text, "html.parser") if detail else None
            description = _clean((detail_soup.select_one('meta[name="description"]') or {}).get("content", "")) if detail_soup else ""
            items.append({
                "vendor": vendor, "source": source, "title": title, "summary": f"Use: {description or title}", "url": absolute_url,
                "category": "Case Study" if cooperation else "Product Update",
            })
            if len(items) >= limit:
                return items
    return items


def _crawl_rss(vendor: str, source: str, url: str, limit: int) -> list[dict]:
    response = _safe_get(url)
    if not response:
        return []
    items = []
    for entry in ElementTree.fromstring(response.content).findall("./channel/item"):
        title = _clean(entry.findtext("title", ""))
        link = _clean(entry.findtext("link", ""))
        try:
            published = parsedate_to_datetime(entry.findtext("pubDate", "")).date().isoformat()
        except (TypeError, ValueError):
            continue
        if not _recent(published):
            continue
        description = _clean(BeautifulSoup(entry.findtext("description", ""), "html.parser").get_text(" "))
        cooperation = any(word in title.lower() for word in ("partner", "customer", "case study"))
        items.append({"vendor": vendor, "source": source, "title": title, "summary": f"Use: {description or title}"[:500],
                      "url": link, "published_date": published, "category": "Case Study" if cooperation else _update_category("", title)})
        if len(items) >= limit:
            break
    return items


def _update_category(kind: str, title: str) -> str:
    if "解决方案" in title or "方案上线" in title or "Solution" in title or "Solution Launch" in title:
        return "Solution New"
    if "新产品" in kind or any(word in title for word in ("产品发布", "正式发布", "全新发布", "产品上市", "Product Launch", "General Availability", "GA", "Now Available")):
        return "Product Launch"
    if "价格" in kind or "Price" in kind:
        return "Price Change"
    if "地域" in kind or "可用区" in kind or "Region" in kind or "Availability Zone" in kind:
        return "Region New"
    return "Feature Update"


def _recent(published: str, days: int = 45) -> bool:
    try:
        return date.fromisoformat(published) >= date.today() - timedelta(days=days)
    except ValueError:
        return False


def _domestic_focus(title: str) -> bool:
    overseas = ("墨西哥", "巴西", "马来西亚", "阿联酋", "迪拜", "新加坡", "东京", "首尔", "硅谷", "弗吉尼亚", "法兰克福", "曼谷", "孟买", "多伦多", "Mexico", "Brazil", "Malaysia", "UAE", "Dubai", "Singapore", "Tokyo", "Seoul", "Silicon Valley", "Virginia", "Frankfurt", "Bangkok", "Mumbai", "Toronto")
    return not any(place in title for place in overseas)


def _crawl_aliyun_updates(url: str, limit: int) -> list[dict]:
    response = _safe_get(url)
    if not response:
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    candidates, seen = [], set()
    for card in soup.select("div.slider-item"):
        link = card.select_one("a.item-top[href]")
        title_node = card.select_one(".desc")
        match = re.search(r"20\d{2}[.-]\d{2}[.-]\d{2}", card.get_text(" ", strip=True))
        if not link or not title_node or not match:
            continue
        title = _clean(title_node.get_text(" ", strip=True))
        published = match.group().replace(".", "-")
        href = urljoin(url, link.get("href", ""))
        if href in seen or not _recent(published) or not _domestic_focus(title):
            continue
        seen.add(href)
        kind = _clean(card.get_text(" ", strip=True).split(match.group(), 1)[-1])
        candidates.append((published, title, href, kind))
    items = []
    for published, title, href, kind in sorted(candidates, reverse=True)[:limit]:
        detail = _safe_get(href)
        detail_soup = BeautifulSoup(detail.text, "html.parser") if detail else None
        description = _clean((detail_soup.select_one('meta[name="description"]') or {}).get("content", "")) if detail_soup else ""
        items.append({"vendor": "Alibaba Cloud", "source": "Alibaba Cloud China Official", "title": title,
                      "summary": f"Use: {description or title}", "url": href, "published_date": published,
                      "category": _update_category(kind, title)})
    return items


def _crawl_tencent_updates(url: str, limit: int) -> list[dict]:
    response = _safe_get(url)
    if not response:
        return []
    items = []
    for card in BeautifulSoup(response.text, "html.parser").select("div.pr2-product-panel__inner"):
        title_node = card.select_one("h3.pr2-product-panel__tit")
        match = re.search(r"20\d{2}-\d{2}-\d{2}", card.get_text(" ", strip=True))
        if not title_node or not match or not _recent(match.group()):
            continue
        title = _clean(title_node.get_text(" ", strip=True))
        if not _domestic_focus(title):
            continue
        text = _clean(card.get_text(" ", strip=True))
        rest = text.split(match.group(), 1)[-1]
        description = _clean(rest.split("产品介绍页", 1)[0].split("产品文档", 1)[0])
        kind_node = card.select_one(".pr2-product-panel__tag")
        link = card.select_one("a[href]")
        items.append({"vendor": "Tencent Cloud", "source": "Tencent Cloud China Official", "title": title,
                      "summary": f"Use: {description or title}", "url": urljoin(url, link.get("href", "")) if link else url,
                      "published_date": match.group(), "category": _update_category(_clean(kind_node.get_text()) if kind_node else text, title)})
        if len(items) >= limit:
            break
    return items


def _parse_volcengine_updates(markdown: str, product: str, url: str, today: date) -> list[dict]:
    items = []
    for line in markdown.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3 or cells[0].startswith("---"):
            continue
        date_cell = cells[0] if re.fullmatch(r"\d{2}\.\d{2}", cells[0]) else cells[2]
        raw_date = re.search(r"20\d{2}\\?-\d{2}\\?-\d{2}|\b\d{2}\.\d{2}\b", date_cell)
        if not raw_date:
            continue
        value = raw_date.group().replace("\\", "")
        try:
            published = date.fromisoformat(value if "-" in value else f"{today.year}-{value.replace('.', '-')}")
        except ValueError:
            continue
        if not today - timedelta(days=45) <= published <= today:
            continue
        if "." in value:
            detail = cells[1]
            title = re.split(r"[。；;<]", detail.lstrip("* "))[0]
            summary = detail
        else:
            title, summary = cells[0], cells[1]
        title = _clean(re.sub(r"\[([^]]+)\]\([^)]+\)|[`*]", lambda match: match.group(1) if match.group().startswith("[") else "", title))
        summary = _clean(re.sub(r"\[([^]]+)\]\([^)]+\)|<br\s*/?>|[`*]", lambda match: match.group(1) if match.group().startswith("[") else " ", summary))
        if not title or not summary:
            continue
        items.append({"vendor": "Volcengine", "source": "Volcengine Official", "title": f"{product} · {title[:100]}",
                      "summary": f"Use: {summary[:450]}", "url": url, "published_date": published.isoformat(),
                      "category": _update_category("", title)})
    return items


def _crawl_volcengine_updates(urls: list[str], limit: int) -> list[dict]:
    today = date.today()
    items = []
    labels = {"ark": "火山方舟 Coding Plan", "cache": "缓存数据库 Redis 版", "RDS_for_MySQL": "云数据库 MySQL 版"}
    for url in urls:
        _, _, library, document = urlparse(url).path.split("/", 3)
        api_url = f"https://docs.volcengine.com/api/doc/getDocDetail?type=online&LibraryCode={library}&DocumentCode={document}"
        response = _safe_get(api_url)
        if not response:
            continue
        try:
            markdown = response.json()["Result"]["MDContent"]
        except (ValueError, KeyError, TypeError):
            continue
        items.extend(_parse_volcengine_updates(markdown, labels[library], url, today)[:3])
    return sorted(items, key=lambda item: item["published_date"], reverse=True)[:limit]


def crawl_cloud_vendors() -> list[dict]:
    return [item for args in VENDOR_SOURCES for item in _crawl_vendor_news(*args)]


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
        vendors = sorted({item["vendor"] for item in items})
        if vendors:
            cursor.execute("DELETE FROM competitor_news WHERE scrape_date=%s AND vendor = ANY(%s)", (today, vendors))
        for item in items:
            cursor.execute(
                """INSERT INTO competitor_news (scrape_date, published_date, vendor, title, summary, link, category)
                   VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                tuple(item.get(key) or None for key in ("crawl_date", "published_date", "vendor", "title", "summary", "url", "category")),
            )
            count += cursor.rowcount > 0
    return {"competitor_news": count}


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
    query, params = "SELECT id, COALESCE(published_date, scrape_date::date) AS crawl_date, vendor, title, summary, link AS url, category FROM competitor_news WHERE scrape_date >= %s", [cutoff]
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
              (SELECT COUNT(*) FROM competitor_news WHERE scrape_date >= %s) AS cloud_news_count
        """, (today, today, week_ago, week_ago, week_ago))
        return dict(cursor.fetchone())


def get_homepage_modules() -> list[dict]:
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.repo_name, g.language, COALESCE(e.summary_zh, e.summary, g.description) AS summary
            FROM github_trending g LEFT JOIN trending_business_eval e
              ON e.scrape_date=g.scrape_date AND e.repo_name=g.repo_name
            WHERE g.scrape_date=%s AND g.category='daily' ORDER BY g.id LIMIT 3
        """, (today,))
        hotspots = [{"title": row["repo_name"], "tag": row["language"] or "趋势项目", "summary": row["summary"] or ""} for row in cursor.fetchall()]
        cursor.execute("""
            SELECT repo_name, repo_url, COALESCE(summary_zh, summary, reasoning) AS summary,
                   ROUND(((d1+d2+d3+d4)/4.0)::numeric, 1) AS total
            FROM trending_business_eval WHERE scrape_date=%s AND (d1+d2+d3+d4)/4.0 >= 8
            ORDER BY total DESC LIMIT 3
        """, (today,))
        values = [{"title": row["repo_name"], "href": row["repo_url"] or "/insights/hotspots", "tag": f'{float(row["total"]):.1f} / 10', "summary": row["summary"] or ""} for row in cursor.fetchall()]
        cursor.execute("""
            SELECT title, category, first_seen_date, is_baseline, COALESCE(NULLIF(source_description, ''), summary) AS summary
            FROM aliyun_solutions WHERE is_active=TRUE
            ORDER BY CASE WHEN NOT is_baseline AND first_seen_date=%s THEN 0 ELSE 1 END, menu_order, id
            LIMIT 3
        """, (today,))
        solutions = [{"title": row["title"], "tag": "今日新增" if not row["is_baseline"] and row["first_seen_date"] == today else row["category"], "summary": row["summary"] or ""} for row in cursor.fetchall()]
        cursor.execute("SELECT title, summary FROM competitor_news WHERE scrape_date >= %s AND vendor='Alibaba Cloud' ORDER BY id DESC LIMIT 3", (week_ago,))
        competitors = [{"title": row["title"], "tag": "阿里云", "summary": (row["summary"] or "").removeprefix("Use: ")} for row in cursor.fetchall()]
    return [
        {"id": "values", "label": "Today's Valuable Solutions", "href": "/insights/hotspots", "items": values},
        {"id": "hotspots", "label": "Project Insights", "href": "/insights/hotspots", "items": hotspots},
        {"id": "solutions", "label": "Solution Insights", "href": "/insights/solutions", "items": solutions},
        {"id": "competitors", "label": "Competitor Insights", "href": "/insights/competitors", "items": competitors},
    ]
