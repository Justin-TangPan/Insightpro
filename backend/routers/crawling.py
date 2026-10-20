"""Crawler control routes"""
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException
from db import get_db
from routers.auth import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/crawl/trigger")
async def trigger_crawl(_=Depends(require_auth)):
    try:
        from services.task_service import run_task
        stats = await asyncio.to_thread(run_task, "daily_crawl", "manual")
        return {"status": "success", "message": "Crawl completed", "stats": stats}
    except Exception as e:
        logger.exception("Crawl failed")
        raise HTTPException(status_code=500, detail="Crawl failed, please try again later")


@router.get("/crawl/status")
async def crawl_status(_=Depends(require_auth)):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM scrape_log ORDER BY id DESC LIMIT 10")
        logs = [dict(r) for r in c.fetchall()]
    return {"logs": logs}


@router.get("/crawl/health")
async def crawl_health():
    try:
        from crawlers import crawler_monitor
        return crawler_monitor.health_report()
    except Exception:
        return {"status": "unavailable"}


@router.get("/data/freshness")
async def data_freshness():
    from services.freshness_service import get_freshness_report
    return await asyncio.to_thread(get_freshness_report)
