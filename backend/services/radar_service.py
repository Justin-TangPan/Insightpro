"""A source-backed Radar snapshot from the signals currently collected by InsightPro."""
from __future__ import annotations
from datetime import date, datetime, timedelta
from functools import lru_cache
import logging
import re
import time
from zoneinfo import ZoneInfo
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

from db import get_db
from services.intelligence_format import application, competitor, project

logger = logging.getLogger(__name__)


CATEGORIES = ("AI 应用", "Agent", "模型与技术", "AI Infra", "商业化与产业")
KEYWORDS = (
    ("Agent", ("agent", "智能体", "mcp", "computer use", "browser use")),
    ("AI Infra", ("gpu", "inference", "推理平台", "向量数据库", "vector db", "sandbox", "runtime", "云计算")),
    ("模型与技术", ("model", "模型", "多模态", "rag", "context", "训练", "推理", "llm")),
    ("AI 应用", ("app", "应用", "copilot", "browser", "搜索", "coding", "workspace", "产品")),
)


def classify_signal(title: str, summary: str = "") -> str:
    text = f"{title} {summary}".lower()
    return next((category for category, words in KEYWORDS if any(word in text for word in words)), "商业化与产业")


def _app_brief(tagline: str) -> tuple[str, str]:
    text = tagline.lower()
    if "personal ai memory" in text:
        return "个人 AI 记忆进入手机与可穿戴设备，尝试成为随身助手。", "观察持续记忆是否改变个人助手的使用方式。"
    if "switch ai agents" in text:
        return "切换 AI Agent 时保留工作背景，减少反复解释。", "关注跨 Agent 共享上下文能否降低使用门槛。"
    if "every coding agent" in text:
        return "集中管理多台设备上的编程 Agent。", "关注多 Agent 管理是否成为开发团队的新工作台。"
    if "agents" in text and "ux" in text:
        return "把 Agent 能力放进更易用的工作界面。", "关注 Agent 产品的易用性是否成为竞争点。"
    if any(word in text for word in ("dictation", "whisper", "speech", "voice", "audio")):
        return "AI 语音应用：让说话、录音或声音创作成为日常工作入口。", "关注语音交互是否比聊天框更自然。"
    if any(word in text for word in ("memory", "notes", "context", "remember")):
        return "AI 记忆与笔记应用：让个人信息持续参与后续任务。", "关注跨工具记忆是否成为产品的新入口。"
    if any(word in text for word in ("chatgpt", "learn", "duolingo", "tutor")):
        return "AI 学习与个人助手应用：把问答变成更主动的互动体验。", "关注对话之外的新交互是否提高使用频率。"
    if any(word in text for word in ("presentation", "video", "image", "design")):
        return "AI 内容应用：缩短演示、图像或视频的制作过程。", "关注内容创作流程是否出现新的交互方式。"
    if any(word in text for word in ("agent", "automate", "autonomous")):
        return "AI Agent 应用：让 AI 从回答问题走向执行任务。", "关注它能否稳定完成一个具体场景。"
    return "近期发布的 AI 应用，可从原始产品介绍判断具体用途。", "先验证目标用户与实际使用场景。"


def _parse_product_hunt_feed(xml: bytes, today: date) -> list[dict]:
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ElementTree.fromstring(xml)
    apps = []
    for entry in root.findall("a:entry", ns):
        title = (entry.findtext("a:title", "", ns) or "").strip()
        published = (entry.findtext("a:published", "", ns) or "")[:10]
        content = entry.findtext("a:content", "", ns) or ""
        first_paragraph = BeautifulSoup(content, "html.parser").find("p")
        tagline = first_paragraph.get_text(" ", strip=True) if first_paragraph else ""
        text = f"{title} {tagline}".lower()
        if not title or not tagline or not (today - timedelta(days=7)).isoformat() <= published <= today.isoformat():
            continue
        if not re.search(r"\b(ai|agent|agents|chatgpt|claude|whisper|llm)\b|artificial intelligence", text):
            continue
        if re.search(r"\b(model|models|gpu|api|sdk|server|infrastructure|benchmark|runtime|database|weights|trained|cli|linter|formatter)\b|\b\d{2,3}b\b", text):
            continue
        link = next((item.get("href", "") for item in entry.findall("a:link", ns) if item.get("rel") == "alternate"), "")
        if not link.startswith("https://www.producthunt.com/products/"):
            continue
        brief, why = _app_brief(f"{title} {tagline}")
        app = {"title": title, "summary": brief, "tagline": tagline, "why": why,
                     "category": "AI 应用", "source": "Product Hunt", "url": link, "day": published,
                     "evaluation": None, "action": "待核实"}
        app["intelligence"] = application({"title": title, "url": link, "source_text": tagline, "analysis": None})
        apps.append(app)
    return sorted(apps, key=lambda item: (
        sum(word in f'{item["title"]} {item["tagline"]}'.lower() for word in ("personal", "memory", "context", "agent", "phone", "wrist")),
        item["day"]), reverse=True)[:8]


@lru_cache(maxsize=2)
def _product_hunt_apps(refresh_window: int, today: date) -> list[dict]:
    try:
        response = requests.get("https://www.producthunt.com/feed", timeout=5,
                                headers={"User-Agent": "InsightPro Radar/1.0"})
        response.raise_for_status()
        return _parse_product_hunt_feed(response.content, today)
    except (requests.RequestException, ElementTree.ParseError) as error:
        logger.warning("Product Hunt feed unavailable: %s", error)
        return []


