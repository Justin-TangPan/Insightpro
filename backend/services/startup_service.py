"""Idempotent startup catch-up for jobs missed while the API was offline."""
import logging
from datetime import datetime

from db import get_db
from services.freshness_service import has_rows_today, solution_catalogs_fresh_today

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
                is_baseline BOOLEAN NOT NULL DEFAULT FALSE,
                vendor TEXT NOT NULL DEFAULT '阿里云',
                content_snapshot JSONB,
                change_summary TEXT NOT NULL DEFAULT '',
                menu_order INTEGER NOT NULL DEFAULT 0,
                removed_at TIMESTAMPTZ,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_aliyun_solutions_seen ON aliyun_solutions(last_seen_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_aliyun_solutions_changed ON aliyun_solutions(last_changed_date DESC)")
        cursor.execute("ALTER TABLE aliyun_solutions ADD COLUMN IF NOT EXISTS is_baseline BOOLEAN")
        cursor.execute("UPDATE aliyun_solutions SET is_baseline=TRUE WHERE is_baseline IS NULL")
        cursor.execute("ALTER TABLE aliyun_solutions ALTER COLUMN is_baseline SET DEFAULT FALSE")
        cursor.execute("ALTER TABLE aliyun_solutions ALTER COLUMN is_baseline SET NOT NULL")
        cursor.execute("ALTER TABLE aliyun_solutions ADD COLUMN IF NOT EXISTS menu_order INTEGER NOT NULL DEFAULT 0")
        cursor.execute("ALTER TABLE aliyun_solutions ADD COLUMN IF NOT EXISTS removed_at TIMESTAMPTZ")
        cursor.execute("ALTER TABLE aliyun_solutions ADD COLUMN IF NOT EXISTS vendor TEXT NOT NULL DEFAULT '阿里云'")
        cursor.execute("ALTER TABLE aliyun_solutions ADD COLUMN IF NOT EXISTS content_snapshot JSONB")
        cursor.execute("ALTER TABLE aliyun_solutions ADD COLUMN IF NOT EXISTS change_summary TEXT NOT NULL DEFAULT ''")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS requirements (
                id BIGSERIAL PRIMARY KEY,
                user_id UUID NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'active', 'planned', 'completed', 'archived')),
                priority TEXT NOT NULL DEFAULT 'medium'
                    CHECK (priority IN ('low', 'medium', 'high', 'critical')),
                source_type TEXT NOT NULL DEFAULT 'manual',
                source_id TEXT,
                source_url TEXT,
                absorbed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute("ALTER TABLE requirements ADD COLUMN IF NOT EXISTS absorbed_at TIMESTAMPTZ")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS solutions (
                id BIGSERIAL PRIMARY KEY,
                user_id UUID NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '未分类',
                status TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'active', 'deprecated', 'archived')),
                version TEXT NOT NULL DEFAULT 'v0.1.0',
                reference_url TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS requirement_solutions (
                requirement_id BIGINT NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
                solution_id BIGINT NOT NULL REFERENCES solutions(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (requirement_id, solution_id)
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_requirements_user_status ON requirements(user_id, status, updated_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_solutions_user_status ON solutions(user_id, status, updated_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_requirement_solutions_solution ON requirement_solutions(solution_id)")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_sso_tickets (
                token_hash TEXT PRIMARY KEY,
                user_id UUID NOT NULL,
                target_user_id UUID,
                expires_at TIMESTAMPTZ NOT NULL,
                used_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_sso_tickets_expiry ON agent_sso_tickets(expires_at)")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_sso_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id UUID NOT NULL,
                agent_user_id UUID NOT NULL,
                auth_role TEXT NOT NULL DEFAULT 'user',
                agent_role TEXT NOT NULL DEFAULT 'user',
                display_name TEXT NOT NULL DEFAULT '',
                expires_at TIMESTAMPTZ NOT NULL,
                revoked_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute("ALTER TABLE agent_sso_tickets ADD COLUMN IF NOT EXISTS target_user_id UUID")
        cursor.execute("ALTER TABLE agent_sso_tickets ADD COLUMN IF NOT EXISTS agent_session_id UUID")
        cursor.execute("ALTER TABLE agent_sso_sessions ADD COLUMN IF NOT EXISTS agent_user_id UUID")
        cursor.execute("UPDATE agent_sso_sessions SET agent_user_id=user_id WHERE agent_user_id IS NULL")
        cursor.execute("ALTER TABLE agent_sso_sessions ALTER COLUMN agent_user_id SET NOT NULL")
        cursor.execute("ALTER TABLE agent_sso_sessions ADD COLUMN IF NOT EXISTS auth_role TEXT NOT NULL DEFAULT 'user'")
        cursor.execute("ALTER TABLE agent_sso_sessions ADD COLUMN IF NOT EXISTS agent_role TEXT NOT NULL DEFAULT 'user'")
        cursor.execute("ALTER TABLE agent_sso_sessions ADD COLUMN IF NOT EXISTS display_name TEXT NOT NULL DEFAULT ''")
        cursor.execute("ALTER TABLE agent_sso_sessions ADD COLUMN IF NOT EXISTS agent_session_id UUID")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_sso_sessions_user ON agent_sso_sessions(user_id, expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_sso_sessions_agent_user ON agent_sso_sessions(agent_user_id, expires_at)")
        cursor.execute("CREATE TABLE IF NOT EXISTS agent_audit_events (id BIGSERIAL PRIMARY KEY, actor_user_id UUID NOT NULL, action TEXT NOT NULL, target_user_id UUID, detail TEXT NOT NULL DEFAULT '', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_audit_events_created ON agent_audit_events(created_at DESC)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_sessions (
                id UUID PRIMARY KEY, user_id UUID NOT NULL, context_type TEXT NOT NULL,
                context_id TEXT NOT NULL, context_title TEXT NOT NULL,
                context_snapshot JSONB NOT NULL, title TEXT NOT NULL DEFAULT '新对话',
                conversation JSONB NOT NULL DEFAULT '[]'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cursor.execute("ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS title TEXT NOT NULL DEFAULT '新对话'")
        cursor.execute("ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS conversation JSONB NOT NULL DEFAULT '[]'::jsonb")
        cursor.execute("ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS task_key TEXT NOT NULL DEFAULT ''")
        cursor.execute("ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS task_title TEXT NOT NULL DEFAULT ''")
        cursor.execute("ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS task_status TEXT NOT NULL DEFAULT 'ready'")
        cursor.execute("ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS default_prompt TEXT NOT NULL DEFAULT ''")
        cursor.execute("ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS hermes_session_id TEXT NOT NULL DEFAULT ''")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_sessions_user_updated ON agent_sessions(user_id, updated_at DESC)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_actions (
                id UUID PRIMARY KEY, session_id UUID NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
                user_id UUID NOT NULL, action TEXT NOT NULL, payload JSONB NOT NULL,
                status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed', 'confirmed', 'rejected')),
                result JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), confirmed_at TIMESTAMPTZ
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_actions_user_status ON agent_actions(user_id, status, created_at DESC)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_artifacts (
                id UUID PRIMARY KEY, user_id UUID NOT NULL, session_id UUID NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
                task_key TEXT NOT NULL DEFAULT '', type TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL,
                filename TEXT NOT NULL DEFAULT '', mime_type TEXT NOT NULL DEFAULT 'text/markdown',
                source_type TEXT, source_id TEXT, requirement_id BIGINT, solution_id BIGINT,
                knowledge_status TEXT NOT NULL DEFAULT 'private' CHECK (knowledge_status IN ('private','requested','published')),
                knowledge_path TEXT, reviewed_by UUID, reviewed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cursor.execute("ALTER TABLE agent_artifacts ADD COLUMN IF NOT EXISTS filename TEXT NOT NULL DEFAULT ''")
        cursor.execute("ALTER TABLE agent_artifacts ADD COLUMN IF NOT EXISTS mime_type TEXT NOT NULL DEFAULT 'text/markdown'")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_artifacts_user_updated ON agent_artifacts(user_id, updated_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_artifacts_knowledge ON agent_artifacts(knowledge_status, updated_at)")
        cursor.execute("ALTER TABLE agent_sso_tickets ENABLE ROW LEVEL SECURITY")
        cursor.execute("ALTER TABLE agent_sso_sessions ENABLE ROW LEVEL SECURITY")
        cursor.execute("ALTER TABLE requirements ENABLE ROW LEVEL SECURITY")
        cursor.execute("ALTER TABLE solutions ENABLE ROW LEVEL SECURITY")
        cursor.execute("ALTER TABLE requirement_solutions ENABLE ROW LEVEL SECURITY")
        cursor.execute("ALTER TABLE agent_sessions ENABLE ROW LEVEL SECURITY")
        cursor.execute("ALTER TABLE agent_actions ENABLE ROW LEVEL SECURITY")
        cursor.execute("ALTER TABLE agent_artifacts ENABLE ROW LEVEL SECURITY")
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


def _run_solution_catalogs_if_stale(function) -> bool:
    if solution_catalogs_fresh_today():
        logger.info("startup catch-up skip: solution catalogues are already fresh")
        return False
    logger.warning("startup catch-up run: solution catalog refresh is stale")
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
    from services.aliyun_solution_service import refresh_solution_catalogs

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
                _run_solution_catalogs_if_stale(refresh_solution_catalogs)
                _run_if_missing("baidu_hotsearch", "baidu hotsearch refresh", _fetch_baidu_hotsearch_sync)
                if not has_rows_today("cloud_vendor_news"):
                    logger.warning("startup catch-up run: daily crawl")
                    run_daily_crawl()
                _run_if_missing("competitor_news", "competitor refresh", refresh_competitor_news)
                _run_if_missing("technical_evaluation", "technical evaluation", seed_and_upgrade_technical_evaluation)
                if _technical_summaries_missing():
                    logger.warning("startup catch-up run: project purpose summaries")
                    generate_project_summaries()
            finally:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_ID,))
    except Exception:
        logger.exception("startup catch-up failed")
