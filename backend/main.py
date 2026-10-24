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
from pytz import timezone as tz

from settings import settings
from deep_searcher_integration import init_deep_searcher
from crawlers import init_crawler_tables

logger = logging.getLogger(__name__)

from routers import (
    auth, hotspots, solutions, competitors, reports, chat, crawling,
    analytics, search, dashboard, email, workbench, agent, community, tasks, intelligence_v2,
)


def schedule_jobs(scheduler: BackgroundScheduler):
    """注册所有定时任务"""
    from services.task_service import TASKS, load_source_schedules, run_task, task_trigger
    load_source_schedules()
    for task in TASKS:
        scheduler.add_job(
            run_task,
            task_trigger(task),
            args=[task.key],
            id=task.key,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=6 * 60 * 60,
            replace_existing=True,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    from services.startup_service import ensure_runtime_schema

    ensure_runtime_schema(absorb_requirements=settings.REQUIREMENT_ABSORPTION_ON_STARTUP)
    from services.task_service import recover_orphaned_runs
    recover_orphaned_runs()
    from services import embedding_config_service, runtime_config_service
    runtime_config_service.load()
    embedding_config_service.load()
    scheduler = None
    if settings.SCHEDULER_ENABLED:
        scheduler = BackgroundScheduler(timezone=tz("Asia/Shanghai"))
        schedule_jobs(scheduler)
        scheduler.start()
        logger.info("定时任务调度器已启动")
    app.state.scheduler = scheduler
    try:
        init_deep_searcher()
        logger.info("Context search initialized")
    except Exception as e:
        logger.warning("Context search init failed: %s", e)
    init_crawler_tables()
    if settings.STARTUP_CATCHUP_ENABLED and settings.SCHEDULER_ENABLED:
        from services.startup_service import run_startup_catchup
        threading.Thread(
            target=run_startup_catchup,
            name="insight-startup-catchup",
            daemon=True,
        ).start()
        logger.info("startup catch-up thread started")
    yield
    if scheduler:
        scheduler.shutdown()


app = FastAPI(title="InsightPro API", version=settings.APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

from middleware.error_handler import SanitizingErrorHandler
app.add_middleware(SanitizingErrorHandler)

app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(hotspots.router, prefix="/api", tags=["Hotspots"])
app.include_router(solutions.router, prefix="/api", tags=["Solutions"])
app.include_router(competitors.router, prefix="/api", tags=["Competitors"])
app.include_router(community.router, prefix="/api", tags=["Community"])
app.include_router(reports.router, prefix="/api", tags=["Reports"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(crawling.router, prefix="/api", tags=["Crawling"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])
app.include_router(search.router, prefix="/api", tags=["Search"])
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
app.include_router(email.router, prefix="/api", tags=["Email"])
app.include_router(workbench.router, prefix="/api", tags=["Workbench"])
app.include_router(agent.router, prefix="/api", tags=["Insight-Agent"])
app.include_router(tasks.router, prefix="/api", tags=["Tasks"])
app.include_router(intelligence_v2.router, prefix="/api/v2", tags=["Intelligence V2"])


@app.get("/")
async def root():
    return {"message": "InsightPro API is running", "version": settings.APP_VERSION}


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
