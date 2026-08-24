"""Migrate the 4 tables that exist in SQLite but were missing from Supabase
until reconcile_schema.py created them: industry_news, policy_updates,
cloud_vendor_news, trending_business_eval. Also backfills budget_amount.

Idempotent: uses ON CONFLICT DO NOTHING. Safe to re-run.
"""
import os, sqlite3
from dotenv import load_dotenv
load_dotenv(dotenv_path="../.env", override=True)
import psycopg2
from db import _dsn

SQLITE = os.path.join(os.path.dirname(__file__), "trending.db")
sconn = sqlite3.connect(SQLITE)
sconn.row_factory = sqlite3.Row

pg = psycopg2.connect(_dsn())
pg.autocommit = True
pc = pg.cursor()


def copy_table(table, columns):
    sc = sconn.cursor()
    sc.execute(f"SELECT {', '.join(columns)} FROM {table}")
    rows = sc.fetchall()
    if not rows:
        print(f"  {table}: SQLite 无数据，跳过")
        return
    placeholders = ", ".join(["%s"] * len(columns))
    col_str = ", ".join(columns)
    sql = f'INSERT INTO {table} ({col_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
    inserted = 0
    for r in rows:
        try:
            pc.execute(sql, tuple(r))
            if pc.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"    跳过一行: {e}")
    print(f"  {table}: 迁移 {inserted}/{len(rows)} 条")


print("迁移 4 张缺失表 SQLite → Supabase：")
copy_table("industry_news", ["crawl_date", "source", "title", "summary", "url", "category", "created_at"])
copy_table("policy_updates", ["crawl_date", "source", "title", "summary", "url", "category", "severity", "created_at"])
copy_table("cloud_vendor_news", ["crawl_date", "vendor", "title", "summary", "url", "category", "created_at"])
copy_table("trending_business_eval", ["scrape_date", "repo_name", "repo_url", "language", "stars", "summary", "d1", "d2", "d3", "d4", "total", "level", "recommendation", "reasoning", "eval_time", "created_at"])

# Backfill budget_amount on bidding_opportunities from SQLite (which has the parsed values)
print("回填 bidding_opportunities.budget_amount：")
sc = sconn.cursor()
sc.execute("SELECT id, budget_amount FROM bidding_opportunities WHERE budget_amount IS NOT NULL")
ba_rows = sc.fetchall()
if ba_rows:
    # Map by (bid_date, title) since ids differ between SQLite and Supabase
    sc.execute("SELECT bid_date, title, budget_amount FROM bidding_opportunities WHERE budget_amount IS NOT NULL")
    for r in sc.fetchall():
        pc.execute(
            "UPDATE bidding_opportunities SET budget_amount = %s WHERE bid_date = %s AND title = %s AND budget_amount IS NULL",
            (r["budget_amount"], r["bid_date"], r["title"]),
        )
    print(f"  尝试回填 {len(ba_rows)} 条（按 bid_date+title 匹配）")
else:
    print("  SQLite 无 budget_amount 数据")

sconn.close()
pg.close()
print("完成。")
