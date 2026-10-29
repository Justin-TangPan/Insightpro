"""
Business Insights API — 路由注册入口
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
import hmac
import threading
from datetime import datetime
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
    from services.task_service import TASKS, daily_brief_schedule_enabled, load_source_schedules, run_task, task_trigger
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
        if task.key == "daily_ai_brief" and not daily_brief_schedule_enabled():
            scheduler.pause_job(task.key)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.STARTUP_SCHEMA_ENABLED:
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
    if settings.STARTUP_SCHEMA_ENABLED:
        init_crawler_tables()
    if settings.SCHEDULER_ENABLED:
        from services.page_snapshot_service import bootstrap_page_snapshots_sync
        threading.Thread(target=bootstrap_page_snapshots_sync, name="insight-page-snapshot-startup", daemon=True).start()
    if settings.STARTUP_CATCHUP_ENABLED and settings.SCHEDULER_ENABLED and datetime.now(tz("Asia/Shanghai")).hour >= 8:
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


@app.middleware("http")
async def published_page_reads(request, call_next):
    from services.page_snapshot_service import BUILDING, PATH_TO_PAGE, get_page_snapshot
    path = request.url.path + ("?" + request.url.query if request.url.query else "")
    if request.method == "GET" and path in PATH_TO_PAGE and not BUILDING.get():
        snapshot = await asyncio.to_thread(get_page_snapshot, path)
        if snapshot:
            return JSONResponse(snapshot["content"], headers={"X-Page-Snapshot-Date": snapshot["snapshot_date"].isoformat(),
                                                             "X-Page-Snapshot-Id": str(snapshot["id"])})
        return JSONResponse({"detail": "Daily page snapshot is being prepared"}, status_code=503)
    response = await call_next(request)
    if request.method == "POST" and response.status_code < 400 and request.url.path in {
        "/api/github-trending/refresh", "/api/github-trending/business-eval/refresh",
        "/api/solutions/catalog/refresh", "/api/solutions/aliyun/refresh",
        "/api/community/insights/refresh", "/api/competitors/refresh",
    }:
        try:
            from services.page_snapshot_service import publish_page_snapshots
            await publish_page_snapshots()
        except Exception:
            logger.exception("Could not publish refreshed page snapshots")
    return response


@app.get("/api/pages/{page}/latest")
async def latest_page_snapshot(page: str):
    from services.page_snapshot_service import PAGE_PATHS, get_page_snapshot
    if page not in PAGE_PATHS:
        return JSONResponse({"detail": "Unknown page"}, status_code=404)
    snapshots = {path: await asyncio.to_thread(get_page_snapshot, path) for path in PAGE_PATHS[page]}
    if any(row is None for row in snapshots.values()):
        return JSONResponse({"detail": "Daily page snapshot is being prepared"}, status_code=503)
    return {"date": max(row["snapshot_date"] for row in snapshots.values()),
            "content": {path: row["content"] for path, row in snapshots.items()}}


@app.middleware("http")
async def admin_api_guard(request, call_next):
    from services.page_snapshot_service import PATH_TO_PAGE

    path = request.url.path
    public = {"/api/system/health/live", "/api/system/health/ready", "/api/auth/login", "/api/auth/agent/callback", "/api/auth/agent/verify"}
    if path in {"/api/auth/register", "/api/auth/users/test", "/api/industry-news", "/api/policy/list", "/api/bidding/list", "/api/demand/signals"}:
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    full_path = path + ("?" + request.url.query if request.url.query else "")
    internal_snapshot = bool(settings.HERMES_SSO_SECRET) and full_path in PATH_TO_PAGE and hmac.compare_digest(request.headers.get("x-insight-internal-key", ""), settings.HERMES_SSO_SECRET)
    public_brief_read = path == "/api/daily-ai-brief" and request.method == "GET"
    # Snapshot paths are served by the published_page_reads middleware from the
    # daily page_snapshots cache and must stay anonymously readable for the
    # public frontend; otherwise the guard would 401 them before the cache.
    snapshot_path = full_path in PATH_TO_PAGE
    if path.startswith("/api/") and path not in public and not public_brief_read and not internal_snapshot and not snapshot_path and request.method != "OPTIONS" and auth.require_admin not in request.app.dependency_overrides:
        header = request.headers.get("authorization", "")
        if not header.startswith("Bearer ") or not auth.supabase:
            return JSONResponse({"detail": "Administrator login required"}, status_code=401)
        try:
            account = auth.supabase.auth.get_user(header[7:]).user
        except Exception:
            return JSONResponse({"detail": "Login expired"}, status_code=401)
        if not auth._is_internal_member(account):
            return JSONResponse({"detail": "Administrator access required"}, status_code=401)
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


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
