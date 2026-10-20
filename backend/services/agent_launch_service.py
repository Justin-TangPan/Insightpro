"""Discover official AI application launches and analyze their source text."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from urllib.parse import urlparse
from xml.etree import ElementTree
import logging
import re
import time

import requests
from bs4 import BeautifulSoup
from services import ai_service
from db import get_db
from settings import settings

logger = logging.getLogger(__name__)
HEADERS = {"User-Agent": "InsightPro/1.0"}
SEEDS = (
    ("Meta", "Muse", "2026-09-08", "https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/"),
    ("OpenAI", "dots", "2026-09-29", "https://openai.com/index/introducing-dots/"),
    ("Tencent Cloud", "Tencent productivity Agent suite", "2026-06-05", "https://www.tencent.com/en-us/articles/2202350.html"),
    ("Alibaba Cloud", "Qwen Intelligence", "2026-09-25", "https://www.alibabacloud.com/blog/alibaba-launches-qwen-intelligence-to-power-next-generation-agentic-smartphones_603597"),
    ("Anthropic", "Agents for financial services", "2026-05-05", "https://www.anthropic.com/news/finance-agents"),
    ("Google", "Gemini app becomes more agentic", "2026-05-19", "https://blog.google/innovation-and-ai/products/gemini-app/next-evolution-gemini-app/"),
)
PRODUCT_SEEDS = (
    ("Tencent Cloud", "WorkBuddy", "https://cloud.tencent.com/product/workbuddy"),
    ("Tencent Cloud", "WorkBuddy Enterprise", "https://cloud.tencent.com/product/workbuddy-enterprise"),
    ("Tencent Cloud", "CodeBuddy", "https://cloud.tencent.com/product/acc"),
    ("Alibaba Cloud", "Tongyi Qianwen", "https://tongyi.aliyun.com/"),
    ("Alibaba Cloud", "Bailian", "https://bailian.aliyun.com/"),
    ("Volcengine", "豆包工作", "https://docs.volcengine.com/docs/ark/use-managed-agents-in-doubao-work?lang=en"),
    ("Volcengine", "豆包", "https://www.doubao.com/"),
    ("Volcengine", "扣子 Coze", "https://www.coze.cn/"),
    ("MiniMax", "Hailuo", "https://hailuoai.com/"),
    ("GLM", "Z.ai Agent", "https://chat.z.ai/"),
    ("DeepSeek", "DeepSeek Harness", "https://www.deepseek.com/en/harness/"),
    ("Kimi", "Kimi Claw", "https://www.kimi.com/bot"),
    ("AWS", "Amazon Q Developer", "https://aws.amazon.com/q/developer/"),
    ("Microsoft Azure", "Microsoft Copilot Agents", "https://www.microsoft.com/en/copilot/agents"),
    ("Anthropic", "Claude Code", "https://www.anthropic.com/claude-code"),
    ("OpenAI", "ChatGPT", "https://openai.com/chatgpt/"),
)
EXCLUDED_APPLICATION_URLS = {
    "https://aws.amazon.com/bedrock/",  # Model platform, not an application.
    "https://about.fb.com/news/2026/10/introducing-muse-wonder-models/",
    "https://www.alibabacloud.com/blog/alibaba-unveils-roadmap-on-full-stack-ai-strategy-from-chips-cloud-infrastructure-models-to-agents_603589",
    "https://www.alibabacloud.com/blog/alibaba-unveils-agentic-computer-ai-wearables-and-more-at-2026-apsara-conference_603599",
    "https://docs.volcengine.com/docs/ark/use-managed-agents-in-doubao-work?lang=en",  # Source contains no product details.
    "https://tongyi.aliyun.com/",  # Model laboratory site, not a specific application.
    "https://www.alibabacloud.com/blog/alibaba-launches-qwen-intelligence-to-power-next-generation-agentic-smartphones_603597",
}
SEED_EXCERPTS = {
    "https://openai.com/index/introducing-dots/": (
        "OpenAI introduced dots on September 29, 2026. Dots are always-on personal agents powered by GPT-6 Astra. "
        "They have their own cloud computer and browser, can connect to apps, and work toward user goals. "
        "Users can inspect their work and approve actions. Rollout begins for Pro, Business Premium, and Enterprise "
        "in eligible markets; broader availability is planned."
    ),
}
VENDOR_HOSTS = {"about.fb.com": "Meta", "openai.com": "OpenAI", "www.anthropic.com": "Anthropic",
                "blog.google": "Google", "aws.amazon.com": "AWS", "azure.microsoft.com": "Microsoft Azure",
                "cn.aliyun.com": "Alibaba Cloud", "www.aliyun.com": "Alibaba Cloud",
                "www.alibabacloud.com": "Alibaba Cloud", "cloud.tencent.com": "Tencent Cloud",
                "www.tencent.com": "Tencent Cloud", "docs.volcengine.com": "Volcengine",
                "www.volcengine.com": "Volcengine", "www.doubao.com": "Volcengine", "www.coze.cn": "Volcengine",
                "tongyi.aliyun.com": "Alibaba Cloud", "bailian.aliyun.com": "Alibaba Cloud",
                "hailuoai.com": "MiniMax", "www.minimaxi.com": "MiniMax",
                "chat.z.ai": "GLM", "z.ai": "GLM",
                "www.deepseek.com": "DeepSeek", "www.kimi.com": "Kimi",
                "www.microsoft.com": "Microsoft Azure"}
APP_WORDS = re.compile(r"agent|智能体|assistant|助手|copilot|dots?|muse|claude|gemini|claw|harness|应用|app", re.I)
MODEL_ONLY = re.compile(r"\bmodel\b|\bhaiku\b|\bsonnet\b|\bopus\b|\bargon\b|模型", re.I)
LAUNCH_WORDS = re.compile(r"launch|introduc|releas|announc|unveil|debut|new |发布|推出|上线|全新", re.I)
MONITORED = ("Tencent Cloud", "Alibaba Cloud", "Volcengine", "Anthropic", "OpenAI", "GLM", "DeepSeek", "Kimi", "MiniMax", "Meta", "Google", "AWS", "Microsoft Azure")
_refresh_pool = ThreadPoolExecutor(max_workers=1)
_refresh_lock = Lock()
_refresh_future = None
_refresh_hour = None


def discover() -> list[dict]:
    found = {url: {"vendor": vendor, "title": title, "published": published, "url": url, "kind": "launch"}
             for vendor, title, published, url in SEEDS}
    found.update({url: {"vendor": vendor, "title": title, "published": "", "url": url, "kind": "product"}
                  for vendor, title, url in PRODUCT_SEEDS})
    try:
        response = requests.get("https://about.fb.com/wp-json/wp/v2/search", params={"search": "agent", "per_page": 30}, headers=HEADERS, timeout=10)
        response.raise_for_status()
        for item in response.json():
            url = item.get("url", "").split("?", 1)[0]
            if urlparse(url).hostname == "about.fb.com" and "/news/" in url:
                title = BeautifulSoup(item.get("title", ""), "html.parser").get_text(" ", strip=True)
                if re.search(r"agent|muse|智能体", title, re.I):
                    found.setdefault(url, {"vendor": "Meta", "title": title, "published": "", "url": url})
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Meta launch discovery failed: %s", exc)
    try:
        response = requests.get("https://openai.com/sitemap.xml/product/", headers=HEADERS, timeout=10)
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        for node in root.findall(".//{*}url"):
            url = node.findtext("{*}loc", "")
            if urlparse(url).hostname == "openai.com" and re.search(r"agent|dot|assistant", url, re.I):
                found.setdefault(url, {"vendor": "OpenAI", "title": "", "published": "", "url": url})
    except (requests.RequestException, ElementTree.ParseError) as exc:
        logger.warning("OpenAI launch discovery failed: %s", exc)
    try:
        response = requests.get("https://www.anthropic.com/sitemap.xml", headers=HEADERS, timeout=10)
        response.raise_for_status()
        for node in ElementTree.fromstring(response.content).findall(".//{*}url"):
            url = node.findtext("{*}loc", "")
            if urlparse(url).hostname == "www.anthropic.com" and "/news/" in url and APP_WORDS.search(url):
                found.setdefault(url, {"vendor": "Anthropic", "title": "", "published": "", "url": url})
    except (requests.RequestException, ElementTree.ParseError) as exc:
        logger.warning("Anthropic launch discovery failed: %s", exc)
    try:
        response = requests.get("https://blog.google/innovation-and-ai/technology/ai/rss/", headers=HEADERS, timeout=10)
        response.raise_for_status()
        for node in ElementTree.fromstring(response.content).findall("./channel/item"):
            title, url = node.findtext("title", ""), node.findtext("link", "")
            if urlparse(url).hostname == "blog.google" and APP_WORDS.search(title):
                found.setdefault(url, {"vendor": "Google", "title": title, "published": "", "url": url})
    except (requests.RequestException, ElementTree.ParseError) as exc:
        logger.warning("Google launch discovery failed: %s", exc)
    try:
        response = requests.get("https://www.kimi.com/sitemap.xml", headers=HEADERS, timeout=10)
        response.raise_for_status()
        for node in ElementTree.fromstring(response.content).findall(".//{*}url"):
            url = node.findtext("{*}loc", "")
            if urlparse(url).hostname == "www.kimi.com" and re.search(r"/(agent|agent-swarm|bot)/?$", url):
                found.setdefault(url, {"vendor": "Kimi", "title": "Kimi Agent", "published": "", "url": url, "kind": "product"})
    except (requests.RequestException, ElementTree.ParseError) as exc:
        logger.warning("Kimi product discovery failed: %s", exc)
    for sitemap in ("https://www.tencent.com/post-sitemap.xml", "https://www.tencent.com/post-sitemap2.xml"):
        try:
            response = requests.get(sitemap, headers=HEADERS, timeout=10)
            response.raise_for_status()
            for node in ElementTree.fromstring(response.content).findall(".//{*}url"):
                url = node.findtext("{*}loc", "")
                if urlparse(url).hostname == "www.tencent.com" and re.search(r"agent|workbuddy|yuanbao|qclaw", url, re.I):
                    found.setdefault(url, {"vendor": "Tencent Cloud", "title": "", "published": "", "url": url})
        except (requests.RequestException, ElementTree.ParseError) as exc:
            logger.warning("Tencent launch discovery failed: %s", exc)
    try:
        response = requests.get("https://www.alibabacloud.com/blog", headers=HEADERS, timeout=10)
        response.raise_for_status()
        for link in BeautifulSoup(response.text, "html.parser").select("a[href]"):
            title, url = link.get_text(" ", strip=True), link.get("href", "")
            if urlparse(url).hostname == "www.alibabacloud.com" and "/blog/" in url and APP_WORDS.search(title) and re.search(r"launch|introduc|release|new|unveil", title, re.I):
                found.setdefault(url, {"vendor": "Alibaba Cloud", "title": title, "published": "", "url": url})
    except requests.RequestException as exc:
        logger.warning("Alibaba launch discovery failed: %s", exc)
    try:
        from db import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""SELECT vendor, title, link AS url, COALESCE(published_date::text, scrape_date::text) AS published
                              FROM competitor_news WHERE scrape_date >= %s ORDER BY scrape_date DESC LIMIT 200""",
                           ((datetime.now(timezone.utc) - timedelta(days=60)).date().isoformat(),))
            for row in cursor.fetchall():
                row = dict(row)
                url = row["url"].split("?", 1)[0] if row.get("url") else ""
                if VENDOR_HOSTS.get(urlparse(url).hostname) == row["vendor"] and APP_WORDS.search(row["title"] or "") and re.search(r"发布|推出|上线|launch|introduc|announc|release|new|全新", row["title"] or "", re.I):
                    found.setdefault(url, {**row, "url": url})
    except Exception as exc:
        logger.warning("Cloud vendor AI application discovery failed: %s", exc)
    selected, counts = [], {}
    for item in found.values():
        if item["url"] in EXCLUDED_APPLICATION_URLS:
            continue
        vendor = item["vendor"]
        if counts.get(vendor, 0) < 1:
            selected.append(item)
            counts[vendor] = 1
    for item in found.values():
        if item["url"] in EXCLUDED_APPLICATION_URLS:
            continue
        if item not in selected and counts.get(item["vendor"], 0) < 6:
            selected.append(item)
            counts[item["vendor"]] = counts.get(item["vendor"], 0) + 1
    return selected[:48]


