import os
from dotenv import load_dotenv
load_dotenv(dotenv_path="../.env", override=True)
import psycopg2

dburl = os.getenv("DIRECT_URL", "") or os.getenv("DATABASE_URL", "")
# Strip libpq-unrecognized query params (e.g. pgbouncer) from Supabase pooler DSN
if "?" in dburl:
    base, query = dburl.split("?", 1)
    kept = [p for p in query.split("&") if not p.startswith("pgbouncer=") and not p.startswith("statement_timeout=")]
    dburl = base + ("?" + "&".join(kept) if kept else "")
print("DSN:", dburl.split("@")[-1] if "@" in dburl else "(set)")
conn = psycopg2.connect(dburl)
c = conn.cursor()
TABLES = [
    "github_trending", "baidu_hotsearch", "scrape_log", "page_visits",
    "email_subscribers", "competitor_news", "trending_business_eval",
    "cloud_vendor_news", "aliyun_solutions", "insight_tasks",
]
for t in TABLES:
    c.execute(
        "select count(*) from information_schema.columns where table_schema='public' and table_name=%s",
        (t,),
    )
    n = c.fetchone()[0]
    if n == 0:
        print(f"{t}: MISSING")
        continue
    c.execute(
        "select column_name, data_type from information_schema.columns where table_schema='public' and table_name=%s order by ordinal_position",
        (t,),
    )
    print(t + ": " + ", ".join(f"{n_}:{d}" for n_, d in c.fetchall()))
# also list any extra public tables
c.execute("select table_name from information_schema.tables where table_schema='public' order by table_name")
print("ALL public tables:", [r[0] for r in c.fetchall()])
conn.close()
