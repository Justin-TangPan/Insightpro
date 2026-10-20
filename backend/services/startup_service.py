"""Idempotent startup catch-up for jobs missed while the API was offline."""
from __future__ import annotations

import logging
from datetime import datetime

from db import get_db
from services.freshness_service import has_rows_today, solution_catalogs_fresh_today

logger = logging.getLogger(__name__)
_LOCK_ID = 2_026_071_300


def ensure_runtime_schema() -> None:
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
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (vendor, url)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vendor_ai_app_vendor ON vendor_ai_applications(vendor)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vendor_ai_app_status ON vendor_ai_applications(analysis_status)")

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

    from repositories.workbench_repository import absorb_requirements_into_solutions
    absorb_requirements_into_solutions()


def _run_if_missing(dataset: str, job_name: str, function=None, task_key: str | None = None) -> bool:
    if has_rows_today(dataset):
        logger.info("startup catch-up skip: %s is already fresh", dataset)
        return False
    logger.warning("startup catch-up run: %s (%s is stale)", job_name, dataset)
    if task_key:
        from services.task_service import run_task
        run_task(task_key, "startup", function)
    else:
        function()
    return True


def _run_solution_catalogs_if_stale(function=None) -> bool:
    if solution_catalogs_fresh_today():
        logger.info("startup catch-up skip: solution catalogues are already fresh")
        return False
    logger.warning("startup catch-up run: solution catalog refresh is stale")
    if function:
        function()
    else:
        from services.task_service import run_task
        run_task("solution_catalogs_daily", "startup")
    return True


def run_startup_catchup() -> None:
    """Run today's missing jobs in dependency order, once across all API processes."""
    from main_legacy import _fetch_baidu_hotsearch_sync, evaluate_trending_business

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
                _run_if_missing("github_trending", "github refresh", task_key="github_daily")
                _run_solution_catalogs_if_stale()
                _run_if_missing("baidu_hotsearch", "baidu hotsearch refresh", _fetch_baidu_hotsearch_sync, "daily_crawl")
                _run_if_missing("competitor_news", "competitor refresh", task_key="competitor_daily")
                _run_if_missing("technical_evaluation", "technical evaluation", seed_and_upgrade_technical_evaluation, "trending_business_eval_daily")
                from services.task_service import run_task
                run_task("project_briefs_zh_daily", "startup")
            finally:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_ID,))
    except Exception:
        logger.exception("startup catch-up failed")
