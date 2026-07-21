"""页面埋点分析路由"""
from fastapi import APIRouter, Depends, Query, Request
from routers.auth import require_auth
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from db import get_db

router = APIRouter()


class TrackRequest(BaseModel):
    page: str
    visitor_id: Optional[str] = ""
    user_agent: Optional[str] = ""


def record_visit(page_path: str, visitor_id: str, user_agent: str = "", referrer: str = ""):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO page_visits (page_path, visitor_id, user_agent, referrer) VALUES (%s, %s, %s, %s)",
                  (page_path, visitor_id, user_agent, referrer))


def get_analytics(days: int = 7) -> dict:
    with get_db() as conn:
        c = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("SELECT (created_at AT TIME ZONE 'Asia/Shanghai')::date AS date, COUNT(*) AS pv, COUNT(DISTINCT visitor_id) AS uv FROM page_visits WHERE (created_at AT TIME ZONE 'Asia/Shanghai')::date >= %s::date GROUP BY date ORDER BY date", (cutoff,))
        daily_stats = [dict(r) for r in c.fetchall()]
        c.execute("SELECT page_path, COUNT(*) AS pv, COUNT(DISTINCT visitor_id) AS uv FROM page_visits WHERE (created_at AT TIME ZONE 'Asia/Shanghai')::date >= %s::date GROUP BY page_path ORDER BY pv DESC", (cutoff,))
        page_stats = [dict(r) for r in c.fetchall()]
        c.execute("SELECT COUNT(*) AS cnt FROM page_visits WHERE (created_at AT TIME ZONE 'Asia/Shanghai')::date = %s::date", (today,))
        today_pv = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(DISTINCT visitor_id) AS cnt FROM page_visits WHERE (created_at AT TIME ZONE 'Asia/Shanghai')::date = %s::date", (today,))
        today_uv = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) AS cnt FROM page_visits")
        total_pv = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(DISTINCT visitor_id) AS cnt FROM page_visits")
        total_uv = c.fetchone()["cnt"]
        return {"today": {"pv": today_pv, "uv": today_uv}, "total": {"pv": total_pv, "uv": total_uv}, "daily": daily_stats, "pages": page_stats}


@router.post("/track")
async def track_visit(req: TrackRequest, request: Request):
    visitor_id = req.visitor_id or (request.client.host if request.client else "unknown")
    ua = req.user_agent or request.headers.get("user-agent", "")
    ref = request.headers.get("referer", "")
    record_visit(req.page, visitor_id, ua, ref)
    return {"status": "ok"}


@router.get("/analytics")
async def analytics_endpoint(days: int = Query(7, ge=1, le=90), _=Depends(require_auth)):
    return get_analytics(days)


@router.post("/track/batch")
async def track_batch(visits: List[TrackRequest], request: Request):
    client_ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    for v in visits:
        vid = v.visitor_id or client_ip
        record_visit(v.page, vid, v.user_agent or ua, "")
    return {"status": "ok", "count": len(visits)}
