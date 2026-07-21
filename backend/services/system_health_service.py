"""End-to-end readiness checks for the production data path.

Liveness only proves that the process can answer. Readiness additionally proves
that PostgreSQL is reachable and that the data required by the technical
hotspots page is current and non-empty.
"""
from datetime import datetime

from db import get_db
from services.freshness_service import get_freshness_report


def _technical_snapshot() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM github_trending
               WHERE scrape_date = %s AND category = 'daily') AS trending_count,
              (SELECT COUNT(*) FROM trending_business_eval
               WHERE scrape_date = %s) AS evaluation_count
            """,
            (today, today),
        )
        row = cursor.fetchone()
    return {
        "business_date": today,
        "trending_count": int(row["trending_count"]),
        "evaluation_count": int(row["evaluation_count"]),
    }


def evaluate_readiness(freshness: dict, technical: dict) -> dict:
    """Evaluate readiness separately so the policy remains unit-testable."""
    checks = {
        "freshness": freshness.get("status") == "fresh",
        "github_trending_nonempty": technical.get("trending_count", 0) > 0,
        "technical_evaluation_nonempty": technical.get("evaluation_count", 0) > 0,
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    return {
        "status": "healthy" if not failed_checks else "unhealthy",
        "checked_at": datetime.now().isoformat(),
        "checks": checks,
        "failed_checks": failed_checks,
        "technical_hotspots": technical,
        "freshness": freshness,
    }


def get_readiness_report() -> dict:
    """Return the complete database and data-readiness report."""
    try:
        freshness = get_freshness_report()
        technical = _technical_snapshot()
        return evaluate_readiness(freshness, technical)
    except Exception as exc:
        return {
            "status": "unhealthy",
            "checked_at": datetime.now().isoformat(),
            "checks": {"database": False},
            "failed_checks": ["database"],
            "error": str(exc)[:300],
        }
