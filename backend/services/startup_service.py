"""Idempotent startup catch-up for jobs missed while the API was offline."""
from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from db import get_db
from services.freshness_service import has_rows_today, solution_catalogs_fresh_today

logger = logging.getLogger(__name__)
_LOCK_ID = 2_026_071_300


def ensure_runtime_schema(absorb_requirements: bool = True) -> None:
    """Run Alembic migrations, then apply idempotent DDL that Alembic cannot manage.

    Alembic handles: table creation, column additions, type changes, simple indexes.
    This function handles: pgvector extension, RLS policies, GIN trigram indexes,
    and any runtime-conditional DDL (e.g. embedding dimensions).
    """
    # ── Step 1: Run Alembic migrations ──
    from alembic.config import Config as AlembicConfig
    from alembic import command as alembic_cmd
    alembic_cfg = AlembicConfig()
    alembic_cfg.set_main_option("script_location", "migrations")
    from db import _dsn
    alembic_cfg.set_main_option("sqlalchemy.url", _dsn())
    alembic_cmd.upgrade(alembic_cfg, "head")
    logger.info("Alembic migrations applied (or already up-to-date)")

    # ── Step 2: Idempotent DDL not managed by Alembic ──
    with get_db() as conn:
        cursor = conn.cursor()
        from settings import settings
        if not 1 <= settings.EMBEDDING_DIMENSIONS <= 4000:
            raise RuntimeError("EMBEDDING_DIMENSIONS must be between 1 and 4000")

        # pgvector extension + knowledge_chunks embedding column
        cursor.execute("CREATE SCHEMA IF NOT EXISTS extensions")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions")
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id BIGSERIAL PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                owner_user_id UUID,
                visibility TEXT NOT NULL CHECK (visibility IN ('team','private')),
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source_url TEXT,
                metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                content_hash TEXT NOT NULL,
                embedding extensions.vector({settings.EMBEDDING_DIMENSIONS}) NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (source_type, source_id, chunk_index)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_access ON knowledge_chunks(visibility, owner_user_id, updated_at DESC)")

        # Structured official AI applications (identity + source snapshot + structured analysis)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vendor_ai_applications (
                id BIGSERIAL PRIMARY KEY,
                vendor TEXT NOT NULL,
                name TEXT,
                url TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'launch',
                published_at TEXT,
                category TEXT,
                summary TEXT,
                capability TEXT,
                opportunity TEXT,
                limitation TEXT,
                source_text TEXT,
                analysis_status TEXT NOT NULL DEFAULT 'pending',
                analyzed_at TIMESTAMPTZ,
                analysis_model TEXT,
                source_fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                source_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                source_fingerprint TEXT,
                analyzed_source_fingerprint TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (vendor, url)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vendor_ai_app_vendor ON vendor_ai_applications(vendor)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vendor_ai_app_status ON vendor_ai_applications(analysis_status)")
        cursor.execute("""CREATE TABLE IF NOT EXISTS board_daily_insights (
            board TEXT NOT NULL, insight_date TEXT NOT NULL, fingerprint TEXT NOT NULL,
            analysis TEXT NOT NULL, generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (board, insight_date)
        )""")

        # Agent runtime history column (added post-Alembic)
        cursor.execute("ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS runtime_history JSONB NOT NULL DEFAULT '[]'::jsonb")

        # Row-Level Security policies
        cursor.execute("ALTER TABLE agent_sso_tickets ENABLE ROW LEVEL SECURITY")
        cursor.execute("ALTER TABLE agent_sso_sessions ENABLE ROW LEVEL SECURITY")
        cursor.execute("ALTER TABLE requirements ENABLE ROW LEVEL SECURITY")
        cursor.execute("ALTER TABLE solutions ENABLE ROW LEVEL SECURITY")
        cursor.execute("ALTER TABLE requirement_solutions ENABLE ROW LEVEL SECURITY")
        cursor.execute("ALTER TABLE agent_sessions ENABLE ROW LEVEL SECURITY")
        cursor.execute("ALTER TABLE agent_actions ENABLE ROW LEVEL SECURITY")
        cursor.execute("ALTER TABLE agent_artifacts ENABLE ROW LEVEL SECURITY")

        # pg_trgm extension + GIN trigram search indexes
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_github_trending_search ON github_trending USING GIN
            ((COALESCE(repo_name,'') || ' ' || COALESCE(description,'') || ' ' || COALESCE(language,'')) gin_trgm_ops)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_aliyun_solutions_search ON aliyun_solutions USING GIN
            ((COALESCE(title,'') || ' ' || COALESCE(category,'') || ' ' || COALESCE(summary,'') || ' ' || COALESCE(source_description,'')) gin_trgm_ops)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_competitor_news_search ON competitor_news USING GIN
            ((COALESCE(title,'') || ' ' || COALESCE(vendor,'') || ' ' || COALESCE(summary,'') || ' ' || COALESCE(category,'')) gin_trgm_ops)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_requirements_search ON requirements USING GIN
            ((COALESCE(title,'') || ' ' || COALESCE(description,'') || ' ' || COALESCE(source_type,'')) gin_trgm_ops)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_solutions_search ON solutions USING GIN
            ((COALESCE(name,'') || ' ' || COALESCE(description,'') || ' ' || COALESCE(category,'') || ' ' || COALESCE(version,'')) gin_trgm_ops)
        """)

    if absorb_requirements:
        from repositories.workbench_repository import absorb_requirements_into_solutions
        absorb_requirements_into_solutions()


def refresh_baidu_hotsearch_if_missing() -> dict:
    if has_rows_today("baidu_hotsearch"):
        return {"status": "success", "total": 0}
    from crawlers.baidu_crawler import _fetch_baidu_hotsearch_sync

    items = _fetch_baidu_hotsearch_sync()
    if not items or any(item.get("title") in {"Loading data...", "Hot search load failed"} for item in items):
        return {"status": "partial_success", "error": "Baidu hot search returned no fresh items"}
    return {"status": "success", "total": len(items)}


def _run_if_missing(dataset: str, job_name: str, function=None, task_key: str | None = None) -> bool:
    if has_rows_today(dataset):
        logger.info("startup catch-up skip: %s is already fresh", dataset)
        return False
    logger.warning("startup catch-up run: %s (%s is stale)", job_name, dataset)
    if task_key:
        _run_task_if_missing_today(task_key, function)
    else:
        function()
    return True


def _run_solution_catalogs_if_stale(function=None) -> bool:
    if solution_catalogs_fresh_today():
        logger.info("startup catch-up skip: solution catalogues are already fresh")
        return False
    logger.warning("startup catch-up run: solution catalog refresh is stale")
    return _run_task_if_missing_today("solution_catalogs_daily", function)


def _task_succeeded_today(task_key: str) -> bool:
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT status='success' AS present
            FROM platform_task_runs
            WHERE task_key=%s
              AND (started_at AT TIME ZONE 'Asia/Shanghai')::date=%s
            ORDER BY started_at DESC, id DESC LIMIT 1""", (task_key, today))
        row = cursor.fetchone()
        return bool(row and row["present"])


