"""A source-backed Radar snapshot from the signals currently collected by InsightPro."""
from __future__ import annotations
from datetime import date, datetime, timedelta
from functools import lru_cache
import logging
import re
import time
from urllib.parse import urlsplit, urlunsplit
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


VENDORS = ("OpenAI", "Anthropic", "Google", "Microsoft", "AWS", "阿里云", "腾讯云", "火山引擎", "华为云", "Meta", "行业动态")
VENDOR_ALIASES = {
    "openai": "OpenAI", "anthropic": "Anthropic", "claude": "Anthropic", "google": "Google", "gemini": "Google",
    "microsoft": "Microsoft", "azure": "Microsoft", "aws": "AWS", "amazon": "AWS", "阿里云": "阿里云", "alibaba": "阿里云",
    "aliyun": "阿里云", "腾讯云": "腾讯云", "tencent": "腾讯云", "火山引擎": "火山引擎", "volcengine": "火山引擎",
    "豆包": "火山引擎", "华为云": "华为云", "huawei": "华为云", "meta": "Meta", "facebook": "Meta",
}
TYPE_RULES = (
    ("商业动作", ("收购", "融资", "投资", "合作", "战略", "acqui", "funding", "partner", "investment")),
    ("解决方案", ("解决方案", "solution", "行业方案")),
    ("GitHub 技术", ("github", "开源", "open source", "repository", "repo")),
    ("社区动态", ("社区", "开发者", "知乎", "csdn", "热搜")),
    ("模型", ("模型", "大模型", "llm", "gpt-", "claude ", "gemini", "qwen", "deepseek")),
    ("AI 应用", ("ai 应用", "应用", "app", "copilot", "workbuddy", "chatgpt", "claude code", "dots")),
    ("产品发布", ("发布", "推出", "上线", "launch", "introduc", "announc", "release", "更新")),
)


def _normal_url(value: str) -> str:
    try:
        parsed = urlsplit(value.strip())
        if parsed.scheme and parsed.netloc:
            return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), "", ""))
    except ValueError:
        pass
    return ""


def _event_vendor(vendor: str, title: str, url: str) -> str:
    text = f"{vendor} {title} {url}".casefold()
    for alias, canonical in VENDOR_ALIASES.items():
        matched = alias in text if re.search(r"[^\x00-\x7f]", alias) else bool(re.search(rf"\b{re.escape(alias)}\b", text))
        if matched:
            return canonical
    host = urlsplit(url).hostname or ""
    if host.endswith("openai.com"): return "OpenAI"
    if host.endswith("anthropic.com"): return "Anthropic"
    if host.endswith("fb.com"): return "Meta"
    if host.endswith("google.com"): return "Google"
    if host.endswith("microsoft.com") or host.endswith("azure.com"): return "Microsoft"
    if host.endswith("amazon.com") or host.endswith("aws.amazon.com"): return "AWS"
    if host.endswith("aliyun.com") or host.endswith("alibabacloud.com"): return "阿里云"
    if host.endswith("tencent.com") or host.endswith("tencentcloud.com"): return "腾讯云"
    if host.endswith("volcengine.com") or host.endswith("doubao.com"): return "火山引擎"
    if host.endswith("huawei.com") or host.endswith("huaweicloud.com"): return "华为云"
    return "行业动态"


def _event_type(board: str, category: str, title: str, summary: str) -> str:
    if board == "github": return "GitHub 技术"
    if board == "community": return "社区动态"
    if board == "apps": return "AI 应用"
    if board == "solutions": return "解决方案"
    text = f"{category} {title} {summary}".casefold()
    return next((label for label, words in TYPE_RULES if any(word in text for word in words)), "商业动作" if board == "competitors" else "产品发布")