def _source(item: dict) -> dict | None:
    url = item["url"]
    if url in EXCLUDED_APPLICATION_URLS or urlparse(url).scheme != "https" or urlparse(url).hostname not in VENDOR_HOSTS:
        return None
    try:
        response = requests.get(url, headers=HEADERS, timeout=12)
        response.raise_for_status()
        if urlparse(response.url).hostname not in VENDOR_HOSTS:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        article = soup.find("article") or soup.find("main") or soup
        if len(article.get_text(" ", strip=True)) < 200:
            article = soup
        for tag in article.find_all(["script", "style", "nav", "footer"]):
            tag.decompose()
        title_node = soup.find("h1") or soup.find("title")
        title = title_node.get_text(" ", strip=True) if title_node else item["title"]
        if item["title"] and (not APP_WORDS.search(title) or len(title) < 8):
            title = item["title"]
        description = (soup.find("meta", attrs={"name": "description"}) or {}).get("content", "")
        body = f"{description} {article.get_text(' ', strip=True)}"[:9000]
        if not body or (not APP_WORDS.search(title) and item.get("kind") != "product" and url not in {seed[3] for seed in SEEDS}) or (MODEL_ONLY.search(title) and not re.search(r"agent|智能体|assistant|助手|copilot|应用|app", title, re.I)) or (not item.get("kind") and not LAUNCH_WORDS.search(title)):
            return None
        return {**item, "title": title, "source_text": body}
    except requests.RequestException as exc:
        logger.warning("Agent source unavailable %s: %s", url, exc)
        if url in SEED_EXCERPTS:
            return {**item, "source_text": SEED_EXCERPTS[url]}
        return None


