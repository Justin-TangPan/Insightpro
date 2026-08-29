"""
Reconcile Supabase Postgres schema to match what backend code expects.

Idempotent. Safe to run repeatedly. Run once after deploy:
    python reconcile_schema.py

Actions:
  1. Rename columns that migrate_to_supabase.py had renamed (date→bid_date, etc.)
     back to the names the code's SQL uses.
  2. Add missing columns (ADD COLUMN IF NOT EXISTS).
  3. Create missing tables (CREATE TABLE IF NOT EXISTS).
  4. Create indexes / unique constraints (CREATE ... IF NOT EXISTS).
  5. Backfill renamed-column data (old→new) where new is NULL.
"""
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path="../.env", override=True)
import psycopg2

from db import _dsn


def col_exists(c, table: str, col: str) -> bool:
    c.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=%s AND column_name=%s",
        (table, col),
    )
    return c.fetchone() is not None


def rename_col(c, table: str, old: str, new: str):
    """Rename old→new if old exists and new doesn't. Backfill if both exist."""
    if col_exists(c, table, old) and not col_exists(c, table, new):
        c.execute(f'ALTER TABLE "{table}" RENAME COLUMN "{old}" TO "{new}"')
        print(f"  {table}: renamed {old} → {new}")
    elif col_exists(c, table, old) and col_exists(c, table, new):
        # both exist: backfill new from old where new is NULL, then drop old
        c.execute(f'UPDATE "{table}" SET "{new}" = "{old}" WHERE "{new}" IS NULL AND "{old}" IS NOT NULL')
        c.execute(f'ALTER TABLE "{table}" DROP COLUMN IF EXISTS "{old}"')
        print(f"  {table}: backfilled {new} from {old} and dropped {old}")


def add_col(c, table: str, col: str, ddl_type: str):
    c.execute(f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS "{col}" {ddl_type}')


def run():
    conn = psycopg2.connect(_dsn())
    conn.autocommit = True
    c = conn.cursor()

    print("[removed datasets]")
    c.execute("DROP TABLE IF EXISTS demand_reports, demand_signals, bidding_opportunities, policy_updates, industry_news CASCADE")

    # ── competitor_news: rename date→scrape_date; add category ──
    print("[competitor_news]")
    rename_col(c, "competitor_news", "date", "scrape_date")
    add_col(c, "competitor_news", "category", "TEXT")
    c.execute("CREATE INDEX IF NOT EXISTS idx_comp_news_date ON competitor_news(scrape_date)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_comp_news_unique ON competitor_news(scrape_date, vendor, title)")

    # ── email_subscribers ──
    print("[email_subscribers]")
    add_col(c, "email_subscribers", "active", "INTEGER DEFAULT 1")
    add_col(c, "email_subscribers", "weekdays", "INTEGER[] NOT NULL DEFAULT ARRAY[0,1,2,3,4,5,6]")
    add_col(c, "email_subscribers", "send_time", "TEXT NOT NULL DEFAULT '09:05'")
    add_col(c, "email_subscribers", "last_sent_at", "TIMESTAMPTZ")

    # ── github_trending: unique + indexes (match SQLite schema) ──
    print("[github_trending]")
    c.execute("CREATE INDEX IF NOT EXISTS idx_trending_date ON github_trending(scrape_date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_trending_category ON github_trending(category)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_trending_unique ON github_trending(scrape_date, category, repo_name)")

    # ── baidu_hotsearch ──
    print("[baidu_hotsearch]")
    c.execute("CREATE INDEX IF NOT EXISTS idx_baidu_date ON baidu_hotsearch(scrape_date)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_baidu_unique ON baidu_hotsearch(scrape_date, title)")

    # ── Missing tables ──
    print("[trending_business_eval]")
    c.execute("""
        CREATE TABLE IF NOT EXISTS trending_business_eval (
            id SERIAL PRIMARY KEY,
            scrape_date TEXT NOT NULL,
            repo_name TEXT NOT NULL,
            repo_url TEXT,
            language TEXT,
            stars TEXT,
            summary TEXT,
            d1 REAL, d2 REAL, d3 REAL, d4 REAL,
            total REAL,
            level TEXT,
            recommendation TEXT,
            reasoning TEXT,
            eval_time TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    c.execute("ALTER TABLE trending_business_eval ADD COLUMN IF NOT EXISTS summary TEXT")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tbe_date ON trending_business_eval(scrape_date)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tbe_unique ON trending_business_eval(scrape_date, repo_name)")

    print("[cloud_vendor_news]")
    c.execute("""
        CREATE TABLE IF NOT EXISTS cloud_vendor_news (
            id SERIAL PRIMARY KEY,
            crawl_date TEXT NOT NULL,
            vendor TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_cloudnews_date ON cloud_vendor_news(crawl_date)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_cloudnews_unique ON cloud_vendor_news(crawl_date, vendor, title)")

    # ── insight_tasks: AI 分析任务 + 报告存储 ──
    print("[insight_tasks]")
    c.execute("""
        CREATE TABLE IF NOT EXISTS insight_tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            data_sources JSONB,
            result JSONB,
            error TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_task_status ON insight_tasks(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_task_created ON insight_tasks(created_at)")

    print("[aliyun_solutions]")
    c.execute("""
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
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_aliyun_solutions_seen ON aliyun_solutions(last_seen_date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_aliyun_solutions_changed ON aliyun_solutions(last_changed_date DESC)")
    c.execute("ALTER TABLE aliyun_solutions ADD COLUMN IF NOT EXISTS is_baseline BOOLEAN NOT NULL DEFAULT FALSE")
    c.execute("ALTER TABLE aliyun_solutions ADD COLUMN IF NOT EXISTS menu_order INTEGER NOT NULL DEFAULT 0")
    c.execute("ALTER TABLE aliyun_solutions ADD COLUMN IF NOT EXISTS removed_at TIMESTAMPTZ")
    c.execute("ALTER TABLE aliyun_solutions ADD COLUMN IF NOT EXISTS vendor TEXT NOT NULL DEFAULT '阿里云'")
    c.execute("ALTER TABLE aliyun_solutions ADD COLUMN IF NOT EXISTS content_snapshot JSONB")
    c.execute("ALTER TABLE aliyun_solutions ADD COLUMN IF NOT EXISTS change_summary TEXT NOT NULL DEFAULT ''")

    conn.close()
    print("\nSchema reconciliation complete.")


if __name__ == "__main__":
    run()
