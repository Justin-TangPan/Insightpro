"""技术热点路由 — GitHub Trending"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta
from db import get_db
from routers.auth import require_auth

router = APIRouter()


# 导入原 main.py 中的函数（待后续完全迁移到 service）
from main_legacy import (
    scrape_github_trending,
    refresh_and_store,
    evaluate_trending_business,
    _parse_eval_json,
    BUSINESS_EVAL_SYSTEM_PROMPT,
    _fetch_baidu_hotsearch_sync,
)


def _empty_eval_summary():
    return {"strong": 0, "worth": 0, "marginal": 0, "not_recommended": 0}


def _summarize_eval(items: list[dict]) -> dict:
    summary = _empty_eval_summary()
    for it in items:
        lvl = (it.get("level") or "")
        if "强烈推荐" in lvl:
            summary["strong"] += 1
        elif "值得做" in lvl:
            summary["worth"] += 1
        elif "勉强" in lvl:
            summary["marginal"] += 1
        elif "不建议" in lvl:
            summary["not_recommended"] += 1
    return summary


def _heuristic_score_project(item: dict) -> dict:
    text = f"{item.get('repo_name', '')} {item.get('description', '')}".lower()
    server_keywords = ["server", "database", "infra", "framework", "runtime", "api", "agent", "rag", "llm", "model"]
    marketing_keywords = ["ai", "agent", "automation", "analytics", "dashboard", "workflow", "search"]
    scenario_keywords = ["chat", "code", "data", "dev", "ops", "security", "browser", "document", "video"]
    cloud_keywords = ["kubernetes", "docker", "cloud", "deploy", "serverless", "postgres", "redis", "gpu"]

    def score(keywords: list[str], base: float) -> float:
        hits = sum(1 for kw in keywords if kw in text)
        return min(9.0, base + hits * 1.1)

    d1 = score(server_keywords, 5.4)
    d2 = score(marketing_keywords, 5.0)
    d3 = score(scenario_keywords, 5.2)
    d4 = score(cloud_keywords, 4.8)
    total = round((d1 + d2 + d3 + d4) / 4, 1)
    if total >= 8:
        level = "强烈推荐"
    elif total >= 6:
        level = "值得做"
    elif total >= 4:
        level = "勉强可做"
    else:
        level = "不建议"
    return {
        "repo_name": item.get("repo_name", ""),
        "repo_url": item.get("repo_url"),
        "language": item.get("language"),
        "stars": item.get("stars"),
        "summary": f"{item.get('repo_name', '该项目')} 是一个围绕 {item.get('description') or '开源技术能力'} 的项目，可用于快速验证和搭建相关应用。",
        "d1": round(d1, 1),
        "d2": round(d2, 1),
        "d3": round(d3, 1),
        "d4": round(d4, 1),
        "total": total,
        "level": level,
        "recommendation": "优先验证企业场景、部署复杂度和可复制的解决方案包装。",
        "reasoning": "数据库或 AI 评估不可用时，基于项目描述、技术属性和云上部署关键词生成临时评估。",
        "eval_time": datetime.now().strftime("%H:%M:%S"),
        "evaluation_mode": "heuristic",
    }


async def _evaluate_live_items(items: list[dict], limit: int = 25) -> list[dict]:
    from services.ai_service import chat_complete

    selected = items[:limit]
    if not selected:
        return []
    project_lines = [
        f"{i + 1}. {r['repo_name']} | Stars={r.get('stars') or 'N/A'} | {r.get('description') or ''}"
        for i, r in enumerate(selected)
    ]
    user_prompt = "对以下 GitHub Trending 项目逐一进行四维业务价值评估，严格按指定 JSON 数组格式输出：\n\n" + "\n".join(project_lines)
    try:
        raw = await asyncio.to_thread(
            chat_complete,
            messages=[
                {"role": "system", "content": BUSINESS_EVAL_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=8192,
            timeout=120,
        )
        parsed = _parse_eval_json(raw)
    except Exception as e:
        print(f"[business-eval] 实时 AI 评估失败，使用启发式兜底: {e}")
        parsed = []

    if not parsed:
        return [_heuristic_score_project(item) for item in selected]

    enriched = []
    for item in parsed:
        repo_name = item.get("repo_name", "")
        match = next((r for r in selected if r.get("repo_name") == repo_name), None)
        enriched.append({
            "repo_name": repo_name,
            "repo_url": match.get("repo_url") if match else None,
            "language": match.get("language") if match else None,
            "stars": match.get("stars") if match else None,
            "summary": item.get("summary") or "",
            "d1": item.get("d1"),
            "d2": item.get("d2"),
            "d3": item.get("d3"),
            "d4": item.get("d4"),
            "total": item.get("total"),
            "level": item.get("level") or "",
            "recommendation": item.get("recommendation") or "",
            "reasoning": item.get("reasoning") or "",
            "eval_time": datetime.now().strftime("%H:%M:%S"),
            "evaluation_mode": "ai",
        })
    return enriched


def _store_live_evaluations(date_str: str, items: list[dict]) -> None:
    if not items:
        return
    with get_db() as conn:
        c = conn.cursor()
        for item in items:
            c.execute(
                """
                INSERT INTO trending_business_eval
                (scrape_date, repo_name, repo_url, language, stars, summary, d1, d2, d3, d4,
                 total, level, recommendation, reasoning, eval_time)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (scrape_date, repo_name) DO UPDATE SET
                  repo_url = EXCLUDED.repo_url,
                  language = EXCLUDED.language,
                  stars = EXCLUDED.stars,
                  summary = EXCLUDED.summary,
                  d1 = EXCLUDED.d1,
                  d2 = EXCLUDED.d2,
                  d3 = EXCLUDED.d3,
                  d4 = EXCLUDED.d4,
                  total = EXCLUDED.total,
                  level = EXCLUDED.level,
                  recommendation = EXCLUDED.recommendation,
                  reasoning = EXCLUDED.reasoning,
                  eval_time = EXCLUDED.eval_time
                """,
                (
                    date_str, item.get("repo_name"), item.get("repo_url"), item.get("language"),
                    item.get("stars"), item.get("summary"), item.get("d1"), item.get("d2"), item.get("d3"),
                    item.get("d4"), item.get("total"), item.get("level"),
                    item.get("recommendation"), item.get("reasoning"), item.get("eval_time"),
                ),
            )


@router.get("/github-trending")
async def get_github_trending(
    since: str = Query("daily", enum=["daily", "weekly", "monthly"]),
    date: Optional[str] = None,
):
    """获取 GitHub Trending 项目（优先实时，降级数据库）"""
    try:
        items = await asyncio.to_thread(scrape_github_trending, since=since)
        if items:
            now = datetime.now()
            try:
                with get_db() as conn:
                    c = conn.cursor()
                    for item in items:
                        c.execute("""
                            INSERT INTO github_trending
                            (scrape_date, scrape_time, repo_name, repo_url, description, language, stars, forks, today_stars, category)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (scrape_date, category, repo_name) DO NOTHING
                        """, (now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
                              item["repo_name"], item["repo_url"], item["description"],
                              item["language"], item["stars"], item["forks"],
                              item["today_stars"], item["category"]))
            except Exception as e:
                print(f"GitHub 实时数据写入数据库失败，继续返回实时结果: {e}")
            return {"items": items, "source": "live", "count": len(items), "date": now.strftime("%Y-%m-%d")}
    except Exception as e:
        print(f"GitHub 实时抓取失败，降级到数据库: {e}")

    target_date = date or datetime.now().strftime("%Y-%m-%d")
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT * FROM github_trending
                WHERE scrape_date = %s AND category = %s
                ORDER BY id
            """, (target_date, since))
            rows = c.fetchall()
    except Exception as e:
        print(f"GitHub 数据库降级读取失败: {e}")
        rows = []
    if rows:
        return {"items": [dict(r) for r in rows], "source": "database", "count": len(rows), "date": target_date}
    return {"items": [], "source": "empty", "count": 0, "date": target_date}


