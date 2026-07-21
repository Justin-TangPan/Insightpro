"""招标信息路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from routers.auth import require_auth
from typing import Optional

from services.bidding_service import (
    get_bidding_opportunities, get_bidding_stats,
    collect_bidding_data, analyze_bidding,
)

router = APIRouter()


@router.get("/bidding/list")
async def bidding_list(
    industry: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=90),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    items, total = get_bidding_opportunities(
        industry=industry, status=status, days=days,
        page=page, page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return {
        "items": items, "count": len(items),
        "total": total, "page": page,
        "page_size": page_size, "total_pages": total_pages,
    }


@router.get("/bidding/stats")
async def bidding_stats():
    return get_bidding_stats()


@router.post("/bidding/refresh")
async def refresh_bidding(_=Depends(require_auth)):
    try:
        count = collect_bidding_data()
        return {"status": "success", "message": f"已采集 {count} 条", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bidding/analyze")
async def bidding_analyze(_=Depends(require_auth)):
    return analyze_bidding()
