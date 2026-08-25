"""Small database-backed context lookup used by chat and reports."""
from db import get_db


def init_deep_searcher(force_reload: bool = False):
    """Kept as a startup-compatible no-op; context now comes from PostgreSQL."""
    return None


def retrieve_context(query_text: str, top_k: int = 10) -> list[dict]:
    query = query_text.strip().lower()
    sources = [
        (
            "github_trending",
            "SELECT repo_name AS title, description AS summary, repo_url AS url, language AS source FROM github_trending ORDER BY scrape_date DESC, id DESC LIMIT 20",
        ),
        (
            "solutions",
            "SELECT title, summary, url, category AS source FROM aliyun_solutions WHERE is_active=TRUE ORDER BY last_changed_date DESC, id DESC LIMIT 20",
        ),
        (
            "competitive_news",
            "SELECT title, summary, link AS url, vendor AS source FROM competitor_news ORDER BY scrape_date DESC, id DESC LIMIT 20",
        ),
    ]
    results = []
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            for collection, sql in sources:
                cursor.execute(sql)
                for row in cursor.fetchall():
                    text = f"[{row['source'] or collection}] {row['title']}\n{row['summary'] or ''}".strip()
                    score = 1.0 if query and query in text.lower() else 0.5
                    results.append({
                        "text": text,
                        "score": score,
                        "metadata": {"title": row["title"], "url": row["url"] or ""},
                        "collection": collection,
                    })
    except Exception:
        return []
    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]


def context_to_str(results: list[dict], max_chars: int = 6000) -> str:
    text = "\n\n".join(f"--- {item['collection']} ---\n{item['text']}" for item in results)
    return text if len(text) <= max_chars else text[:max_chars] + "...\n[内容已截断]"


async def deep_research(query_text: str, max_iter: int = 3) -> dict:
    results = retrieve_context(query_text, top_k=max(3, max_iter * 3))
    return {
        "answer": context_to_str(results) or "暂无可用的技术解决方案资料。",
        "sources": results,
        "tokens": 0,
    }
