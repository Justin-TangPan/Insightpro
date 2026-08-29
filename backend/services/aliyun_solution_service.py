"""阿里云技术解决方案采集、摘要与更新检测。"""
from __future__ import annotations
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, urlunparse

import requests

from db import get_db
from settings import settings


INDEX_URL = "https://cn.aliyun.com/solution/tech-solution/"
MENU_URL = "https://developer.aliyun.com/adc/api/skillBuilder/getMenuTree"
DETAIL_URL = "https://help.aliyun.cn/help/json/document_detail.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; InsightPro/0.4)"}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _canonical_url(url: str) -> str:
    parsed = urlparse(urljoin(INDEX_URL, url))
    if parsed.path.startswith("/solution/tech-solution/"):
        return urlunparse(("https", "cn.aliyun.com", parsed.path.rstrip("/"), "", "", ""))
    return urlunparse(("https", parsed.netloc, parsed.path.rstrip("/"), "", parsed.query, parsed.fragment))


def _parse_menu_tree(payload: dict) -> list[dict]:
    roots = payload.get("data")
    if not isinstance(roots, list) or not roots:
        raise ValueError("阿里云解决方案目录为空")

    solutions = []
    seen = set()
    menu_order = 0

    def walk(nodes: list[dict] | None, categories: tuple[str, ...] = ()) -> None:
        nonlocal menu_order
        for node in nodes or []:
            if node.get("visible") is False:
                continue
            title = _clean(node.get("title", ""))
            url = _canonical_url(node.get("url", "")) if node.get("url") else ""
            if title and url and url not in seen:
                seen.add(url)
                category_path = categories if len(categories) >= 2 else categories + (title,)
                primary_category = category_path[0] if category_path else "技术解决方案"
                secondary_category = category_path[1] if len(category_path) > 1 else "分类入口"
                solutions.append({
                    "title": title,
                    "url": url,
                    "category": f"{primary_category} / {secondary_category}",
                    "primary_category": primary_category,
                    "secondary_category": secondary_category,
                    "menu_order": menu_order,
                    "source_type": node.get("type", ""),
                    "node_id": node.get("abcId") or 0,
                    "source_description": "",
                    "menu_data": {
                        "id": node.get("id"),
                        "parentId": node.get("parentId"),
                        "type": node.get("type"),
                        "tags": node.get("tags") or [],
                    },
                })
                menu_order += 1
            next_categories = categories if url else categories + ((title,) if title else ())
            walk(node.get("children"), next_categories)

    walk(roots)
    if not solutions:
        raise ValueError("阿里云解决方案目录没有可访问条目")
    return solutions


def _parse_detail_payload(payload: dict) -> dict:
    data = payload.get("data") or {}
    return {
        "title": _clean(data.get("docTitle") or data.get("title") or ""),
        "source_description": _clean(data.get("desc", "")),
        "last_modified": data.get("lastModifiedTime"),
        "version": data.get("version"),
    }


def _fallback_summary(title: str, description: str) -> str:
    description = _clean(description)
    for text in re.split(r"[，。；]", description):
        text = text.strip()
        if 20 <= len(text) <= 30:
            return text
    if len(description) >= 20:
        return description[:30].rstrip("，,；;：:。 ")
    return (_clean(title) + "，提供云上业务架构设计、部署与落地实践")[:30]


def _summarize(items: list[dict]) -> dict[str, str]:
    fallback = {item["url"]: _fallback_summary(item["title"], item["source_description"]) for item in items}
    # ponytail: bulk imports use official descriptions; batch model calls only if editorial summaries become necessary.
    if not items or len(items) > 20 or not settings.CHAT_API_KEY:
        return fallback
    from services.ai_service import chat_complete, extract_json_array

    prompt = "请分析以下阿里云解决方案，输出 JSON 数组。每项只含 url 和 summary；summary 必须为20至30个中文字符，说明方案是什么和解决什么问题，不写营销套话。\n" + "\n".join(
        f"{item['url']} | {item['title']} | {item['source_description']}" for item in items
    )
    try:
        rows = extract_json_array(chat_complete(user_prompt=prompt, temperature=0.2, max_tokens=1200, timeout=90))
        for row in rows:
            url = row.get("url")
            summary = _clean(row.get("summary", ""))
            if url in fallback and 20 <= len(summary) <= 30:
                fallback[url] = summary
    except Exception as exc:
        print(f"[Aliyun Solutions] AI 摘要失败，使用页面摘要: {exc}")
    return fallback