@router.get("/github-trending/history")
async def get_github_trending_history(
    days: int = Query(7, ge=1, le=90),
    category: str = Query("daily", enum=["daily", "weekly", "monthly"]),
):
    """查询历史 GitHub Trending 记录"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            c.execute("""
                SELECT DISTINCT scrape_date FROM github_trending
                WHERE scrape_date >= %s AND category = %s
                ORDER BY scrape_date DESC
            """, (cutoff, category))
            dates = [r["scrape_date"] for r in c.fetchall()]
            history = []
            for d in dates:
                c.execute("""
                    SELECT * FROM github_trending
                    WHERE scrape_date = %s AND category = %s
                    ORDER BY id LIMIT 25
                """, (d, category))
                rows = c.fetchall()
                c.execute("""
                    SELECT repo_name, repo_url, language, stars, summary, d1, d2, d3, d4,
                           total, level, recommendation, reasoning, eval_time
                    FROM trending_business_eval
                    WHERE scrape_date = %s
                    ORDER BY total DESC
                """, (d,))
                evaluations = c.fetchall() if category == "daily" else []
                history.append({
                    "date": d,
                    "items": [dict(r) for r in rows],
                    "evaluations": [dict(r) for r in evaluations],
                })
            return {"history": history, "total_dates": len(dates), "category": category}
    except Exception as e:
        print(f"GitHub 历史记录读取失败: {e}")
        return {"history": [], "total_dates": 0, "category": category}


@router.post("/github-trending/refresh")
async def manual_refresh(_=Depends(require_auth)):
    """手动触发 GitHub Trending 刷新"""
    try:
        await asyncio.to_thread(refresh_and_store)
        return {"status": "success", "message": "GitHub Trending 数据已刷新"}
    except Exception as e:
        items = await asyncio.to_thread(scrape_github_trending, since="daily")
        if items:
            return {"status": "partial_success", "message": f"数据库写入失败，已获取 {len(items)} 条实时 GitHub Trending", "items": items}
        raise HTTPException(status_code=500, detail=f"刷新失败: {str(e)}")


@router.get("/github-trending/business-eval")
async def get_business_eval(date: Optional[str] = None):
    """获取当日 GitHub Trending 业务价值评估结果"""
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT repo_name, repo_url, language, stars, summary,
                       d1, d2, d3, d4, total, level, recommendation, reasoning, eval_time
                FROM trending_business_eval
                WHERE scrape_date = %s
                ORDER BY total DESC
            """, (target_date,))
            rows = c.fetchall()
        items = [dict(r) for r in rows]
        if items:
            return {"date": target_date, "items": items, "count": len(items), "summary": _summarize_eval(items), "source": "database"}
    except Exception as e:
        print(f"[business-eval] 数据库读取失败，尝试实时评估: {e}")

    if date and target_date != datetime.now().strftime("%Y-%m-%d"):
        return {"date": target_date, "items": [], "count": 0, "summary": _empty_eval_summary(), "source": "empty_history"}

    live_items = await asyncio.to_thread(scrape_github_trending, since="daily")
    # The read path must remain fast and non-empty even when the AI provider is slow.
    # Manual refresh and the startup worker can upgrade these heuristic rows later.
    items = [_heuristic_score_project(item) for item in live_items[:25]]
    if items:
        try:
            await asyncio.to_thread(_store_live_evaluations, target_date, items)
        except Exception as e:
            print(f"[business-eval] 实时评估写入失败，继续返回结果: {e}")
    return {"date": target_date, "items": items, "count": len(items), "summary": _summarize_eval(items), "source": "live_heuristic"}


