"""
Business Insights API — 路由注册入口
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone as tz

from settings import settings
from deep_searcher_integration import init_deep_searcher
from crawlers import init_crawler_tables

from routers import (
    auth, hotspots, solutions, competitors, reports, chat, crawling,
    analytics, search, dashboard, email, workbench, agent,
)


def schedule_jobs(scheduler: BackgroundScheduler):
    """注册所有定时任务"""
    from crawlers import run_daily_crawl
    from services.email_service import send_scheduled_digests
    from services.aliyun_solution_service import refresh_solution_catalogs
    from main_legacy import (
        refresh_and_store, refresh_competitor_news,
        evaluate_trending_business, generate_project_summaries, cleanup_old_data,
    )
    jobs = [
        (refresh_and_store, 9, 0, "github_daily"),
        (refresh_solution_catalogs, 9, 0, "solution_catalogs_daily"),
        (run_daily_crawl, 9, 0, "daily_crawl"),
        (refresh_competitor_news, 9, 2, "competitor_daily"),
        (evaluate_trending_business, 9, 3, "trending_business_eval_daily"),
        (generate_project_summaries, 9, 4, "project_summaries_daily"),
        (cleanup_old_data, 3, 0, "cleanup"),
    ]
    for fn, h, m, jid in jobs:
        scheduler.add_job(
            fn,
            CronTrigger(hour=h, minute=m, timezone=tz("Asia/Shanghai")),
            id=jid,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=6 * 60 * 60,
            replace_existing=True,
        )
    # ponytail: one scheduler matches the current single-API deployment; add a DB lease before running replicas.
    scheduler.add_job(
        send_scheduled_digests,
        CronTrigger(minute="*", second=0, timezone=tz("Asia/Shanghai")),
        id="scheduled_email",
        coalesce=True,
        max_instances=1,
        replace_existing=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    from services.startup_service import ensure_runtime_schema

    ensure_runtime_schema()
    scheduler = BackgroundScheduler(timezone=tz("Asia/Shanghai"))
    schedule_jobs(scheduler)
    scheduler.start()
    print("[OK] 定时任务调度器已启动")
    try:
        init_deep_searcher()
        print("[OK] Context search initialized")
    except Exception as e:
        print(f"[WARN] Context search init failed: {e}")
    init_crawler_tables()
    if settings.STARTUP_CATCHUP_ENABLED:
        from services.startup_service import run_startup_catchup
        threading.Thread(
            target=run_startup_catchup,
            name="insight-startup-catchup",
            daemon=True,
        ).start()
        logging.getLogger(__name__).info("startup catch-up thread started")
    yield
    scheduler.shutdown()


app = FastAPI(title="InsightPro API", version="0.8.5", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(hotspots.router, prefix="/api", tags=["Hotspots"])
app.include_router(solutions.router, prefix="/api", tags=["Solutions"])
app.include_router(competitors.router, prefix="/api", tags=["Competitors"])
app.include_router(reports.router, prefix="/api", tags=["Reports"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(crawling.router, prefix="/api", tags=["Crawling"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])
app.include_router(search.router, prefix="/api", tags=["Search"])
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
app.include_router(email.router, prefix="/api", tags=["Email"])
app.include_router(workbench.router, prefix="/api", tags=["Workbench"])
app.include_router(agent.router, prefix="/api", tags=["Insight-Agent"])


@app.get("/")
async def root():
    return {"message": "InsightPro API is running", "version": "0.8.5"}


@app.get("/api/system/health/live")
async def liveness():
    """Process liveness probe; intentionally has no external dependencies."""
    return {"status": "alive"}


@app.get("/api/system/health/ready")
async def readiness():
    """Production readiness for database, freshness, and technical hotspots."""
    from services.system_health_service import get_readiness_report

    report = await asyncio.to_thread(get_readiness_report)
    return JSONResponse(
        status_code=200 if report["status"] == "healthy" else 503,
        content=report,
    )
