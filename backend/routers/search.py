"""全局搜索路由"""
from fastapi import APIRouter, Query
from db import get_db

router = APIRouter()


@router.get("/search")
async def global_search(q: str = Query("", min_length=1, max_length=100)):
    if not q:
        return {"results": [], "total": 0}
    safe_q = q.strip()[:100].replace("'", "''").replace('"', '""')
    results = []
    queries = [
        ("SELECT title, source, url, 'industry_news' AS type FROM industry_news WHERE title ILIKE %s ORDER BY id DESC LIMIT 5",),
        ("SELECT title, industry AS source, url, 'bidding' AS type FROM bidding_opportunities WHERE title ILIKE %s ORDER BY relevance_score DESC LIMIT 5",),
        ("SELECT title, industry AS source, url, 'demand' AS type FROM demand_signals WHERE title ILIKE %s ORDER BY relevance_score DESC LIMIT 5",),
        ("SELECT title, source, url, 'policy' AS type FROM policy_updates WHERE title ILIKE %s ORDER BY id DESC LIMIT 5",),
    ]
    with get_db() as conn:
        c = conn.cursor()
        for sql, in queries:
            try:
                c.execute(sql, (f"%{safe_q}%",))
                results.extend([dict(r) for r in c.fetchall()])
            except Exception:
                pass
    return {"results": results, "total": len(results), "query": q}
