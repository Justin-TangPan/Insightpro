"""Global search across public insights and the signed-in user's workbench."""
from __future__ import annotations

import asyncio
import re
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from db import get_db
from routers.auth import get_current_user

router = APIRouter()
SearchKind = Literal["all", "technical", "solution", "competitor", "ai_application", "community", "requirement", "managed_solution"]


def _tokens(query: str) -> list[str]:
    return list(dict.fromkeys(part.lower() for part in re.findall(r"[\w\-./]+", query, re.UNICODE) if part))[:8]


def _snippet(item: dict, tokens: list[str], limit: int = 150) -> str:
    text = re.sub(r"\s+", " ", item.pop("search_text", "") or "").strip()
    if not text:
        return ""
    lower = text.lower()
    positions = [lower.find(token) for token in tokens if lower.find(token) >= 0]
    start = max(0, (min(positions) if positions else 0) - 35)
    excerpt = text[start:start + limit].strip()
    return ("…" if start else "") + excerpt + ("…" if start + limit < len(text) else "")


def _search(query: str, kind: SearchKind, page: int, page_size: int, user_id: Optional[str], date_from: str | None = None, date_to: str | None = None) -> dict:
    tokens = _tokens(query)
    if not tokens:
        return {"results": [], "total": 0, "query": query, "page": 1, "pages": 0, "facets": {}}

    workbench = ""
    params: list = []
    if user_id:
        workbench = """
        UNION ALL
        SELECT 'requirement', title, priority || ' · ' || status, '/workbench/requirements/' || id,
               updated_at::date::text, 'updated', id::text,
               title || ' ' || description || ' ' || source_type
        FROM requirements WHERE user_id=%s
        UNION ALL
        SELECT 'managed_solution', name, COALESCE(category,'') || ' · ' || COALESCE(version,''), '/workbench/solutions/' || id,
               updated_at::date::text, 'updated', id::text,
               name || ' ' || description || ' ' || category || ' ' || version
        FROM solutions WHERE user_id=%s
        """
        params.extend([user_id, user_id])

    sql = f"""
        WITH projects AS (
            SELECT DISTINCT ON (repo_name) repo_name, repo_url, description, language, scrape_date
            FROM github_trending ORDER BY repo_name, scrape_date DESC, id DESC
        ),
        competitors AS (
            SELECT DISTINCT ON (vendor, title) vendor, title, link AS url, summary, category, published_date, scrape_date
            FROM competitor_news ORDER BY vendor, title, scrape_date DESC, id DESC
        ),
        items(item_type, title, source, url, item_date, date_basis, item_key, search_text) AS (
            SELECT 'technical', repo_name, COALESCE(language, 'GitHub'), COALESCE(repo_url, '/insights/hotspots'),
                   scrape_date, 'observed', repo_name,
                   COALESCE(repo_name,'') || ' ' || COALESCE(description,'') || ' ' || COALESCE(language,'')
            FROM projects
            UNION ALL
            SELECT 'solution', title, vendor || ' · ' || category, url, last_changed_date, 'changed', url,
                   COALESCE(title,'') || ' ' || COALESCE(vendor,'') || ' ' || COALESCE(category,'') || ' '
                   || COALESCE(summary,'') || ' ' || COALESCE(source_description,'') || ' ' || COALESCE(change_summary,'')
            FROM aliyun_solutions WHERE is_active=TRUE
            UNION ALL
            SELECT 'competitor', title, vendor, COALESCE(url, '/insights/competitors'),
                   COALESCE(published_date::text, scrape_date),
                   CASE WHEN published_date IS NULL THEN 'observed' ELSE 'published' END,
                   COALESCE(url, vendor || ':' || title),
                   COALESCE(title,'') || ' ' || COALESCE(vendor,'') || ' ' || COALESCE(summary,'') || ' ' || COALESCE(category,'')
            FROM competitors
            UNION ALL
            SELECT 'ai_application', COALESCE(NULLIF(name,''), vendor), vendor, url,
                   CASE WHEN published_at ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}' THEN LEFT(published_at, 10)
                        ELSE source_fetched_at::date::text END,
                   CASE WHEN published_at ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}' THEN 'published' ELSE 'observed' END,
                   vendor || ':' || url,
                   COALESCE(name,'') || ' ' || COALESCE(vendor,'') || ' ' || COALESCE(category,'') || ' '
                   || COALESCE(summary,'') || ' ' || COALESCE(capability,'') || ' '
                   || COALESCE(opportunity,'') || ' ' || COALESCE(limitation,'') || ' ' || COALESCE(source_text,'')
            FROM vendor_ai_applications WHERE kind <> 'product'
            UNION ALL
            SELECT CASE WHEN 'technology_ecosystem'=ANY(v2_event.business_scopes) THEN 'technical'
                        WHEN 'ai_applications'=ANY(v2_event.business_scopes) THEN 'ai_application'
                        WHEN 'solutions'=ANY(v2_event.business_scopes) THEN 'solution'
                        WHEN 'competitor_dynamics'=ANY(v2_event.business_scopes) THEN 'competitor'
                        ELSE 'community' END,
                   v2_event.title, COALESCE(entity.metadata->>'vendor',
                       (SELECT string_agg(DISTINCT source_ref.name, ' · ')
                        FROM intelligence_event_evidence evidence_ref
                        JOIN intelligence_raw_items raw_ref ON raw_ref.id=evidence_ref.raw_item_id
                        JOIN intelligence_sources source_ref ON source_ref.source_key=raw_ref.source_key
                        WHERE evidence_ref.event_id=v2_event.id), 'Insight-Pro'), '/events/' || v2_event.id,
                   COALESCE(v2_event.published_at,v2_event.last_seen_at)::date::text,
                   CASE WHEN v2_event.published_at IS NULL THEN 'observed' ELSE 'published' END,
                   'v2:' || v2_event.id, v2_event.title || ' ' || COALESCE(v2_event.summary,'') || ' '
                   || COALESCE(entity.canonical_name,'') || ' ' || COALESCE(entity.metadata::text,'') || ' '
                   || COALESCE((SELECT string_agg(raw.title || ' ' || raw.content::text, ' ')
                                FROM intelligence_event_evidence evidence
                                JOIN intelligence_raw_items raw ON raw.id=evidence.raw_item_id
                                WHERE evidence.event_id=v2_event.id), '')
            FROM intelligence_events v2_event
            LEFT JOIN intelligence_entities entity ON entity.entity_key=v2_event.entity_key
            WHERE v2_event.status='active' AND v2_event.business_scopes &&
                  ARRAY['technology_ecosystem','ai_applications','solutions','competitor_dynamics','community_insights']::text[]
            {workbench}
        ),
        compatible AS (
            SELECT * FROM items item
            WHERE left(item.item_key, 3) = 'v2:' OR item.item_type IN ('requirement','managed_solution')
               OR NOT EXISTS (
                   SELECT 1 FROM intelligence_events v2_event
                   JOIN intelligence_event_evidence evidence ON evidence.event_id=v2_event.id
                   JOIN intelligence_raw_items raw ON raw.id=evidence.raw_item_id
                   WHERE v2_event.status='active'
                     AND CASE item.item_type WHEN 'technical' THEN 'technology_ecosystem'
                          WHEN 'solution' THEN 'solutions' WHEN 'competitor' THEN 'competitor_dynamics'
                          WHEN 'ai_application' THEN 'ai_applications' ELSE '' END=ANY(v2_event.business_scopes)
                     AND (raw.canonical_url=item.url OR lower(v2_event.title)=lower(item.title))
               )
        ),
        matched AS (
            SELECT * FROM compatible i
            WHERE NOT EXISTS (
                SELECT 1 FROM unnest(%s::text[]) AS tokens(token)
                WHERE strpos(lower(COALESCE(i.search_text,'')), tokens.token) = 0
            )
        ),
        scoped AS (
            SELECT * FROM matched
            WHERE (%s::text IS NULL OR COALESCE(item_date,'') >= %s)
              AND (%s::text IS NULL OR COALESCE(item_date,'') <= %s)
        ),
        ranked AS (
            SELECT *, CASE
                WHEN lower(title) = lower(%s) THEN 0
                WHEN left(lower(title), length(%s)) = lower(%s) THEN 1
                WHEN NOT EXISTS (SELECT 1 FROM unnest(%s::text[]) AS tokens(token) WHERE strpos(lower(title), tokens.token) = 0) THEN 2
                WHEN EXISTS (SELECT 1 FROM unnest(%s::text[]) AS tokens(token) WHERE strpos(lower(title), tokens.token) > 0) THEN 3
                WHEN NOT EXISTS (SELECT 1 FROM unnest(%s::text[]) AS tokens(token) WHERE strpos(lower(COALESCE(source,'')), tokens.token) = 0) THEN 4
                ELSE 5 END AS relevance
            FROM scoped
        ),
        stats AS (
            SELECT count(*) FILTER (WHERE item_type='technical') AS technical,
                   count(*) FILTER (WHERE item_type='solution') AS solution,
                   count(*) FILTER (WHERE item_type='competitor') AS competitor,
                   count(*) FILTER (WHERE item_type='ai_application') AS ai_application,
                   count(*) FILTER (WHERE item_type='community') AS community,
                   count(*) FILTER (WHERE item_type='requirement') AS requirement,
                   count(*) FILTER (WHERE item_type='managed_solution') AS managed_solution
            FROM ranked
        ),
        filtered AS (
            SELECT * FROM ranked WHERE (%s='all' OR item_type=%s)
        ),
        page_rows AS (
            SELECT * FROM filtered
            ORDER BY relevance, item_date DESC NULLS LAST, item_type, item_key
            LIMIT %s OFFSET %s
        )
        SELECT p.*, (SELECT count(*) FROM filtered) AS total,
               s.technical, s.solution, s.competitor, s.ai_application, s.requirement, s.managed_solution
        FROM stats s LEFT JOIN page_rows p ON TRUE
    """
    params.extend([
        tokens, date_from, date_from, date_to, date_to,
        query, query, query, tokens, tokens, tokens,
        kind, kind, page_size, (page - 1) * page_size,
    ])
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        rows = [dict(row) for row in cursor.fetchall()]

    first = rows[0] if rows else {}
    results = []
    for row in rows:
        if not row.get("item_type"):
            continue
        item = {
            "type": row["item_type"], "title": row["title"], "source": row["source"],
            "url": row["url"], "date": row["item_date"], "date_basis": row["date_basis"],
            "search_text": row["search_text"],
        }
        item["snippet"] = _snippet(item, tokens)
        results.append(item)

    total = int(first.get("total") or 0)
    facets = {key: int(first.get(key) or 0) for key in (
        "technical", "solution", "competitor", "ai_application", "community", "requirement", "managed_solution",
    )}
    return {
        "results": results, "total": total, "query": query, "page": page,
        "page_size": page_size, "pages": (total + page_size - 1) // page_size, "facets": facets,
    }


@router.get("/search")
async def global_search(
    q: str = Query("", min_length=1, max_length=100),
    kind: SearchKind = "all",
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    user=Depends(get_current_user),
):
    safe_q = re.sub(r"\s+", " ", q).strip()[:100]
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must be on or before date_to")
    return await asyncio.to_thread(
        _search, safe_q, kind, page, page_size, str(user.id) if user else None,
        date_from.isoformat() if date_from else None, date_to.isoformat() if date_to else None,
    )
