"""Data cleanup — remove old scrape logs and visit records."""
import logging
from datetime import datetime, timedelta
from db import get_db

logger = logging.getLogger(__name__)


def cleanup_old_data():
    cutoff_90 = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    cutoff_180 = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    with get_db() as conn:
        c = conn.cursor()
        for table in ["github_trending", "trending_business_eval", "baidu_hotsearch", "scrape_log", "competitor_news"]:
            c.execute(f"DELETE FROM {table} WHERE scrape_date < %s", (cutoff_90,))
        c.execute("DELETE FROM page_visits WHERE created_at < %s", (cutoff_180,))
    logger.info("old data cleanup done (90d/180d cutoffs)")
