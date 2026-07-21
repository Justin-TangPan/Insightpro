import os, json, sys

base = os.path.dirname(os.path.abspath(__file__))

def w(fname, content):
    path = os.path.join(base, fname)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'W: {fname}')

# main.py
w('main.py', """\"\"\"
Business Insights API - routing registration entry
\"\"\"
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone as tz

from settings import settings
from deep_searcher_integration import init_deep_searcher
from crawlers import init_crawler_tables

from routers import (
    auth, insights, industry, hotspots, competitors,
    bidding, demand, policy, reports, chat, crawling,
    analytics, search, dashboard, email,
)


def schedule_jobs(scheduler):
    from crawlers import run_daily_crawl
    from services.bidding_service import collect_bidding_data
    from services.demand_service import collect_demand_signals
    from services.email_service import send_daily_digest
    from main_legacy import (
        refresh_and_store, refresh_competitor_news,
        evaluate_trending_business, cleanup_old_data,
    )
    jobs = [
        (collect_demand_signals, 8, 0, "demand_daily"),
        (collect_bidding_data, 8, 30, "bidding_daily"),
        (refresh_and_store, 9, 0, "github_daily"),
        (run_daily_crawl, 9, 0, "daily_crawl"),
        (refresh_competitor_news, 9, 2, "competitor_daily"),
        (evaluate_trending_business, 9, 3, "trending_business_eval_daily"),
        (send_daily_digest, 9, 5, "daily_email"),
        (cleanup_old_data, 3, 0, "cleanup"),
    ]
    for fn, h, m, jid in jobs:
        scheduler.add_job(fn, CronTrigger(hour=h, minute=m, timezone=tz("Asia/Shanghai")), id=jid)


@asynccontextmanager
async def lifespan(app):
    scheduler = BackgroundScheduler()
    schedule_jobs(scheduler)
    scheduler.start()
    print("[OK] Scheduled tasks started")
    try:
        init_deep_searcher()
        print("[OK] DeepSearcher initialized")
    except Exception as e:
        print(f"[WARN] DeepSearcher init failed: {e}")
    init_crawler_tables()
    yield
    scheduler.shutdown()


app = FastAPI(title="InsightPro API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://localhost:3001",
        "http://127.0.0.1:3000",
        f"http://{settings.PUBLIC_IP}:3000",
        f"http://{settings.PUBLIC_IP}:3001",
        "http://94.74.90.21:3000",
    ],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(insights.router, prefix="/api", tags=["Insights"])
app.include_router(industry.router, prefix="/api", tags=["Industry"])
app.include_router(hotspots.router, prefix="/api", tags=["Hotspots"])
app.include_router(competitors.router, prefix="/api", tags=["Competitors"])
app.include_router(bidding.router, prefix="/api", tags=["Bidding"])
app.include_router(demand.router, prefix="/api", tags=["Demand"])
app.include_router(policy.router, prefix="/api", tags=["Policy"])
app.include_router(reports.router, prefix="/api", tags=["Reports"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(crawling.router, prefix="/api", tags=["Crawling"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])
app.include_router(search.router, prefix="/api", tags=["Search"])
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
app.include_router(email.router, prefix="/api", tags=["Email"])


@app.get("/")
async def root():
    return {"message": "InsightPro API is running", "version": "2.0"}
""")

print('Done')
