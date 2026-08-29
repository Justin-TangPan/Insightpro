"""华为云解决方案实践采集与内容变更检测。"""
from __future__ import annotations

import html
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from db import get_db
from services.aliyun_solution_service import _change_summary, _content_hash, _fallback_summary, _summarize


INDEX_URL = "https://www.huaweicloud.com/solution/reference-architecture.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; InsightPro/0.4)"}
CARD_RE = re.compile(
    r'&quot;cardItem&quot;:\{.*?&quot;label&quot;:&quot;(.*?)&quot;.*?&quot;href&quot;:&quot;(https://www\.huaweicloud\.com/solution/implementations/[^&]+)&quot;.*?&quot;caption&quot;:&quot;(.*?)&quot;.*?&quot;description&quot;:&quot;(.*?)&quot;',
    re.S,
)
CATEGORY_ORDER = ("AI", "数据分析与管理", "应用现代化", "安全与合规", "网络", "运维监控", "云迁移")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _parse_catalog(page: str) -> list[dict]:
    items, seen = [], set()
    for category, url, title, description in CARD_RE.findall(page):
        url = html.unescape(url).split("?")[0]
        if url in seen:
            continue
        seen.add(url)
        title, category = _clean(html.unescape(title)), _clean(html.unescape(category))
        description = _clean(BeautifulSoup(html.unescape(description), "html.parser").get_text(" "))
        items.append({
            "title": title, "url": url,
            "category": f"{category} / 解决方案实践",
            "source_description": description,
            "menu_order": len(items),
        })
    if not items:
        raise ValueError("华为云解决方案目录没有可访问条目")
    order = {category: index for index, category in enumerate(CATEGORY_ORDER)}
    items.sort(key=lambda item: (order.get(item["category"].split(" / ")[0], len(order)), item["menu_order"]))
    for index, item in enumerate(items):
        item["menu_order"] = index
    return items


def _enrich(item: dict) -> dict:
    try:
        response = requests.get(item["url"], headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        heading = soup.select_one("h1")
        title = _clean(heading.get_text(" ") if heading else "")
        description = _clean((soup.select_one('meta[name="description"]') or {}).get("content", ""))
        sections = [_clean(node.get_text(" ")) for node in soup.select(".pep-solution-banner__desc, .scence-content-block_detail, .por-text-title-t3")]
        if title:
            item["title"] = title
        if description:
            item["source_description"] = description
        item["detail_text"] = " | ".join(sections)
    except Exception as exc:
        item["detail_failed"] = True
        item["detail_error"] = str(exc)
    return item


def scrape_huawei_solutions() -> list[dict]:
    response = requests.get(INDEX_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    items = _parse_catalog(response.text)
    with ThreadPoolExecutor(max_workers=6) as executor:
        return list(executor.map(_enrich, items))


def refresh_huawei_solutions() -> dict:
    items = scrape_huawei_solutions()
    today = datetime.now().strftime("%Y-%m-%d")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT url, title, category, source_description, content_hash, content_snapshot FROM aliyun_solutions WHERE vendor='华为云'")
        existing = {row["url"]: dict(row) for row in cursor.fetchall()}
        initial_baseline = not existing
        for item in items:
            old = existing.get(item["url"])
            if old and item.get("detail_failed"):
                item.update(title=old["title"], source_description=old["source_description"])
                snapshot = old.get("content_snapshot") or {}
                if isinstance(snapshot, str):
                    snapshot = json.loads(snapshot)
                item["detail_text"] = snapshot.get("detail_text", "")
            item["vendor"] = "华为云"
            item["content_snapshot"] = {key: item.get(key, "") for key in ("title", "category", "source_description", "detail_text")}
            item["content_hash"] = _content_hash(item)
        changed = [item for item in items if item["url"] not in existing or existing[item["url"]]["content_hash"] != item["content_hash"]]
        summaries = _summarize(changed)
        new_count = changed_count = 0
        for item in items:
            old = existing.get(item["url"])
            if not old:
                new_count += 1
                cursor.execute("""INSERT INTO aliyun_solutions
                    (title, url, category, source_description, summary, content_hash, vendor, content_snapshot, change_summary, first_seen_date, last_seen_date, last_changed_date, is_active, is_baseline, menu_order, removed_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,'',%s,%s,%s,TRUE,%s,%s,NULL)""",
                    (item["title"], item["url"], item["category"], item["source_description"], summaries[item["url"]], item["content_hash"], "华为云", json.dumps(item["content_snapshot"], ensure_ascii=False), today, today, today, initial_baseline, item["menu_order"]))
            elif old["content_hash"] != item["content_hash"]:
                changed_count += 1
                cursor.execute("""UPDATE aliyun_solutions SET title=%s, category=%s, source_description=%s, summary=%s, content_hash=%s, content_snapshot=%s::jsonb, change_summary=%s, last_seen_date=%s, last_changed_date=%s, is_active=TRUE, is_baseline=FALSE, menu_order=%s, removed_at=NULL, updated_at=NOW() WHERE url=%s""",
                    (item["title"], item["category"], item["source_description"], summaries[item["url"]], item["content_hash"], json.dumps(item["content_snapshot"], ensure_ascii=False), _change_summary(old, item), today, today, item["menu_order"], item["url"]))
            else:
                cursor.execute("UPDATE aliyun_solutions SET last_seen_date=%s, is_active=TRUE, removed_at=NULL, updated_at=NOW() WHERE url=%s", (today, item["url"]))
        cursor.execute("UPDATE aliyun_solutions SET is_active=FALSE, removed_at=NOW(), updated_at=NOW() WHERE is_active=TRUE AND vendor='华为云' AND url <> ALL(%s)", ([item["url"] for item in items],))
        removed_count = cursor.rowcount
    return {"status": "success", "checked_date": today, "total": len(items), "new": new_count, "updated": changed_count, "removed": removed_count}