def analyze(item: dict) -> dict:
    result = {key: item[key] for key in ("vendor", "title", "published", "url")}
    result["kind"] = item.get("kind", "launch")
    result["source_text"] = item.get("source_text", "")[:300]
    result["analysis"] = None
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("ai_application:" + item["url"],))
            cursor.execute("SELECT id, analysis FROM intelligence_analysis WHERE kind='ai_application' AND source_key=%s", (item["url"],))
            existing = cursor.fetchone()
            if existing and _parse_structured(existing["analysis"]):
                result.update(analysis=existing["analysis"], analysis_id=existing["id"])
                _upsert_application(cursor, item, {"summary": existing["analysis"], "capability": "", "opportunity": "", "limitation": ""}, "done")
            elif settings.CHAT_API_KEY:
                if existing:
                    cursor.execute("DELETE FROM intelligence_analysis WHERE id=%s", (existing["id"],))
                analysis = _analyze_with_retry(item)
                if analysis:
                    fields = _parse_structured(analysis)
                    composed = _compose_analysis(fields)
                    cursor.execute("INSERT INTO intelligence_analysis (kind, source_key, analysis) VALUES ('ai_application',%s,%s) RETURNING id", (item["url"], composed))
                    result.update(analysis=composed, analysis_id=cursor.fetchone()["id"])
                    _upsert_application(cursor, item, fields, "done")
                else:
                    result["analysis"] = _fallback_analysis(item)
                    _upsert_application(cursor, item, {"summary": result["analysis"], "capability": "", "opportunity": "", "limitation": ""}, "failed")
    except Exception as exc:
        logger.warning("Agent analysis failed %s: %s", item["url"], exc)
    return result


