"""行业新闻与解决方案洞察路由。"""
import asyncio
from fastapi import APIRouter, Depends, Query
from typing import Optional
from crawlers import get_cloud_vendor_news, get_industry_news
from routers.auth import require_auth
from services.aliyun_solution_service import get_aliyun_solutions, refresh_aliyun_solutions

router = APIRouter()


@router.get("/industry-news")
async def industry_news(
    days: int = Query(7, ge=1, le=90),
    source: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """获取行业新闻（36氪/财联社/第一财经/AI产业）"""
    items = get_industry_news(days=days, source=source, limit=limit)
    return {"items": items, "count": len(items)}


@router.get("/industry-partnerships")
async def industry_partnerships(days: int = Query(30, ge=1, le=90), limit: int = Query(8, ge=1, le=50)):
    """获取云厂商客户与生态合作动态。"""
    keywords = ("合作", "携手", "联合", "签约", "客户", "案例", "伙伴", "customer", "case study", "partner")
    items = [
        item for item in get_cloud_vendor_news(days=days, limit=200)
        if item.get("vendor") != "华为云" and (
            item.get("category") == "合作案例" or any(word in item.get("title", "").lower() for word in keywords)
        )
    ][:limit]
    return {"items": items, "count": len(items)}


@router.get("/solutions/aliyun")
async def aliyun_solutions():
    """获取阿里云技术解决方案，最近新增或变更项优先。"""
    return await asyncio.to_thread(get_aliyun_solutions)


@router.post("/solutions/aliyun/refresh")
async def refresh_solutions(_=Depends(require_auth)):
    """手动检查阿里云解决方案更新。"""
    return await asyncio.to_thread(refresh_aliyun_solutions)
