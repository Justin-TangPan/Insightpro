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

    def walk(nodes: list[dict] | None, categories: tuple[str, ...] = ()) -> None:
        for node in nodes or []:
            if node.get("visible") is False:
                continue
            title = _clean(node.get("title", ""))
            url = _canonical_url(node.get("url", "")) if node.get("url") else ""
            if title and url and url not in seen:
                seen.add(url)
                solutions.append({
                    "title": title,
                    "url": url,
                    "category": " / ".join(categories[:2]) or "技术解决方案",
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
    fingerprint = {key: value for key, value in item.items() if key not in {"content_hash", "detail_error", "detail_failed"}}
    return hashlib.sha256(json.dumps(fingerprint, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


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
        cursor.execute("SELECT url, title, source_description, content_hash, summary FROM aliyun_solutions")
        existing = {row["url"]: dict(row) for row in cursor.fetchall()}
        for item in items:
            old = existing.get(item["url"])
            if old and item.get("detail_failed"):
                item.update(
                    title=old["title"],
                    source_description=old["source_description"],
                    content_hash=old["content_hash"],
                )
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
                      (title, url, category, source_description, summary, content_hash,
                       first_seen_date, last_seen_date, last_changed_date, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                    """,
                    (item["title"], item["url"], item["category"], item["source_description"],
                     summaries[item["url"]], item["content_hash"], today, today, today),
                )
            elif old["content_hash"] != item["content_hash"]:
                changed_count += 1
                cursor.execute(
                    """
                    UPDATE aliyun_solutions
                    SET title=%s, category=%s, source_description=%s, summary=%s,
                        content_hash=%s, last_seen_date=%s, last_changed_date=%s,
                        is_active=TRUE, updated_at=NOW()
                    WHERE url=%s
                    """,
                    (item["title"], item["category"], item["source_description"], summaries[item["url"]],
                     item["content_hash"], today, today, item["url"]),
                )
            else:
                cursor.execute(
                    """UPDATE aliyun_solutions
                       SET last_seen_date=%s, is_active=TRUE, updated_at=NOW()
                       WHERE url=%s""",
                    (today, item["url"]),
                )

        current_urls = [item["url"] for item in items]
        cursor.execute(
            "UPDATE aliyun_solutions SET is_active=FALSE, updated_at=NOW() WHERE is_active=TRUE AND url <> ALL(%s)",
            (current_urls,),
        )
        removed_count = cursor.rowcount
    return {"status": "success", "checked_date": today, "total": len(items), "new": new_count, "updated": changed_count, "removed": removed_count}


def get_aliyun_solutions() -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, url, category, source_description, summary,
                   first_seen_date, last_seen_date, last_changed_date, updated_at
            FROM aliyun_solutions
            WHERE is_active=TRUE
            ORDER BY last_changed_date DESC, category, title
            """
        )
        items = [dict(row) for row in cursor.fetchall()]
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    for item in items:
        item["is_recent"] = item["last_changed_date"] >= cutoff
        item["change_type"] = "new" if item["first_seen_date"] == item["last_changed_date"] else "updated"
    return {
        "items": items,
        "count": len(items),
        "recent_count": sum(item["is_recent"] for item in items),
        "last_checked": max((item["last_seen_date"] for item in items), default=None),
        "source": INDEX_URL,
    }
