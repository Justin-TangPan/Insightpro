"""Community insight routes."""
import asyncio

from fastapi import APIRouter, Depends

from routers.auth import require_auth
from services.community_insight_service import get_community_insights

router = APIRouter()


@router.get("/community/insights")
async def community_insights():
    return await asyncio.to_thread(get_community_insights)


@router.post("/community/insights/refresh")
async def refresh_community_insights(_=Depends(require_auth)):
    return await asyncio.to_thread(get_community_insights, True)


@router.get("/community/insights/history")
async def community_insight_history():
    from services.insight_dashboard_service import history
    return await asyncio.to_thread(history, "community")
