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
        c.execute("""UPDATE trending_business_eval SET analysis_id=NULL
                     WHERE scrape_date < %s AND analysis_id IS NOT NULL""", (cutoff_90,))
        c.execute("""DELETE FROM trending_business_eval old
                     WHERE old.scrape_date < %s
                       AND NOT EXISTS (
                         SELECT 1 FROM trending_business_eval recent
                         WHERE recent.analysis_id=old.id AND recent.scrape_date >= %s
                       )""", (cutoff_90, cutoff_90))
        for table in ["github_trending", "baidu_hotsearch", "scrape_log", "competitor_news"]:
            c.execute(f"DELETE FROM {table} WHERE scrape_date < %s", (cutoff_90,))
        c.execute("DELETE FROM page_visits WHERE created_at < %s", (cutoff_180,))
    logger.info("old data cleanup done (90d/180d cutoffs)")
