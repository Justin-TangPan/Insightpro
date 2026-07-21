"""政策法规路由"""
from fastapi import APIRouter, Query
from typing import Optional
from crawlers import get_policy_updates

router = APIRouter()


@router.get("/policy/list")
async def policy_list(
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
):
    """获取政策法规列表"""
    items = get_policy_updates(days=days, limit=limit)
    return {"items": items, "count": len(items)}


@router.get("/cloud-vendors")
async def cloud_vendors(
    days: int = Query(7, ge=1, le=90),
    vendor: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """获取云厂商最新动态"""
    from crawlers import get_cloud_vendor_news
    items = get_cloud_vendor_news(days=days, vendor=vendor, limit=limit)
    return {"items": items, "count": len(items)}