def _content_hash(item: dict) -> str:
    fingerprint = {key: value for key, value in item.items() if key not in {"content_hash", "detail_error", "detail_failed", "menu_order", "vendor", "content_snapshot"}}
    return hashlib.sha256(json.dumps(fingerprint, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _change_summary(old: dict, item: dict) -> str:
    """Return the small, user-facing diff instead of only saying 'updated'."""
    before = old.get("content_snapshot") or {
        "title": old.get("title", ""), "category": old.get("category", ""),
        "source_description": old.get("source_description", ""),
    }
    if isinstance(before, str):
        try:
            before = json.loads(before)
        except json.JSONDecodeError:
            before = {}
    after = item.get("content_snapshot") or {}
    labels = (("title", "方案名称"), ("category", "所属分类"), ("source_description", "方案简介"), ("detail_text", "方案正文"))
    changes = []
    for field, label in labels:
        old_value, new_value = _clean(str(before.get(field, ""))), _clean(str(after.get(field, "")))
        if old_value != new_value:
            if field == "detail_text":
                changes.append("方案正文已更新")
            else:
                changes.append(f"{label}：{old_value[:80] or '（无）'} → {new_value[:80] or '（无）'}")
    return "；".join(changes) or "方案页面内容已更新"


def _classify_change(item: dict, cutoff: str) -> tuple[bool, str]:
    change_type = "new" if item["first_seen_date"] == item["last_changed_date"] else "updated"
    return not item["is_baseline"] and item["last_changed_date"] >= cutoff, change_type


def _enrich_solution(item: dict) -> dict:
    if not item["node_id"]:
        item["content_hash"] = _content_hash(item)
        return item
    try:
        response = requests.get(
            DETAIL_URL,
            params={
                "nodeId": item["node_id"], "alias": "", "pageNum": 1, "pageSize": 20,
                "website": "cn", "language": "zh", "channel": "",
            },
            headers=HEADERS,
            timeout=30,
        )
        response.raise_for_status()
        detail = _parse_detail_payload(response.json())
        item["source_description"] = detail["source_description"]
        item["detail_data"] = detail
    except Exception as exc:
        item["detail_failed"] = True
        item["detail_error"] = str(exc)
    item["content_hash"] = _content_hash(item)
    return item


def scrape_aliyun_solutions() -> list[dict]:
    response = requests.get(MENU_URL, params={"aliyun_lang": "zh"}, headers=HEADERS, timeout=30)
    response.raise_for_status()
    solutions = _parse_menu_tree(response.json())
    with ThreadPoolExecutor(max_workers=6) as executor:
        solutions = list(executor.map(_enrich_solution, solutions))
    failures = sum(bool(item.get("detail_failed")) for item in solutions)
    if failures:
        print(f"[Aliyun Solutions] {failures} 个详情读取失败，保留目录数据")
    return solutions


def refresh_aliyun_solutions() -> dict:
    items = scrape_aliyun_solutions()
    today = datetime.now().strftime("%Y-%m-%d")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT url, title, category, source_description, content_hash, summary, is_baseline, content_snapshot FROM aliyun_solutions WHERE vendor='阿里云'")
        existing = {row["url"]: dict(row) for row in cursor.fetchall()}
        initial_baseline = not existing
        for item in items:
            old = existing.get(item["url"])
            if old and item.get("detail_failed"):
                item.update(
                    title=old["title"],
                    source_description=old["source_description"],
                )
                snapshot = old.get("content_snapshot") or {}
                if isinstance(snapshot, str):
                    snapshot = json.loads(snapshot)
                item["vendor"] = "阿里云"
                item["content_snapshot"] = snapshot
                item["content_hash"] = old["content_hash"]
                continue
            item["vendor"] = "阿里云"
            item["content_snapshot"] = {
                "title": item["title"], "category": item["category"],
                "source_description": item["source_description"],
                "detail_text": _clean(json.dumps(item.get("detail_data") or {}, ensure_ascii=False)),
            }
            item["content_hash"] = _content_hash(item)
        changed = [item for item in items if item["url"] not in existing or existing[item["url"]]["content_hash"] != item["content_hash"]]
        summaries = _summarize(changed)

        new_count = changed_count = 0
        for item in items:
            old = existing.get(item["url"])
            if not old:
                new_count += 1
                cursor.execute(
                    """
                    INSERT INTO aliyun_solutions
                      (title, url, category, source_description, summary, content_hash, vendor, content_snapshot, change_summary,
                       first_seen_date, last_seen_date, last_changed_date, is_active,
                       is_baseline, menu_order, removed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, '', %s, %s, %s, TRUE, %s, %s, NULL)
                    """,
                    (item["title"], item["url"], item["category"], item["source_description"],
                     summaries[item["url"]], item["content_hash"], item["vendor"], json.dumps(item["content_snapshot"], ensure_ascii=False), today, today, today,
                     initial_baseline, item["menu_order"]),
                )
            elif old["content_hash"] != item["content_hash"]:
                changed_count += 1
                cursor.execute(
                    """
                    UPDATE aliyun_solutions
                    SET title=%s, category=%s, source_description=%s, summary=%s, vendor=%s,
                        content_hash=%s, last_seen_date=%s, last_changed_date=%s,
                        content_snapshot=%s::jsonb, change_summary=%s, is_active=TRUE, is_baseline=FALSE, menu_order=%s,
                        removed_at=NULL, updated_at=NOW()
                    WHERE url=%s
                    """,
                    (item["title"], item["category"], item["source_description"], summaries[item["url"]], item["vendor"],
                     item["content_hash"], today, today, json.dumps(item["content_snapshot"], ensure_ascii=False), _change_summary(old, item), item["menu_order"], item["url"]),
                )
            else:
                cursor.execute(
                    """UPDATE aliyun_solutions
                       SET category=%s, menu_order=%s, last_seen_date=%s,
                           is_active=TRUE, removed_at=NULL, updated_at=NOW()
                       WHERE url=%s""",
                    (item["category"], item["menu_order"], today, item["url"]),
                )

        current_urls = [item["url"] for item in items]
        cursor.execute(
            """UPDATE aliyun_solutions
               SET is_active=FALSE, removed_at=NOW(), updated_at=NOW()
               WHERE is_active=TRUE AND vendor='阿里云' AND url <> ALL(%s)""",
            (current_urls,),
        )
        removed_count = cursor.rowcount
    return {"status": "success", "checked_date": today, "total": len(items), "new": new_count, "updated": changed_count, "removed": removed_count}


def refresh_solution_catalogs() -> dict:
    """Refresh both official catalogues in one scheduled/manual check."""
    from services.huawei_solution_service import refresh_huawei_solutions
    aliyun = refresh_aliyun_solutions()
    huawei = refresh_huawei_solutions()
    return {
        "status": "success", "checked_date": aliyun["checked_date"],
        "total": aliyun["total"] + huawei["total"],
        "new": aliyun["new"] + huawei["new"],
        "updated": aliyun["updated"] + huawei["updated"],
        "removed": aliyun["removed"] + huawei["removed"],
        "vendors": {"阿里云": aliyun, "华为云": huawei},
    }


def get_aliyun_solutions() -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, url, category, source_description, summary, vendor, change_summary,
                   first_seen_date, last_seen_date, last_changed_date,
                   is_baseline, menu_order, updated_at
            FROM aliyun_solutions
            WHERE is_active=TRUE
            ORDER BY vendor, menu_order, title
            """
        )
        items = [dict(row) for row in cursor.fetchall()]
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    for item in items:
        primary, _, secondary = item["category"].partition(" / ")
        item["primary_category"] = primary
        item["secondary_category"] = secondary or "分类入口"
        item["is_recent"], item["change_type"] = _classify_change(item, cutoff)
    items.sort(key=lambda item: (
        0 if item["is_recent"] and item["change_type"] == "new" else
        1 if item["is_recent"] else 2,
        item["menu_order"], item["title"],
    ))
    today = datetime.now().strftime("%Y-%m-%d")
    vendors = ("阿里云", "华为云")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT vendor, COUNT(*)::int AS count FROM aliyun_solutions WHERE NOT is_active AND removed_at::date=CURRENT_DATE GROUP BY vendor"
        )
        removed_today = {row["vendor"]: row["count"] for row in cursor.fetchall()}
    daily_insights = {}
    for vendor in vendors:
        vendor_items = [item for item in items if item["vendor"] == vendor]
        new_today = sum(not item["is_baseline"] and item["first_seen_date"] == today for item in vendor_items)
        updated_today = sum(
            not item["is_baseline"] and item["last_changed_date"] == today
            and item["first_seen_date"] != item["last_changed_date"] for item in vendor_items
        )
        daily_insights[vendor] = {"date": today, "new": new_today, "updated": updated_today, "removed": removed_today.get(vendor, 0)}
    return {
        "items": items,
        "count": len(items),
        "recent_count": sum(item["is_recent"] for item in items),
        "baseline_count": sum(item["is_baseline"] for item in items),
        "daily_insight": {"date": today, "new": sum(row["new"] for row in daily_insights.values()), "updated": sum(row["updated"] for row in daily_insights.values()), "removed": sum(row["removed"] for row in daily_insights.values())},
        "daily_insights": daily_insights,
        "last_checked": max((item["last_seen_date"] for item in items), default=None),
        "sources": {"阿里云": INDEX_URL, "华为云": "https://www.huaweicloud.com/solution/reference-architecture.html"},
    }


get_solution_catalog = get_aliyun_solutions