def _fallback_analysis(item: dict) -> str:
    """Deterministic placeholder when the AI provider cannot summarize a launch."""
    vendor = item.get("vendor") or ""
    if item.get("kind") == "product":
        return f"{vendor} 官方产品页。AI 分析暂时不可用，请查看官方原文核实产品能力与适用场景。"
    published = item.get("published") or "发布日期待核实"
    return f"{vendor} 发布公告（{published}）。AI 分析暂时不可用，请查看官方原文。"


def _analyze_with_retry(item: dict) -> str | None:
    """Call the AI provider for a structured analysis, retrying with backoff."""
    delays = (2, 5, 10)
    for attempt, delay in enumerate(delays, start=1):
        try:
            analysis = ai_service.chat_complete(
                system_prompt="你是技术情报分析师。只依据给定官方原文，输出完整 JSON（不要 markdown 代码块），字段：summary（一句话概括产品/发布）、capability（能做什么）、opportunity（与云和智能体生态相关的机会）、limitation（一项尚需验证的限制）。用中文叙述，保留品牌、产品和模型的正式名称；普通英文术语译为中文。区分产品页、发布公告和未来计划；使用具体日期，避免今日、昨天、近日等相对时间；不要推测采用率，不要使用来源外事实。每个字段不超过100字。",
                user_prompt=f"厂商：{item['vendor']}\n标题：{item['title']}\n官方链接：{item['url']}\n原文：{item['source_text'][:600]}",
                max_tokens=1200, timeout=120, temperature=0.2,
            ).strip()
            if _parse_structured(analysis):
                return analysis
        except Exception as exc:
            logger.warning("Agent analysis attempt %d failed %s: %s", attempt, item["url"], exc)
        if attempt < len(delays):
            time.sleep(delay)
    return None


