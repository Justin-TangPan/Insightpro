"""数据大屏路由"""
from fastapi import APIRouter
from crawlers import get_homepage_stats

router = APIRouter()


@router.get("/dashboard/stats")
async def get_dashboard_stats():
    db_stats = get_homepage_stats()
    return {
        "kpis": [
            {"label": "GitHub 热点", "value": str(db_stats.get("trending_today", 0)), "trend": "今日"},
            {"label": "AI 价值评估", "value": str(db_stats.get("evaluation_today", 0)), "trend": "今日"},
            {"label": "解决方案", "value": str(db_stats.get("solution_count", 0)), "trend": "当前"},
            {"label": "方案变化", "value": str(db_stats.get("solution_recent_count", 0)), "trend": "近 7 日"},
        ],
        "serviceHealth": [
            {"service": "爬虫服务", "status": "healthy" if db_stats.get("last_crawl") else "unknown", "uptime": "N/A"},
            {"service": "数据库", "status": "healthy", "uptime": "运行中"},
            {"service": "API 服务", "status": "healthy", "uptime": "运行中"},
        ],
        "date": __import__('datetime').datetime.now().strftime("%Y-%m-%d"),
        "source": "database",
    }


@router.get("/homepage/stats")
async def homepage_stats():
    return get_homepage_stats()


@router.get("/homepage/modules")
async def homepage_modules():
    from crawlers import get_homepage_modules
    from datetime import datetime
    return [{**module, "as_of": datetime.now().isoformat(timespec="minutes"), "status": "fresh" if module.get("items") else "empty"} for module in get_homepage_modules()]
