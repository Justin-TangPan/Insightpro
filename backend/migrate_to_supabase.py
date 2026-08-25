"""
SQLite → Supabase PostgreSQL 数据迁移脚本
将本地 trending.db 的数据导入到 Supabase 远端数据库

用法: python migrate_to_supabase.py
"""

import sqlite3
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env", override=True)

from supabase import create_client, Client

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
DB_PATH = os.path.join(os.path.dirname(__file__), "trending.db")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set in .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def migrate_table(table_name: str, supabase_table: str, column_map: dict, batch_size: int = 100):
    """通用迁移函数：SQLite 表 → Supabase 表"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 获取总数
    c.execute(f"SELECT COUNT(*) FROM {table_name}")
    total = c.fetchone()[0]
    if total == 0:
        print(f"  [{table_name}] 无数据，跳过")
        conn.close()
        return 0

    print(f"  [{table_name}] 共 {total} 条记录，开始迁移...")

    # 先清空 Supabase 目标表
    try:
        supabase.table(supabase_table).delete().neq("id", 0).execute()
    except Exception as e:
        print(f"    清空远端表失败: {e}")

    # 分批迁移
    migrated = 0
    offset = 0
    while offset < total:
        c.execute(f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}")
        rows = c.fetchall()

        batch = []
        for row in rows:
            record = {}
            for sqlite_col, supabase_col in column_map.items():
                val = row[sqlite_col]
                # Convert datetime strings to ISO format if needed
                if val is not None and isinstance(val, str) and supabase_col == "created_at":
                    try:
                        val = datetime.strptime(val, "%Y-%m-%d %H:%M:%S").isoformat()
                    except (ValueError, TypeError):
                        val = datetime.now().isoformat()
                record[supabase_col] = val
            batch.append(record)

        if batch:
            try:
                result = supabase.table(supabase_table).insert(batch).execute()
                migrated += len(batch)
                print(f"    已迁移 {migrated}/{total}")
            except Exception as e:
                print(f"    批次插入失败 (offset={offset}): {e}")
                # Try one by one
                for record in batch:
                    try:
                        supabase.table(supabase_table).insert(record).execute()
                        migrated += 1
                    except Exception:
                        pass

        offset += batch_size

    conn.close()
    print(f"  [{table_name}] 迁移完成: {migrated}/{total}")
    return migrated


def main():
    print("=" * 60)
    print("SQLite → Supabase 数据迁移")
    print("=" * 60)

    if not os.path.exists(DB_PATH):
        print(f"ERROR: SQLite 数据库不存在: {DB_PATH}")
        sys.exit(1)

    total_migrated = 0

    # 1. GitHub Trending
    total_migrated += migrate_table("github_trending", "github_trending", {
        "scrape_date": "scrape_date", "scrape_time": "scrape_time",
        "repo_name": "repo_name", "repo_url": "repo_url",
        "description": "description", "language": "language",
        "stars": "stars", "forks": "forks",
        "today_stars": "today_stars", "tags": "tags",
        "category": "category", "created_at": "created_at",
    })

    # 2. Baidu Hotsearch
    total_migrated += migrate_table("baidu_hotsearch", "baidu_hotsearch", {
        "scrape_date": "scrape_date", "scrape_time": "scrape_time",
        "rank": "rank", "title": "title", "hot": "hot",
        "link": "link", "created_at": "created_at",
    })

    # 3. Email Subscribers
    total_migrated += migrate_table("email_subscribers", "email_subscribers", {
        "email": "email", "name": "name", "created_at": "created_at",
    })

    # 4. Page Visits
    total_migrated += migrate_table("page_visits", "page_visits", {
        "page_path": "page_path", "visitor_id": "visitor_id",
        "user_agent": "user_agent", "referrer": "referrer",
        "created_at": "created_at",
    }, batch_size=500)

    # 5. Scrape Log
    total_migrated += migrate_table("scrape_log", "scrape_log", {
        "scrape_date": "scrape_date", "scrape_time": "scrape_time",
        "status": "status", "items_count": "items_count",
        "error_msg": "error_msg", "created_at": "created_at",
    })

    # 6. Competitor News
    total_migrated += migrate_table("competitor_news", "competitor_news", {
        "vendor": "vendor", "title": "title", "link": "link",
        "summary": "summary", "scrape_date": "date", "created_at": "created_at",
    })

    print("=" * 60)
    print(f"迁移完成！总计迁移 {total_migrated} 条记录")
    print("=" * 60)


if __name__ == "__main__":
    main()