def _parse_structured(content: str) -> dict | None:
    """Accept complete Chinese prose or a complete structured response only."""
    data = ai_service.extract_json(content)
    if isinstance(data, dict):
        fields = {key: data.get(key, "") for key in ("summary", "capability", "opportunity", "limitation")}
        if all(isinstance(value, str) for value in fields.values()) and re.search(r"[\u4e00-\u9fff]", fields["summary"]):
            return {key: value.strip() for key, value in fields.items()}
    elif content and not content.lstrip().startswith(("{", "```")) and re.search(r"[\u4e00-\u9fff]", content):
        return {"summary": content.strip(), "capability": "", "opportunity": "", "limitation": ""}
    return None


def _compose_analysis(fields: dict) -> str:
    """Compose a single-line analysis from structured fields for the shared display contract."""
    parts = [fields[key] for key in ("capability", "opportunity", "limitation") if fields.get(key)]
    if parts:
        return "；".join(parts)
    return fields.get("summary") or ""


def _upsert_application(cursor, item: dict, fields: dict, status: str = "done") -> None:
    """Persist a discovered application with its structured analysis, upserting by (vendor, url)."""
    cursor.execute("""
        INSERT INTO vendor_ai_applications
            (vendor, name, url, kind, published_at, category, summary, capability, opportunity, limitation, source_text, analysis_status, analyzed_at, analysis_model)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s)
        ON CONFLICT (vendor, url) DO UPDATE SET
            name = EXCLUDED.name,
            kind = EXCLUDED.kind,
            published_at = EXCLUDED.published_at,
            category = EXCLUDED.category,
            summary = EXCLUDED.summary,
            capability = EXCLUDED.capability,
            opportunity = EXCLUDED.opportunity,
            limitation = EXCLUDED.limitation,
            source_text = EXCLUDED.source_text,
            analysis_status = EXCLUDED.analysis_status,
            analyzed_at = NOW(),
            analysis_model = EXCLUDED.analysis_model,
            updated_at = NOW()
    """, (item["vendor"], item.get("title"), item["url"], item.get("kind", "launch"),
          item.get("published") or None, None, fields.get("summary"), fields.get("capability"),
          fields.get("opportunity"), fields.get("limitation"), (item.get("source_text") or "")[:2000],
          status, settings.CHAT_MODEL))


def _read_structured() -> list[dict]:
    """Read persisted applications from the database, newest announcements first."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, vendor, name, url, kind, published_at, summary, capability, opportunity, limitation, source_text
                FROM vendor_ai_applications
                ORDER BY (published_at IS NULL OR published_at = '') ASC, published_at DESC, id DESC
                LIMIT 48
            """)
            rows = [dict(row) for row in cursor.fetchall()]
    except Exception as exc:
        logger.warning("Structured application read failed: %s", exc)
        return []
    items = []
    urls = {row["url"] for row in rows}
    for row in rows:
        if row["url"] in EXCLUDED_APPLICATION_URLS:
            continue
        if "/en/" in row["url"] and row["url"].replace("/en/", "/", 1) in urls:
            continue
        fields = {"summary": row.get("summary") or "", "capability": row.get("capability") or "",
                  "opportunity": row.get("opportunity") or "", "limitation": row.get("limitation") or ""}
        if not _parse_structured(fields["summary"]):
            fields = {key: "" for key in fields}
        title = row.get("name") or ""
        if not re.search(r"[\u4e00-\u9fff]", title) and len(title.split()) > 2 and fields["summary"]:
            title = fields["summary"].split("。", 1)[0][:64]
        items.append({"vendor": row["vendor"], "title": title,
                      "published": row.get("published_at") or "", "url": row["url"],
                      "kind": row.get("kind") or "launch", "source_text": (row.get("source_text") or "")[:300],
                      "analysis": _compose_analysis(fields), "analysis_id": row["id"],
                      "summary": fields["summary"], "capability": fields["capability"],
                      "opportunity": fields["opportunity"], "limitation": fields["limitation"]})
    return items


