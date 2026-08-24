"""Idempotent startup catch-up for jobs missed while the API was offline."""
import logging
from datetime import datetime

from db import get_db
from services.freshness_service import has_rows_today

logger = logging.getLogger(__name__)
_LOCK_ID = 2_026_071_300


def ensure_runtime_schema() -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "ALTER TABLE trending_business_eval ADD COLUMN IF NOT EXISTS summary TEXT"
        )
        cursor.execute(
            "ALTER TABLE email_subscribers ADD COLUMN IF NOT EXISTS weekdays INTEGER[] NOT NULL DEFAULT ARRAY[0,1,2,3,4,5,6]"
        )
        cursor.execute(
            "ALTER TABLE email_subscribers ADD COLUMN IF NOT EXISTS send_time TEXT NOT NULL DEFAULT '09:05'"
        )
        cursor.execute(
            "ALTER TABLE email_subscribers ADD COLUMN IF NOT EXISTS last_sent_at TIMESTAMPTZ"
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS aliyun_solutions (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                source_description TEXT,
                summary TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                first_seen_date TEXT NOT NULL,
                last_seen_date TEXT NOT NULL,
                last_changed_date TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_aliyun_solutions_seen ON aliyun_solutions(last_seen_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_aliyun_solutions_changed ON aliyun_solutions(last_changed_date DESC)")


def _technical_summaries_missing() -> bool:
    today = datetime.now().strftime("%Y-%m-%d")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT EXISTS (
              SELECT 1
              FROM github_trending g
              LEFT JOIN trending_business_eval e
                ON e.scrape_date = g.scrape_date AND e.repo_name = g.repo_name
              WHERE g.scrape_date = %s AND g.category = 'daily'
                AND CHAR_LENGTH(COALESCE(e.summary, '')) < 100
            ) AS missing
            """,
            (today,),
        )
        return cursor.fetchone()["missing"]


def _run_if_missing(dataset: str, job_name: str, function) -> bool:
    if has_rows_today(dataset):
        logger.info("startup catch-up skip: %s is already fresh", dataset)
        return False
    logger.warning("startup catch-up run: %s (%s is stale)", job_name, dataset)
    function()
    return True


def run_startup_catchup() -> None:
    """Run today's missing jobs in dependency order, once across all API processes."""
    from crawlers import run_daily_crawl
    from main_legacy import (
        _fetch_baidu_hotsearch_sync,
        evaluate_trending_business,
        generate_project_summaries,
        refresh_and_store,
        refresh_competitor_news,
    )
    from services.bidding_service import collect_bidding_data
    from services.demand_service import collect_demand_signals
    from services.aliyun_solution_service import refresh_aliyun_solutions

    def seed_and_upgrade_technical_evaluation():
        from routers.hotspots import _heuristic_score_project, _store_live_evaluations
        from main_legacy import scrape_github_trending

        live_items = scrape_github_trending(since="daily")
        heuristic_items = [_heuristic_score_project(item) for item in live_items[:25]]
        _store_live_evaluations(datetime.now().strftime("%Y-%m-%d"), heuristic_items)
        result = evaluate_trending_business()
        if result.get("status") != "success":
            logger.warning("AI evaluation upgrade unavailable; heuristic evaluation remains active: %s", result)

    try:
        with get_db() as lock_conn:
            cursor = lock_conn.cursor()
            cursor.execute("SELECT pg_try_advisory_lock(%s) AS acquired", (_LOCK_ID,))
            if not cursor.fetchone()["acquired"]:
                logger.info("startup catch-up skipped: another process owns the lock")
                return
            try:
                _run_if_missing("github_trending", "github refresh", refresh_and_store)
                _run_if_missing("aliyun_solutions", "aliyun solutions refresh", refresh_aliyun_solutions)
                _run_if_missing("baidu_hotsearch", "baidu hotsearch refresh", _fetch_baidu_hotsearch_sync)
                if any(not has_rows_today(name) for name in ("industry_news", "policy_updates", "cloud_vendor_news")):
                    logger.warning("startup catch-up run: daily crawl")
                    run_daily_crawl()
                _run_if_missing("competitor_news", "competitor refresh", refresh_competitor_news)
                _run_if_missing("bidding_opportunities", "bidding refresh", collect_bidding_data)
                _run_if_missing("demand_signals", "demand derivation", collect_demand_signals)
                _run_if_missing("technical_evaluation", "technical evaluation", seed_and_upgrade_technical_evaluation)
                if _technical_summaries_missing():
                    logger.warning("startup catch-up run: project purpose summaries")
                    generate_project_summaries()
            finally:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_ID,))
    except Exception:
        logger.exception("startup catch-up failed")
