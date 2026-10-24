"""Public Chinese developer-community trend aggregation."""
from __future__ import annotations

import time
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from crawlers.baidu_crawler import _fetch_baidu_hotsearch_sync
from services.intelligence_data_service import store_community_raw
from services.source_registry_service import list_sources, record_source_health

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept-Language": "zh-CN,zh;q=0.9"}
AI_TOPICS = {
    "Agent 与框架": ("ai agent", "智能体", "agent框架", "agent skill", "agent skills", "agentic", "mcp", "模型上下文协议", "langchain", "langgraph", "工作流编排", "多智能体"),
    "AI 应用": ("人工智能", "生成式ai", "ai应用", "ai助手", "copilot", "chatgpt", "claude", "openai", "anthropic", "豆包", "deepseek"),
    "模型与技术": ("大模型", "语言模型", "多模态模型", "基础模型", "llm", "推理模型", "模型训练", "模型微调", "rag", "向量数据库", "gemini", "qwen", "kimi"),
    "AI 开发工具": ("ai编程", "ai coding", "代码生成", "编程助手", "claude code", "cursor", "vibe coding", "代码智能体"),
    "AI Infra": ("ai infra", "gpu推理", "推理服务", "推理框架", "模型部署", "向量检索", "模型服务", "训练集群"),
}
_cache: tuple[float, list[dict], tuple[tuple[str, str], ...]] = (0, [], ())


def _contains(text: str, word: str) -> bool:
    word = word.casefold()
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", text)) if word.isascii() else word in text


def _tech(items: list[dict], limit: int = 8) -> list[dict]:
    matched = []
    for item in items:
        title = str(item.get("title") or "").casefold()
        text = f'{title} {item.get("summary", "")}'.casefold()
        category = next((name for name, words in AI_TOPICS.items() if any(_contains(text, word) for word in words)), None)
        title_has_ai_signal = any(_contains(title, word) for words in AI_TOPICS.values() for word in words)
        url = str(item.get("url") or "")
        try:
            parsed_url = urlsplit(url)
        except ValueError:
            continue
        if category and title_has_ai_signal and parsed_url.scheme in ("http", "https") and parsed_url.netloc:
            matched.append({**item, "topic_category": category,
                            "relevance": "high" if any(_contains(text, word) for word in ("ai", "人工智能", "agent", "大模型", "llm")) else "medium"})
    return matched[:limit]


def _csdn(base_url: str) -> list[dict]:
    rows = requests.get(base_url, headers=HEADERS, timeout=12).json().get("data", [])
    return _tech([{"source": "CSDN", "title": row.get("articleTitle", ""), "summary": f'热度 {row.get("pcHotRankScore") or row.get("hotRankScore") or "—"} · 阅读 {row.get("viewCount") or 0}', "url": row.get("articleDetailUrl", "")} for row in rows])


def _tencent(base_url: str) -> list[dict]:
    soup = BeautifulSoup(requests.get(base_url, headers=HEADERS, timeout=12).text, "html.parser")
    items = []
    for link in soup.select("a.cdc-article-panel-response2__title[href]"):
        href, title = link.get("href", ""), link.get_text(" ", strip=True)
        desc = link.find_next("a", class_="cdc-article-panel-response2__desc")
        if title and href:
            items.append({"source": "腾讯云社区", "title": title, "summary": desc.get_text(" ", strip=True) if desc else "", "url": href})
    return _tech(items)


def _baidu(base_url: str) -> list[dict]:
    return _tech([{"source": "百度热搜", "title": row.get("title", ""), "summary": f'热搜指数 {row.get("hot") or "—"}', "url": row.get("link", "")} for row in _fetch_baidu_hotsearch_sync(base_url)])


def _zhihu(base_url: str) -> list[dict]:
    rows = requests.get(base_url, params={"limit": 30}, headers=HEADERS, timeout=12).json().get("data", [])
    items = []
    for row in rows:
        target = row.get("target") or {}
        title = target.get("title") or ""
        if title:
            items.append({"source": "知乎", "title": title, "summary": row.get("detail_text") or "知乎热榜", "url": f'https://www.zhihu.com/question/{target.get("id")}'})
    return _tech(items)


FEEDS = {"community_zhihu": _zhihu, "community_baidu": _baidu, "community_tencent": _tencent, "community_csdn": _csdn}


def refresh_community_source(source_key: str) -> dict:
    global _cache
    source = next((item for item in list_sources() if item["source_key"] == source_key), None)
    if not source or source_key not in FEEDS:
        raise ValueError("Unsupported community source")
    if not source["enabled"]:
        raise ValueError("Community source is disabled")
    try:
        items = FEEDS[source_key](source.get("base_url") or "")
        observed_at = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="minutes")
        unique = {}
        for item in items:
            url = str(item.get("url") or "").split("#", 1)[0].rstrip("/")
            if url and url not in unique:
                unique[url] = {**item, "url": url, "published_at": item.get("published_at"), "observed_at": observed_at}
        items = list(unique.values())
        stored = store_community_raw(items)
    except Exception as error:
        record_source_health(source_key, "failed", str(error))
        raise
    record_source_health(source_key, "healthy" if items else "empty")
    _cache = (0, [], ())
    return {"status": "success", "source_key": source_key, "total": len(items), "stored": stored}


def get_community_insights(force: bool = False) -> dict:
    global _cache
    sources = {source["source_key"]: source for source in list_sources()
               if source["source_key"] in FEEDS and source["enabled"]}
    signature = tuple(sorted((key, source.get("base_url") or "") for key, source in sources.items()))
    if not force and time.time() - _cache[0] < 900 and _cache[2] == signature:
        items = _cache[1]
    else:
        items = []
        def safe_fetch(entry):
            source_key, base_url = entry
            try:
                return source_key, FEEDS[source_key](base_url), None
            except Exception as error:
                return source_key, [], str(error)
        with ThreadPoolExecutor(max_workers=4) as pool:
            for source_key, fetch_items, error in pool.map(safe_fetch, signature):
                record_source_health(source_key, "failed" if error else "healthy" if fetch_items else "empty", error)
                items.extend(fetch_items)
        observed_at = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="minutes")
        unique = {}
        for item in items:
            url = str(item.get("url") or "").split("#", 1)[0].rstrip("/")
            if url and url not in unique:
                unique[url] = {**item, "url": url, "published_at": item.get("published_at"), "observed_at": observed_at}
        items = list(unique.values())
        store_community_raw(items)
        _cache = (time.time(), items, signature)
    sources = ["知乎", "百度热搜", "腾讯云社区", "CSDN"]
    return {"items": items, "count": len(items), "sources": [{"name": source, "count": sum(item["source"] == source for item in items)} for source in sources]}