def _task_attempted_today(task_key: str) -> bool:
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT EXISTS (
            SELECT 1 FROM platform_task_runs
            WHERE task_key=%s
              AND (started_at AT TIME ZONE 'Asia/Shanghai')::date=%s
        ) AS present""", (task_key, today))
        return bool(cursor.fetchone()["present"])


def _run_task_if_missing_today(task_key: str, function=None) -> bool:
    if _task_succeeded_today(task_key):
        return False
    if _task_attempted_today(task_key):
        logger.info("startup catch-up skip: %s already attempted today", task_key)
        return False
    from services.task_service import run_task
    run_task(task_key, "startup", function)
    return True


def run_startup_catchup() -> None:
    """Run today's missing jobs in dependency order, once across all API processes."""
    from services.evaluation_service import evaluate_trending_business
    from services.task_service import required_source_tasks

    def seed_and_upgrade_technical_evaluation():
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
                for task_key in required_source_tasks():
                    _run_task_if_missing_today(task_key)
                _run_task_if_missing_today("baidu_hotsearch_daily")
                _run_if_missing("technical_evaluation", "technical evaluation", seed_and_upgrade_technical_evaluation, "trending_business_eval_daily")
                _run_task_if_missing_today("project_briefs_zh_daily")
                _run_task_if_missing_today("board_insights_daily")
            finally:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_ID,))
    except Exception:
        logger.exception("startup catch-up failed")
