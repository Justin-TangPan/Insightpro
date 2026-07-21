"""Idempotent startup catch-up for jobs missed while the API was offline."""
import logging
from datetime import datetime

from db import get_db
from services.freshness_service import has_rows_today

logger = logging.getLogger(__name__)
_LOCK_ID = 2_026_071_300


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
        refresh_and_store,
        refresh_competitor_news,
    )
    from services.bidding_service import collect_bidding_data
    from services.demand_service import collect_demand_signals

    def seed_and_upgrade_technical_evaluation():
        from routers.hotspots import _heuristic_score_project, _store_live_evaluations
        from main_legacy import scrape_github_trending

        live_items = scrape_github_trending(since="daily")
        heuristic_items = [_heuristic_score_project(item) for item in live_items[:10]]
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
                _run_if_missing("baidu_hotsearch", "baidu hotsearch refresh", _fetch_baidu_hotsearch_sync)
                if any(not has_rows_today(name) for name in ("industry_news", "policy_updates", "cloud_vendor_news")):
                    logger.warning("startup catch-up run: daily crawl")
                    run_daily_crawl()
                _run_if_missing("competitor_news", "competitor refresh", refresh_competitor_news)
                _run_if_missing("bidding_opportunities", "bidding refresh", collect_bidding_data)
                _run_if_missing("demand_signals", "demand derivation", collect_demand_signals)
                _run_if_missing("technical_evaluation", "technical evaluation", seed_and_upgrade_technical_evaluation)
            finally:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_ID,))
    except Exception:
        logger.exception("startup catch-up failed")
