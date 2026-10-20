"""Public Chinese developer-community trend aggregation."""
from __future__ import annotations

import time

import requests
from bs4 import BeautifulSoup

from crawlers.baidu_crawler import _fetch_baidu_hotsearch_sync

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept-Language": "zh-CN,zh;q=0.9"}
TECH_WORDS = ("AI", "人工智能", "大模型", "模型", "Agent", "智能体", "云", "数据库", "编程", "开发", "开源", "芯片", "算法", "Python", "Java", "鸿蒙", "机器人", "科技")
_cache: tuple[float, list[dict]] = (0, [])


def _tech(items: list[dict], limit: int = 8) -> list[dict]:
    matched = [item for item in items if any(word.casefold() in f'{item.get("title", "")} {item.get("summary", "")}'.casefold() for word in TECH_WORDS)]
    return (matched or items)[:limit]


def _csdn() -> list[dict]:
    rows = requests.get("https://blog.csdn.net/phoenix/web/blog/hotRank?page=0&pageSize=30", headers=HEADERS, timeout=12).json().get("data", [])
    return _tech([{"source": "CSDN", "title": row.get("articleTitle", ""), "summary": f'热度 {row.get("pcHotRankScore") or row.get("hotRankScore") or "—"} · 阅读 {row.get("viewCount") or 0}', "url": row.get("articleDetailUrl", "")} for row in rows])


def _tencent() -> list[dict]:
    soup = BeautifulSoup(requests.get("https://developer.cloud.tencent.com/", headers=HEADERS, timeout=12).text, "html.parser")
    items = []
    for link in soup.select("a.cdc-article-panel-response2__title[href]"):
        href, title = link.get("href", ""), link.get_text(" ", strip=True)
        desc = link.find_next("a", class_="cdc-article-panel-response2__desc")
        if title and href:
            items.append({"source": "腾讯云社区", "title": title, "summary": desc.get_text(" ", strip=True) if desc else "", "url": href})
    return _tech(items)


def _baidu() -> list[dict]:
    return _tech([{"source": "百度热搜", "title": row.get("title", ""), "summary": f'热搜指数 {row.get("hot") or "—"}', "url": row.get("link", "")} for row in _fetch_baidu_hotsearch_sync()])


def _zhihu() -> list[dict]:
    rows = requests.get("https://api.zhihu.com/topstory/hot-lists/total?limit=30", headers=HEADERS, timeout=12).json().get("data", [])
    items = []
    for row in rows:
        target = row.get("target") or {}
        title = target.get("title") or ""
        if title:
            items.append({"source": "知乎", "title": title, "summary": row.get("detail_text") or "知乎热榜", "url": f'https://www.zhihu.com/question/{target.get("id")}'})
    return _tech(items)


def get_community_insights(force: bool = False) -> dict:
    global _cache
    if not force and time.time() - _cache[0] < 900:
        items = _cache[1]
    else:
        items = []
        for fetch in (_zhihu, _baidu, _tencent, _csdn):
            try:
                items.extend(fetch())
            except Exception:
                continue
        _cache = (time.time(), items)
    sources = ["知乎", "百度热搜", "腾讯云社区", "CSDN"]
    return {"items": items, "count": len(items), "sources": [{"name": source, "count": sum(item["source"] == source for item in items)} for source in sources]}
