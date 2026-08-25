"""全局搜索路由"""
from fastapi import APIRouter, Query
from db import get_db

router = APIRouter()


@router.get("/search")
async def global_search(q: str = Query("", min_length=1, max_length=100)):
    if not q:
        return {"results": [], "total": 0}
    safe_q = q.strip()[:100]
    results = []
    queries = [
        ("SELECT repo_name AS title, language AS source, repo_url AS url, 'technical' AS type FROM github_trending WHERE repo_name ILIKE %s ORDER BY id DESC LIMIT 5",),
        ("SELECT title, category AS source, url, 'solution' AS type FROM aliyun_solutions WHERE is_active=TRUE AND title ILIKE %s ORDER BY last_changed_date DESC LIMIT 5",),
        ("SELECT title, vendor AS source, link AS url, 'competitor' AS type FROM competitor_news WHERE title ILIKE %s ORDER BY id DESC LIMIT 5",),
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
