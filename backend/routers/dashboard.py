"""Dashboard routes"""
import asyncio
import re
from datetime import datetime

from fastapi import APIRouter
from crawlers import get_homepage_stats, get_homepage_modules
from db import get_db
from services.ai_service import chat_complete
from services.radar_service import build_radar_snapshot

router = APIRouter()


@router.get("/radar/snapshot")
async def radar_snapshot():
    return await asyncio.to_thread(build_radar_snapshot)


@router.get("/dashboard/stats")
async def get_dashboard_stats():
    db_stats = get_homepage_stats()
    return {
        "kpis": [
            {"label": "Trending Projects", "value": str(db_stats.get("trending_today", 0)), "trend": "Today"},
            {"label": "AI Value Evaluation", "value": str(db_stats.get("evaluation_today", 0)), "trend": "Today"},
            {"label": "Solutions", "value": str(db_stats.get("solution_count", 0)), "trend": "Current"},
            {"label": "Solution Changes", "value": str(db_stats.get("solution_recent_count", 0)), "trend": "Last 7 days"},
        ],
        "serviceHealth": [
            {"service": "Crawler Service", "status": "healthy" if db_stats.get("last_crawl") else "unknown", "uptime": "N/A"},
            {"service": "Database", "status": "healthy", "uptime": "Running"},
            {"service": "API Service", "status": "healthy", "uptime": "Running"},
        ],
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source": "database",
    }


@router.get("/homepage/stats")
async def homepage_stats():
    return get_homepage_stats()


@router.get("/homepage/modules")
async def homepage_modules():
    return [{**module, "as_of": datetime.now().isoformat(timespec="minutes"), "status": "fresh" if module.get("items") else "empty"} for module in get_homepage_modules()]


def _one_sentence(text: str) -> str:
    cleaned = re.sub(r"^[#*\-\s]*(建议举措|建议|Recommendation)[:：\s]*", "", text or "", flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(' "“”')
    sentence = re.split(r"(?<=[。！？!?])", cleaned, maxsplit=1)[0][:120].strip()
    return sentence if sentence.endswith(("。", "！", "？", "!", "?")) else f"{sentence}。" if sentence else ""


def _homepage_recommendation(today: str) -> dict[str, str]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT recommendation FROM homepage_daily_recommendations WHERE insight_date=%s", (today,))
        stored = cursor.fetchone()
        if stored:
            return {"recommendation": stored["recommendation"], "source": "stored"}
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", (79110421,))
        cursor.execute("SELECT recommendation FROM homepage_daily_recommendations WHERE insight_date=%s", (today,))
        stored = cursor.fetchone()
        if stored:
            return {"recommendation": stored["recommendation"], "source": "stored"}
        cursor.execute("""SELECT repo_name, summary, recommendation FROM trending_business_eval
                          WHERE scrape_date=%s ORDER BY total DESC NULLS LAST""", (today,))
        projects = [dict(row) for row in cursor.fetchall()]
        cursor.execute("""SELECT vendor, title, COALESCE(NULLIF(change_summary, ''), summary) AS summary
                          FROM aliyun_solutions WHERE is_active=TRUE AND NOT is_baseline AND last_changed_date=%s
                          ORDER BY vendor, menu_order, id""", (today,))
        solutions = [dict(row) for row in cursor.fetchall()]
        cursor.execute("""SELECT vendor, title, summary FROM competitor_news
                          WHERE scrape_date=%s ORDER BY id DESC""", (today,))
        competitors = [dict(row) for row in cursor.fetchall()]

        sections = [
            "项目洞察：\n" + "\n".join(f"{item['repo_name']}：{item.get('summary') or ''}；{item.get('recommendation') or ''}" for item in projects)[:600],
            "云方案变化：\n" + "\n".join(f"{item.get('vendor') or ''} {item['title']}：{item.get('summary') or ''}" for item in solutions)[:600],
            "友商动态：\n" + "\n".join(f"{item.get('vendor') or ''} {item['title']}：{item.get('summary') or ''}" for item in competitors)[:600],
        ]
        if not projects and not solutions and not competitors:
            return {"recommendation": "今日洞察仍在汇总，建议稍后再查看行动建议。", "source": "fallback"}
        # ponytail: balanced caps keep every source represented and the homepage response below proxy timeout.
        context = "\n\n".join(sections)
        try:
            generated = _one_sentence(chat_complete(
                system_prompt="你是技术解决方案负责人。综合当天全部项目洞察、云厂商方案变化和友商动态，提炼跨来源的共性机会，只输出一句简洁、具体、可执行的中文建议。不得复述单条建议或只推荐某一个项目；不要标题、列表、背景复述或 Markdown。",
                user_prompt=context,
                temperature=0.2,
                max_tokens=1024,
                timeout=25,
            ))
            if generated:
                cursor.execute("INSERT INTO homepage_daily_recommendations (insight_date, recommendation) VALUES (%s, %s)", (today, generated))
                return {"recommendation": generated, "source": "ai"}
        except Exception:
            pass
        fallback = next((item.get("recommendation") for item in projects if item.get("recommendation")), "")
        recommendation = _one_sentence(fallback) or "优先验证今日高价值项目与客户场景的匹配度，再决定是否进入方案实践。"
        cursor.execute("INSERT INTO homepage_daily_recommendations (insight_date, recommendation) VALUES (%s, %s)", (today, recommendation))
        return {"recommendation": recommendation, "source": "fallback"}


@router.get("/homepage/recommendation")
async def homepage_recommendation():
    today = datetime.now().strftime("%Y-%m-%d")
    result = await asyncio.to_thread(_homepage_recommendation, today)
    return {**result, "as_of": datetime.now().isoformat(timespec="minutes")}