def analysis_progress() -> dict:
    """Report AI-application analysis progress for the admin console."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT count(*) AS total,
                       count(*) FILTER (WHERE analysis_status='done') AS done,
                       count(*) FILTER (WHERE analysis_status='failed') AS failed,
                       count(*) FILTER (WHERE analysis_status='pending') AS pending,
                       max(analyzed_at) AS last_analyzed_at
                FROM vendor_ai_applications
            """)
            summary = dict(cursor.fetchone())
            cursor.execute("""
                SELECT vendor, count(*) AS total,
                       count(*) FILTER (WHERE analysis_status='done') AS done
                FROM vendor_ai_applications
                GROUP BY vendor ORDER BY total DESC
            """)
            summary["by_vendor"] = [dict(row) for row in cursor.fetchall()]
        return summary
    except Exception as exc:
        logger.warning("AI application progress read failed: %s", exc)
        return {"total": 0, "done": 0, "failed": 0, "pending": 0, "last_analyzed_at": None, "by_vendor": []}


def _ingest() -> int:
    """Discover applications and persist identity + source snapshots as pending."""
    with ThreadPoolExecutor(max_workers=6) as pool:
        sources = [item for item in pool.map(_source, discover()) if item]
    ingested = 0
    with get_db() as conn:
        cursor = conn.cursor()
        for item in sources:
            cursor.execute("""
                INSERT INTO vendor_ai_applications
                    (vendor, name, url, kind, published_at, source_text, analysis_status, source_fetched_at)
                VALUES (%s,%s,%s,%s,%s,%s,'pending',NOW())
                ON CONFLICT (vendor, url) DO UPDATE SET
                    name = EXCLUDED.name,
                    kind = EXCLUDED.kind,
                    published_at = EXCLUDED.published_at,
                    source_text = EXCLUDED.source_text,
                    source_fetched_at = NOW(),
                    updated_at = NOW()
            """, (item["vendor"], item.get("title"), item["url"], item.get("kind", "launch"),
                  item.get("published"), (item.get("source_text") or "")[:2000]))
            ingested += 1
    return ingested


def _pending_rows(batch: int) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, vendor, name AS title, url, kind, published_at AS published, source_text
            FROM vendor_ai_applications
            WHERE analysis_status = 'pending'
            ORDER BY id LIMIT %s
        """, (batch,))
        return [dict(row) for row in cursor.fetchall()]


def _enrich(batch: int) -> int:
    """Analyze pending applications serially, with a short gap to avoid provider rate limits."""
    rows = _pending_rows(batch)
    if not rows:
        return 0
    for row in rows:
        analyze({"vendor": row["vendor"], "title": row["title"], "url": row["url"],
                 "kind": row["kind"], "published": row["published"], "source_text": row["source_text"]})
        time.sleep(3)
    return len(rows)


def _reset_failed() -> int:
    """Requeue previously failed analyses for a retry on the next pass."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE vendor_ai_applications SET analysis_status='pending' WHERE analysis_status='failed'")
        return cursor.rowcount


def latest() -> list[dict]:
    """Backfill the structured table incrementally, then return what is persisted."""
    try:
        _ingest()
        for _round in range(3):
            _reset_failed()
            for _ in range(10):
                if _enrich(6) == 0:
                    break
    except Exception as exc:
        logger.warning("Agent backfill failed: %s", exc)
    return _read_structured()


def snapshot() -> tuple[list[dict], bool]:
    global _refresh_future, _refresh_hour
    hour = int(datetime.now(timezone.utc).timestamp() // 3600)
    with _refresh_lock:
        if _refresh_hour != hour or _refresh_future is None:
            _refresh_future = _refresh_pool.submit(latest)
            _refresh_hour = hour
        future = _refresh_future
    rows = _read_structured()
    if rows:
        return rows, not future.done()
    if future.done():
        try:
            items = future.result()
            if items:
                return items, False
        except Exception as exc:
            logger.warning("Agent discovery failed: %s", exc)
    fallback = [{"vendor": vendor, "title": title, "published": published, "url": url,
                 "kind": "launch", "analysis": _fallback_analysis({"vendor": vendor, "kind": "launch", "published": published})}
                for vendor, title, published, url in SEEDS]
    fallback += [{"vendor": vendor, "title": title, "published": "", "url": url,
                  "kind": "product", "analysis": _fallback_analysis({"vendor": vendor, "kind": "product"})}
                 for vendor, title, url in PRODUCT_SEEDS]
    return fallback, True