def _agent_launch_app(item: dict) -> dict:
    """Map an official AI-application launch record into the home-page app card shape."""
    return {"title": item.get("title") or "",
            "summary": item.get("source_text") or "",
            "tagline": item.get("source_text") or "",
            "why": item.get("analysis") or "",
            "category": "AI 应用",
            "source": item.get("vendor") or "Official",
            "url": item.get("url") or "",
            "day": item.get("published") or "",
            "evaluation": None,
            "action": "",
            "intelligence": application(item)}


def build_radar_snapshot(today: date | None = None) -> dict:
    today = today or datetime.now(ZoneInfo("Asia/Shanghai")).date()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT n.title, n.summary, n.link AS url, n.scrape_date AS day, n.vendor AS source,
                                 a.id AS analysis_id, a.analysis
                          FROM competitor_news n LEFT JOIN intelligence_analysis a
                            ON a.kind='competitor_update' AND a.source_key=n.link || '::' || n.title
                          WHERE n.scrape_date >= %s AND n.scrape_date <= %s
                          ORDER BY n.scrape_date DESC, n.id DESC""", ((today - timedelta(days=13)).isoformat(), today.isoformat()))
        news = [dict(row) for row in cursor.fetchall()]
        cursor.execute("""SELECT g.repo_name AS title, COALESCE(a.summary_zh, a.summary, e.summary_zh, e.summary, g.description) AS summary,
                                 g.repo_url AS url, g.scrape_date AS day, 'GitHub' AS source,
                                 COALESCE(a.total, e.total) AS evaluation, COALESCE(a.recommendation, e.recommendation) AS action,
                                 a.reasoning AS analysis, a.id AS analysis_id
                          FROM github_trending g LEFT JOIN trending_business_eval e
                            ON e.scrape_date=g.scrape_date AND e.repo_name=g.repo_name
                          LEFT JOIN trending_business_eval a ON a.id=e.analysis_id
                          WHERE g.scrape_date >= %s AND g.scrape_date <= %s AND g.category='daily'
                          ORDER BY g.scrape_date DESC, g.id DESC""", ((today - timedelta(days=13)).isoformat(), today.isoformat()))
        projects = [dict(row) for row in cursor.fetchall()]

    buckets = {name: {"name": name, "current": 0, "previous": 0, "direction": "—", "representative": ""} for name in CATEGORIES}
    events, seen = [], set()
    today_count = 0
    for row in news + projects:
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        day = str(row.get("day") or "")[:10]
        category = classify_signal(title, str(row.get("summary") or ""))
        key = (title.casefold(), day)
        if key in seen:
            continue
        seen.add(key)
        bucket = buckets[category]
        if day >= (today - timedelta(days=6)).isoformat():
            bucket["current"] += 1
            if not bucket["representative"]:
                bucket["representative"] = title
        else:
            bucket["previous"] += 1
        if day == today.isoformat():
            today_count += 1
        if day >= (today - timedelta(days=6)).isoformat():
            url = str(row.get("url") or "")
            event = {"title": title, "summary": str(row.get("summary") or "").removeprefix("Use: "), "category": category,
                     "source": row.get("source") or "", "url": url if url.startswith(("https://", "http://")) else "", "day": day,
                     "evaluation": row.get("evaluation"), "action": row.get("action") or ""}
            event["intelligence"] = (project({"repo_name": title, "repo_url": event["url"], "summary": event["summary"],
                                               "reasoning": row.get("analysis"), "analysis_id": row.get("analysis_id")})
                                     if row.get("source") == "GitHub" else
                                     competitor({"vendor": row.get("source") or "", "title": title,
                                                 "link": event["url"], "summary": event["summary"],
                                                 "analysis": row.get("analysis"), "analysis_id": row.get("analysis_id")}))
            events.append(event)
    try:
        from services import agent_launch_service
        launch_items, _ = agent_launch_service.snapshot()
        apps = [_agent_launch_app(item) for item in launch_items[:4]]
    except Exception as exc:
        logger.warning("Official AI application snapshot unavailable: %s", exc)
        apps = []
    for app in apps:
        buckets["AI 应用"]["current"] += 1
        if not buckets["AI 应用"]["representative"]:
            buckets["AI 应用"]["representative"] = app.get("title") or ""
    for bucket in buckets.values():
        current, previous = bucket["current"], bucket["previous"]
        bucket["direction"] = "↑" if current > previous and current >= 3 else "↓" if previous > current and previous >= 3 else "→" if current or previous else "—"
    official = [item for item in events if item["source"] != "GitHub"
                and re.search(r"\bAI\b|智能体|\bAgent\b|模型|推理", item["title"], re.I)
                and re.search(r"新品发布|产品发布|正式发布|推出|上线|发布|带来|launch|introduc|announc|generally available", item["title"], re.I)
                and not re.search(r"登录|元数据|调价|收费|价格|获评|leader|排名|报告|login|metadata|pricing", item["title"], re.I)]
    official.sort(key=lambda item: item["day"], reverse=True)
    top_signals = official[:3]
    return {"as_of": today.isoformat(), "today_count": today_count, "recent_count": sum(b["current"] for b in buckets.values()),
            "evaluated_count": sum(bool(row.get("evaluation")) for row in events), "categories": list(buckets.values()),
            "top_signals": top_signals, "apps": apps[:4]}