def _one_sentence(value: str, fallback: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text or text.startswith("{summary") or text.startswith("{\"summary"):
        return fallback
    match = re.search(r"[。！？!?](?:\s|$)", text)
    return (text[:match.end()].strip() if match else text[:115].rstrip("，,；;。 ") + ("。" if len(text) > 115 else ""))


def build_intelligence_radar(now: datetime | None = None) -> dict:
    """Build a seven-day, cross-board event feed and merge duplicate source links."""
    now = now or datetime.now(ZoneInfo("Asia/Shanghai"))
    today = now.date()
    since = (today - timedelta(days=6)).isoformat()
    until = today.isoformat()
    raw: list[dict] = []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT n.vendor, n.title, n.summary, n.link AS url,
                                 COALESCE(n.published_date::text, n.scrape_date::text) AS happened_at,
                                 'competitors' AS board, COALESCE(n.category, '') AS category, a.analysis AS why_detail
                          FROM competitor_news n LEFT JOIN intelligence_analysis a
                            ON a.kind='competitor_update' AND a.source_key=n.link || '::' || n.title
                          WHERE COALESCE(n.published_date::text, n.scrape_date::text) BETWEEN %s AND %s
                          UNION ALL
                          SELECT vendor, title, summary, url, crawl_date AS happened_at,
                                 'competitors' AS board, COALESCE(category, '') AS category, NULL AS why_detail
                          FROM cloud_vendor_news WHERE crawl_date BETWEEN %s AND %s""", (since, until, since, until))
        raw.extend(dict(row) for row in cursor.fetchall())
        cursor.execute("""SELECT vendor, name AS title, COALESCE(summary, source_text, '') AS summary, url,
                                 COALESCE(published_at, source_fetched_at::date::text) AS happened_at,
                                 'apps' AS board, COALESCE(category, '') AS category, opportunity AS why_detail
                          FROM vendor_ai_applications
                          WHERE LEFT(COALESCE(published_at, source_fetched_at::date::text), 10) BETWEEN %s AND %s
                            AND kind!='product'""", (since, until))
        raw.extend(dict(row) for row in cursor.fetchall())
        cursor.execute("""SELECT vendor, title, COALESCE(change_summary, source_description, '') AS summary, url,
                                 last_changed_date AS happened_at, 'solutions' AS board, COALESCE(category, '') AS category
                          FROM aliyun_solutions WHERE last_changed_date BETWEEN %s AND %s AND is_active AND NOT is_baseline""", (since, until))
        raw.extend(dict(row) for row in cursor.fetchall())
        cursor.execute("""SELECT '' AS vendor, g.repo_name AS title, COALESCE(e.summary_zh, e.summary, g.description, '') AS summary,
                                 g.repo_url AS url, g.scrape_date AS happened_at, 'github' AS board,
                                 COALESCE(g.category, '') AS category, e.reasoning AS why_detail
                          FROM github_trending g LEFT JOIN trending_business_eval e
                            ON e.scrape_date=g.scrape_date AND e.repo_name=g.repo_name
                          WHERE g.scrape_date BETWEEN %s AND %s AND g.category='daily'""", (since, until))
        raw.extend(dict(row) for row in cursor.fetchall())

    # Community APIs expose current ranked lists without publication timestamps; mark their first observation today.
    try:
        from services.community_insight_service import get_community_insights
        for item in get_community_insights().get("items", []):
            if item.get("title") and item.get("url"):
                raw.append({**item, "vendor": "", "happened_at": today.isoformat(), "board": "community", "category": "社区热点"})
    except Exception as exc:
        logger.warning("Community radar feed unavailable: %s", exc)

    merged: dict[str, dict] = {}
    title_index: dict[tuple[str, str], str] = {}
    url_index: dict[str, str] = {}
    source_counts: dict[str, set[str]] = {}
    for row in raw:
        title = re.sub(r"\s+", " ", str(row.get("title") or "")).strip()
        if not title:
            continue
        day = str(row.get("happened_at") or "")[:10]
        try:
            event_day = date.fromisoformat(day)
        except ValueError:
            continue
        if event_day > today or (today - event_day).days > 6:
            continue
        board = str(row.get("board") or "")
        url = str(row.get("url") or "").strip()
        vendor = _event_vendor(str(row.get("vendor") or ""), title, url)
        kind = _event_type(board, str(row.get("category") or ""), title, str(row.get("summary") or ""))
        source = str(row.get("source") or "").strip()
        if not source:
            source = {"apps": "AI 应用发布库", "solutions": f"{vendor}方案目录", "competitors": str(row.get("vendor") or vendor), "github": "GitHub"}.get(board, "")
        if board == "solutions" and not source:
            source = vendor
        source = {"Alibaba Cloud": "阿里云官方", "Tencent Cloud": "腾讯云官方", "Volcengine": "火山引擎官方", "Huawei Cloud": "华为云官方", "Microsoft Azure": "Microsoft 官方"}.get(source, source)
        canonical = _normal_url(url)
        title_key = re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", title.casefold())
        identity = (vendor, title_key)
        key = (url_index.get(canonical, "") if canonical else "") or title_index.get(identity, "")
        key = key or (f"url:{canonical}" if canonical else f"title:{vendor}:{title_key}")
        fallback_why = {"商业动作": "这项动作可能改变厂商竞争关系或市场资源配置。", "解决方案": "这项方案变化可能影响客户的技术选型与交付路径。", "GitHub 技术": "这项技术进入趋势榜，值得观察其采用与生态扩展。", "社区动态": "社区关注度变化可作为开发者需求的早期信号。", "模型": "模型能力变化可能影响应用效果与推理成本。", "AI 应用": "新应用或功能可能改变用户入口与工作流程。", "产品发布": "新产品或功能发布，值得跟踪后续可用性与采用情况。"}[kind]
        source_url = canonical or url
        source_name = source or ("GitHub" if board == "github" else "社区")
        if key not in merged:
            short = title
            if board == "apps" and not re.search(r"发布|推出|上线|更新|launch|release", short, re.I): short += " 发布"
            elif board == "github": short += " 上榜"
            elif board == "solutions": short += " 更新"
            short = short[:10].rstrip() + ("…" if len(short) > 10 else "")
            merged[key] = {"id": key, "title": title, "short_title": short, "vendor": vendor,
                           "happened_at": day, "type": kind, "summary": _one_sentence(row.get("summary", ""), "来源暂未提供摘要。"),
                           "why": _one_sentence(row.get("why_detail", ""), fallback_why), "importance": 3, "board": board,
                           "sources": [], "related": []}
        title_index[identity] = key
        if canonical:
            url_index[canonical] = key
        event = merged[key]
        if all(existing["name"] != source_name for existing in event["sources"]):
            event["sources"].append({"name": source_name, "url": source_url})
        if event_day > date.fromisoformat(event["happened_at"]):
            event["happened_at"] = day
            event["summary"] = _one_sentence(row.get("summary", ""), event["summary"])
        if board in ("apps", "solutions", "competitors"):
            event["board"] = board
            event["vendor"] = vendor
            event["type"] = kind
            event["summary"] = _one_sentence(row.get("summary", ""), event["summary"])
        source_counts.setdefault(board, set()).add(key)

    events = list(merged.values())
    for event in events:
        text = f"{event['title']} {event['summary']}".casefold()
        event["importance"] = 5 if any(word in text for word in ("发布", "上线", "融资", "收购", "发布会", "launch", "release")) else 4 if event["type"] in ("模型", "解决方案", "商业动作") else 3
        event["is_multi_source"] = len(event["sources"]) > 1
    events.sort(key=lambda item: (item["importance"], item["happened_at"]), reverse=True)
    for event in events:
        event["related"] = [{"id": candidate["id"], "title": candidate["title"]}
                            for candidate in events if candidate["id"] != event["id"] and candidate["vendor"] == event["vendor"]][:3]

    boards = []
    board_names = {"github": ("GitHub", "/insights/hotspots", "个项目进入趋势榜"), "apps": ("AI 应用", "/insights/app-launches", "条应用发布或更新"),
                   "solutions": ("解决方案", "/insights/solutions", "项方案目录变化"), "community": ("社区", "/insights/community", "条社区热点"),
                   "competitors": ("厂商动态", "/insights/competitors", "条厂商动态")}
    for key, (name, href, phrase) in board_names.items():
        count = len(source_counts.get(key, set()))
        newest = next((event for event in events if event["board"] == key), None)
        unit = {"github": "个项目", "apps": "条应用", "solutions": "项方案", "community": "条社区热点", "competitors": "条厂商动态"}[key]
        boards.append({"key": key, "name": name, "href": href, "count": count,
                       "change": f"{newest['short_title']}" if newest else "近 7 天暂无新增",
                       "unit": unit})
    today_events = [event for event in events if event["happened_at"] == today.isoformat()]
    highlights = (today_events or events)[:5]
    return {"as_of": now.isoformat(timespec="minutes"), "today_count": len(today_events),
            "priority_count": sum(event["importance"] >= 4 for event in events),
            "vendor_count": len({event["vendor"] for event in events if event["vendor"] != "行业动态"}),
            "source_count": len({source["name"] for event in events for source in event["sources"]}),
            "vendors": list(VENDORS), "events": events[:48], "highlights": highlights,
            "highlights_scope": "today" if today_events else "week", "boards": boards}
