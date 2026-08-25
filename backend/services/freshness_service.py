"""Data freshness checks used by health APIs and startup catch-up."""
from datetime import datetime

from db import get_db


DATASETS = {
    "github_trending": ("github_trending", "scrape_date", 0),
    "technical_evaluation": ("trending_business_eval", "scrape_date", 0),
    "aliyun_solutions": ("aliyun_solutions", "last_seen_date", 0),
    "baidu_hotsearch": ("baidu_hotsearch", "scrape_date", 0),
    "cloud_vendor_news": ("cloud_vendor_news", "crawl_date", 1),
    "competitor_news": ("competitor_news", "scrape_date", 1),
}


def has_rows_today(dataset: str) -> bool:
    table, date_column, _ = DATASETS[dataset]
    today = datetime.now().strftime("%Y-%m-%d")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT EXISTS(SELECT 1 FROM {table} WHERE {date_column} = %s) AS present",
            (today,),
        )
        return bool(cursor.fetchone()["present"])


def get_freshness_report() -> dict:
    today = datetime.now().date()
    datasets = []
    overall = "fresh"
    with get_db() as conn:
        cursor = conn.cursor()
        for name, (table, date_column, max_age_days) in DATASETS.items():
            try:
                cursor.execute(f"SELECT MAX({date_column}) AS latest_date, COUNT(*) AS total FROM {table}")
                row = cursor.fetchone()
                latest_raw = row["latest_date"] if row else None
                latest = datetime.strptime(str(latest_raw), "%Y-%m-%d").date() if latest_raw else None
                age_days = (today - latest).days if latest else None
                status = "fresh" if age_days is not None and age_days <= max_age_days else "stale"
                if status == "stale":
                    overall = "stale"
                datasets.append({
                    "dataset": name,
                    "latest_date": latest.isoformat() if latest else None,
                    "age_days": age_days,
                    "max_age_days": max_age_days,
                    "status": status,
                    "total": row["total"] if row else 0,
                })
            except Exception as exc:
                conn.rollback()
                overall = "unhealthy"
                datasets.append({
                    "dataset": name,
                    "latest_date": None,
                    "age_days": None,
                    "max_age_days": max_age_days,
                    "status": "error",
                    "error": str(exc)[:200],
                })
    return {"status": overall, "checked_at": datetime.now().isoformat(), "datasets": datasets}
