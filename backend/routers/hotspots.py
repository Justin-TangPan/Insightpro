"""Project insights routes — GitHub Trending"""
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta
from db import get_db
from routers.auth import require_auth, require_admin

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/agent-launches")
async def agent_launches():
    from services.agent_launch_service import MONITORED, snapshot
    from services.intelligence_format import application
    items, refreshing = snapshot()
    return {"items": [{**item, "intelligence": application(item)} for item in items],
            "vendors": MONITORED, "refreshing": refreshing}


@router.get("/agent-launches/progress")
async def agent_launches_progress(_=Depends(require_admin)):
    from services.agent_launch_service import analysis_progress
    return await asyncio.to_thread(analysis_progress)


# Import functions from original main.py (to be fully migrated to service later)
from main_legacy import (
    scrape_github_trending,
    refresh_and_store,
    evaluate_trending_business,
    _fetch_baidu_hotsearch_sync,
)

# Business logic migrated to service layer (fixing startup_service → router layering violation)
from services.hotspot_service import (
    _empty_eval_summary,
    _summarize_eval,
    _heuristic_score_project,
    _store_live_evaluations,
    _localize_evaluations,
    _canonical_evaluations,
)


@router.get("/github-trending")
async def get_github_trending(
    since: str = Query("daily", enum=["daily", "weekly", "monthly"]),
    date: Optional[str] = None,
):
    """Get GitHub Trending projects (prefer live, fallback to database)"""
    try:
        items = await asyncio.to_thread(scrape_github_trending, since=since)
        if items:
            now = datetime.now()
            try:
                with get_db() as conn:
                    c = conn.cursor()
                    for item in items:
                        c.execute("""
                            INSERT INTO github_trending
                            (scrape_date, scrape_time, repo_name, repo_url, description, language, stars, forks, today_stars, category)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (scrape_date, category, repo_name) DO NOTHING
                        """, (now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
                              item["repo_name"], item["repo_url"], item["description"],
                              item["language"], item["stars"], item["forks"],
                              item["today_stars"], item["category"]))
            except Exception as e:
                logger.warning("GitHub live data write to database failed, returning live results", exc_info=True)
            return {"items": items, "source": "live", "count": len(items), "date": now.strftime("%Y-%m-%d")}
    except Exception as e:
        logger.warning("GitHub live crawl failed, falling back to database", exc_info=True)

    target_date = date or datetime.now().strftime("%Y-%m-%d")
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT * FROM github_trending
                WHERE scrape_date = %s AND category = %s
                ORDER BY id
            """, (target_date, since))
            rows = c.fetchall()
    except Exception as e:
        logger.warning("GitHub database fallback read failed", exc_info=True)
        rows = []
    if rows:
        return {"items": [dict(r) for r in rows], "source": "database", "count": len(rows), "date": target_date}
    return {"items": [], "source": "empty", "count": 0, "date": target_date}


@router.get("/github-trending/history")
async def get_github_trending_history(
    days: int = Query(7, ge=1, le=90),
    category: str = Query("daily", enum=["daily", "weekly", "monthly"]),
    locale: str = Query("zh", enum=["zh", "en"]),
):
    """Query historical GitHub Trending records"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            c.execute("""
                SELECT DISTINCT scrape_date FROM github_trending
                WHERE scrape_date >= %s AND category = %s
                ORDER BY scrape_date DESC
            """, (cutoff, category))
            dates = [r["scrape_date"] for r in c.fetchall()]
            history = []
            for d in dates:
                c.execute("""
                    SELECT * FROM github_trending
                    WHERE scrape_date = %s AND category = %s
                    ORDER BY id LIMIT 25
                """, (d, category))
                rows = c.fetchall()
                c.execute("""
                    SELECT repo_name, repo_url, language, stars, summary, summary_zh, d1, d2, d3, d4,
                           total, level, recommendation, reasoning, eval_time
                    FROM trending_business_eval
                    WHERE scrape_date = %s
                    ORDER BY total DESC
                """, (d,))
                evaluations = _canonical_evaluations(c, [dict(r) for r in c.fetchall()]) if category == "daily" else []
                history.append({
                    "date": d,
                    "items": [dict(r) for r in rows],
                    "evaluations": await asyncio.to_thread(_localize_evaluations, [dict(r) for r in evaluations], locale),
                })
            return {"history": history, "total_dates": len(dates), "category": category}
    except Exception as e:
        logger.warning("GitHub history read failed", exc_info=True)
        return {"history": [], "total_dates": 0, "category": category}


@router.post("/github-trending/refresh")
async def manual_refresh(_=Depends(require_auth)):
    """Manually trigger GitHub Trending refresh"""
    try:
        await asyncio.to_thread(refresh_and_store)
        return {"status": "success", "message": "GitHub Trending data refreshed"}
    except Exception as e:
        items = await asyncio.to_thread(scrape_github_trending, since="daily")
        if items:
            return {"status": "partial_success", "message": f"Database write failed, retrieved {len(items)} live GitHub Trending items", "items": items}
        logger.exception("GitHub Trending refresh failed")
        raise HTTPException(status_code=500, detail="Refresh failed, please try again later")


@router.get("/github-trending/business-eval")
async def get_business_eval(date: Optional[str] = None, locale: str = Query("zh", enum=["zh", "en"])):
    """Get today's GitHub Trending business value evaluation results"""
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT repo_name, repo_url, language, stars, summary, summary_zh,
                       d1, d2, d3, d4, total, level, recommendation, reasoning, eval_time
                FROM trending_business_eval
                WHERE scrape_date = %s
                ORDER BY total DESC
            """, (target_date,))
            rows = c.fetchall()
            items = _canonical_evaluations(c, [dict(r) for r in rows])
        if items:
            return {"date": target_date, "items": await asyncio.to_thread(_localize_evaluations, items, locale), "count": len(items), "summary": _summarize_eval(items), "source": "database"}
    except Exception as e:
        logger.warning("Database read failed, trying live evaluation", exc_info=True)

    if date and target_date != datetime.now().strftime("%Y-%m-%d"):
        return {"date": target_date, "items": [], "count": 0, "summary": _empty_eval_summary(), "source": "empty_history"}

    live_items = await asyncio.to_thread(scrape_github_trending, since="daily")
    # The read path must remain fast and non-empty even when the AI provider is slow.
    # Manual refresh and the startup worker can upgrade these heuristic rows later.
    try:
        with get_db() as conn:
            shared = _canonical_evaluations(conn.cursor(), [dict(item) for item in live_items[:25]])
    except Exception:
        shared = live_items[:25]
    items = [item if item.get("analysis_id") else _heuristic_score_project(item) for item in shared]
    if items:
        try:
            await asyncio.to_thread(_store_live_evaluations, target_date, [item for item in items if not item.get("analysis_id")])
        except Exception as e:
            logger.warning("Live evaluation write failed, returning results", exc_info=True)
    return {"date": target_date, "items": await asyncio.to_thread(_localize_evaluations, items, locale), "count": len(items), "summary": _summarize_eval(items), "source": "live_heuristic"}


@router.post("/github-trending/business-eval/refresh")
async def refresh_business_eval(limit: int = Query(25, ge=1, le=25), locale: str = Query("zh", enum=["zh", "en"]), _=Depends(require_auth)):
    """Manually trigger GitHub Trending business value evaluation"""
    try:
        from services.task_service import run_task
        result = await asyncio.to_thread(run_task, "trending_business_eval_daily", "manual", lambda: evaluate_trending_business(limit))
    except Exception as e:
        logger.warning("Database evaluation refresh failed", exc_info=True)
        raise HTTPException(status_code=503, detail="Unable to verify existing project analysis; retry after storage recovers") from e
    if result.get("status") in {"success", "partial_success"}:
        date_str = result.get("date") or datetime.now().strftime("%Y-%m-%d")
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT repo_name, repo_url, language, stars, summary, summary_zh,
                           d1, d2, d3, d4, total, level, recommendation, reasoning, eval_time
                    FROM trending_business_eval
                    WHERE scrape_date = %s
                    ORDER BY total DESC
                """, (date_str,))
                items = _canonical_evaluations(c, [dict(r) for r in c.fetchall()])
            return {"status": result["status"], "date": date_str, "items": await asyncio.to_thread(_localize_evaluations, items, locale), "count": len(items), "summary": _summarize_eval(items), "source": "database"}
        except Exception as e:
            logger.warning("Evaluation completed but database read failed", exc_info=True)
    raise HTTPException(status_code=503, detail="AI evaluation unavailable; existing estimates remain available")


@router.get("/baidu-hotsearch")
async def get_baidu_hotsearch():
    """Fetch Baidu hot search in real-time"""
    return await asyncio.to_thread(_fetch_baidu_hotsearch_sync)
