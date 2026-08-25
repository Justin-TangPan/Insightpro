"""Global search across public insights and the signed-in user's workbench."""
from __future__ import annotations

import asyncio
import re
from collections import Counter
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from db import get_db
from routers.auth import get_current_user

router = APIRouter()
SearchKind = Literal["all", "technical", "solution", "competitor", "requirement", "managed_solution"]


def _tokens(query: str) -> list[str]:
    return list(dict.fromkeys(part.lower() for part in re.findall(r"[\w\-./]+", query, re.UNICODE) if part))[:8]


def _search_rows(cursor, sql: str, document: str, tokens: list[str], extra_params: tuple = ()) -> list[dict]:
    conditions = " AND ".join(f"({document}) ILIKE %s" for _ in tokens)
    cursor.execute(sql.format(conditions=conditions), tuple(f"%{token}%" for token in tokens) + extra_params)
    return [dict(row) for row in cursor.fetchall()]


def _rank(item: dict, query: str, tokens: list[str]) -> tuple:
    title = item["title"].lower()
    normalized = query.lower()
    if title == normalized:
        relevance = 0
    elif title.startswith(normalized):
        relevance = 1
    elif all(token in title for token in tokens):
        relevance = 2
    elif any(token in title for token in tokens):
        relevance = 3
    else:
        relevance = 4
    return relevance, item["title"]


def _snippet(item: dict, tokens: list[str], limit: int = 150) -> str:
    text = re.sub(r"\s+", " ", item.pop("search_text", "") or "").strip()
    if not text:
        return ""
    lower = text.lower()
    positions = [lower.find(token) for token in tokens if lower.find(token) >= 0]
    start = max(0, (min(positions) if positions else 0) - 35)
    excerpt = text[start:start + limit].strip()
    return ("…" if start else "") + excerpt + ("…" if start + limit < len(text) else "")


def _search(query: str, kind: SearchKind, page: int, page_size: int, user_id: Optional[str]) -> dict:
    tokens = _tokens(query)
    if not tokens:
        return {"results": [], "total": 0, "query": query, "page": 1, "pages": 0, "facets": {}}

    results = []
    with get_db() as conn:
        cursor = conn.cursor()
        results += _search_rows(cursor, """
            SELECT DISTINCT ON (repo_name)
              repo_name AS title, COALESCE(language, 'GitHub') AS source,
              COALESCE(repo_url, '/insights/hotspots') AS url,
              'technical' AS type, COALESCE(description, '') AS search_text
            FROM github_trending WHERE {conditions}
            ORDER BY repo_name, scrape_date DESC, id DESC LIMIT 100
        """, "COALESCE(repo_name,'') || ' ' || COALESCE(description,'') || ' ' || COALESCE(language,'')", tokens)
        results += _search_rows(cursor, """
            SELECT title, category AS source, url, 'solution' AS type,
              COALESCE(summary,'') || ' ' || COALESCE(source_description,'') AS search_text
            FROM aliyun_solutions WHERE is_active=TRUE AND {conditions}
            ORDER BY menu_order LIMIT 100
        """, "COALESCE(title,'') || ' ' || COALESCE(category,'') || ' ' || COALESCE(summary,'') || ' ' || COALESCE(source_description,'')", tokens)
        results += _search_rows(cursor, """
            SELECT DISTINCT ON (vendor, title)
              title, vendor AS source, COALESCE(link, '/insights/competitors') AS url, 'competitor' AS type,
              COALESCE(summary,'') || ' ' || COALESCE(category,'') AS search_text
            FROM competitor_news WHERE {conditions}
            ORDER BY vendor, title, scrape_date DESC, id DESC LIMIT 100
        """, "COALESCE(title,'') || ' ' || COALESCE(vendor,'') || ' ' || COALESCE(summary,'') || ' ' || COALESCE(category,'')", tokens)
        if user_id:
            results += _search_rows(cursor, """
                SELECT title, priority || ' · ' || status AS source,
                  '/workbench/requirements/' || id AS url, 'requirement' AS type,
                  COALESCE(description,'') || ' ' || COALESCE(source_type,'') AS search_text
                FROM requirements WHERE {conditions} AND user_id=%s
                ORDER BY updated_at DESC LIMIT 100
            """, "COALESCE(title,'') || ' ' || COALESCE(description,'') || ' ' || COALESCE(source_type,'')", tokens, (user_id,))
            results += _search_rows(cursor, """
                SELECT name AS title, category || ' · ' || version AS source,
                  '/workbench/solutions/' || id AS url, 'managed_solution' AS type,
                  COALESCE(description,'') AS search_text
                FROM solutions WHERE {conditions} AND user_id=%s
                ORDER BY updated_at DESC LIMIT 100
            """, "COALESCE(name,'') || ' ' || COALESCE(description,'') || ' ' || COALESCE(category,'') || ' ' || COALESCE(version,'')", tokens, (user_id,))

    deduplicated = list({(item["type"], item.get("url") or item["title"]): item for item in results}.values())
    facets = dict(Counter(item["type"] for item in deduplicated))
    filtered = deduplicated if kind == "all" else [item for item in deduplicated if item["type"] == kind]
    filtered.sort(key=lambda item: _rank(item, query, tokens))
    for item in filtered:
        item["snippet"] = _snippet(item, tokens)
    total = len(filtered)
    start = (page - 1) * page_size
    return {
        "results": filtered[start:start + page_size],
        "total": total,
        "query": query,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "facets": facets,
    }


@router.get("/search")
async def global_search(
    q: str = Query("", min_length=1, max_length=100),
    kind: SearchKind = "all",
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    user=Depends(get_current_user),
):
    safe_q = re.sub(r"\s+", " ", q).strip()[:100]
    return await asyncio.to_thread(_search, safe_q, kind, page, page_size, str(user.id) if user else None)