@router.post("/github-trending/business-eval/refresh")
async def refresh_business_eval(limit: int = Query(25, ge=1, le=25), _=Depends(require_auth)):
    """手动触发 GitHub Trending 业务价值评估"""
    try:
        result = await asyncio.to_thread(evaluate_trending_business, limit)
    except Exception as e:
        print(f"[business-eval] 数据库评估刷新失败，尝试实时评估: {e}")
        live_items = await asyncio.to_thread(scrape_github_trending, since="daily")
        items = await _evaluate_live_items(live_items, limit)
        return {"status": "partial_success", "date": datetime.now().strftime("%Y-%m-%d"), "items": items, "count": len(items), "summary": _summarize_eval(items), "source": "live"}
    if result.get("status") == "success":
        date_str = result.get("date") or datetime.now().strftime("%Y-%m-%d")
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT repo_name, repo_url, language, stars, summary,
                           d1, d2, d3, d4, total, level, recommendation, reasoning, eval_time
                    FROM trending_business_eval
                    WHERE scrape_date = %s
                    ORDER BY total DESC
                """, (date_str,))
                items = [dict(r) for r in c.fetchall()]
            return {"status": "success", "date": date_str, "items": items, "count": len(items), "summary": _summarize_eval(items), "source": "database"}
        except Exception as e:
            print(f"[business-eval] 评估已完成但读取数据库失败: {e}")
    return result


@router.get("/baidu-hotsearch")
async def get_baidu_hotsearch():
    """实时爬取百度热搜"""
    return await asyncio.to_thread(_fetch_baidu_hotsearch_sync)
