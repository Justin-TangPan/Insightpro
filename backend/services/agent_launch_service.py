"""Discover official AI application launches and analyze their source text."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from urllib.parse import urlparse, urljoin
from xml.etree import ElementTree
import logging
import hashlib
import json
import re
import time

import requests
from bs4 import BeautifulSoup
from services import ai_service
from db import get_db
from settings import settings
from services.ai_app_sources import PRODUCTS, FEEDS, GITHUB_REPOSITORIES
from services.source_image import first_source_image

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
    "https://github.blog/changelog/2026/",  # Year archive, not an individual update.
}
SEED_EXCERPTS = {
    "https://openai.com/index/introducing-dots/": (
        "OpenAI introduced dots on September 29, 2026. Dots are always-on personal agents powered by GPT-6 Astra. "
        "They have their own cloud computer and browser, can connect to apps, and work toward user goals. "
        "Users can inspect their work and approve actions. Rollout begins for Pro, Business Premium, and Enterprise "
        "in eligible markets; broader availability is planned."
    ),
}
VENDOR_HOSTS = {"about.fb.com": "Meta", "openai.com": "OpenAI", "help.openai.com": "OpenAI", "developers.openai.com": "OpenAI", "www.anthropic.com": "Anthropic", "support.claude.com": "Anthropic", "claude.com": "Anthropic",
                "blog.google": "Google", "aws.amazon.com": "AWS", "azure.microsoft.com": "Microsoft Azure",
                "cn.aliyun.com": "Alibaba Cloud", "www.aliyun.com": "Alibaba Cloud",
                "www.alibabacloud.com": "Alibaba Cloud", "cloud.tencent.com": "Tencent Cloud",
                "www.tencent.com": "Tencent Cloud", "docs.volcengine.com": "Volcengine",
                "www.volcengine.com": "Volcengine", "www.doubao.com": "Volcengine", "www.coze.cn": "Volcengine",
                "tongyi.aliyun.com": "Alibaba Cloud", "bailian.aliyun.com": "Alibaba Cloud",
                "hailuoai.com": "MiniMax", "www.minimaxi.com": "MiniMax",
                "chat.z.ai": "GLM", "z.ai": "GLM",
                "www.deepseek.com": "DeepSeek", "www.kimi.com": "Kimi",
                "www.microsoft.com": "Microsoft Azure", "learn.microsoft.com": "Microsoft Azure",
                "github.blog": "Microsoft Azure", "kiro.dev": "AWS", "docs.coze.cn": "Volcengine",
                "z.ai": "GLM", "api-docs.deepseek.com": "DeepSeek", "www.minimaxi.com": "MiniMax",
                "www.alibabagroup.com": "Alibaba Cloud", "qoder.com": "Alibaba Cloud", "docs.qoder.com": "Alibaba Cloud",
                "www.minimax.cn": "MiniMax"}
APP_WORDS = re.compile(r"agent|智能体|assistant|助手|copilot|dots?|muse|claude|gemini|claw|harness|应用|app", re.I)
MODEL_ONLY = re.compile(r"\bmodel\b|\bhaiku\b|\bsonnet\b|\bopus\b|\bargon\b|模型", re.I)
LAUNCH_WORDS = re.compile(r"launch|introduc|releas|announc|unveil|debut|new |发布|推出|上线|全新", re.I)
MONITORED = ("Tencent Cloud", "Alibaba Cloud", "Volcengine", "Anthropic", "OpenAI", "GLM", "DeepSeek", "Kimi", "MiniMax", "Meta", "Google", "AWS", "Microsoft Azure")
PRODUCT_WORDS = re.compile(r"chatgpt|codex|dots|claude|cowork|gemini|notebook|flow|jules|antigravity|copilot|元宝|workbuddy|codebuddy|千问|qwen|夸克|钉钉|豆包|扣子|coze|glm|清言|z\.ai|deepseek|kimi|海螺|hailuo|minimax agent|meta ai|vibes|amazon q|kiro", re.I)
VENDOR_WORDS = {
    "OpenAI": re.compile(r"chatgpt|codex|dots", re.I),
    "Anthropic": re.compile(r"claude|cowork", re.I),
    "Google": re.compile(r"gemini|notebook|flow|jules|antigravity|stitch", re.I),
    "Tencent Cloud": re.compile(r"元宝|workbuddy|codebuddy", re.I),
    "Alibaba Cloud": re.compile(r"千问|qwen|夸克|钉钉|qoder", re.I),
    "Volcengine": re.compile(r"豆包|扣子|coze", re.I),
    "GLM": re.compile(r"智谱|清言|z\.ai|glm", re.I),
    "DeepSeek": re.compile(r"deepseek", re.I),
    "Kimi": re.compile(r"kimi", re.I),
    "MiniMax": re.compile(r"minimax agent|海螺|hailuo|星野", re.I),
    "Meta": re.compile(r"meta ai|vibes|muse", re.I),
    "AWS": re.compile(r"kiro|amazon q", re.I),
    "Microsoft Azure": re.compile(r"copilot", re.I),
}
DATE_ISO = re.compile(r"20\d{2}[-/]\d{1,2}[-/]\d{1,2}")
DATE_EN = re.compile(r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+20\d{2}", re.I)
_refresh_pool = ThreadPoolExecutor(max_workers=1)
_refresh_lock = Lock()
_refresh_future = None
_refresh_hour = None
FEED_HEALTH: dict[str, str] = {}


def _date(value: str) -> str:
    if re.match(r"^20\d{2}-\d{2}-\d{2}T", value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            result = parsed.astimezone(ZoneInfo("Asia/Shanghai")).date() if parsed.tzinfo else parsed.date()
            return result.isoformat() if result <= datetime.now(ZoneInfo("Asia/Shanghai")).date() else ""
        except ValueError:
            pass
    match = DATE_ISO.search(value.replace("年", "-").replace("月", "-").replace("日", ""))
    if match:
        parts = re.split(r"[-/]", match.group())
        try:
            result = datetime(int(parts[0]), int(parts[1]), int(parts[2])).date()
            return result.isoformat() if result <= datetime.now(ZoneInfo("Asia/Shanghai")).date() else ""
        except ValueError:
            return ""
    match = DATE_EN.search(value)
    if match:
        try:
            value = match.group().replace(",", "")
            for fmt in ("%B %d %Y", "%b %d %Y"):
                try:
                    result = datetime.strptime(value, fmt).date()
                    return result.isoformat() if result <= datetime.now(ZoneInfo("Asia/Shanghai")).date() else ""
                except ValueError:
                    pass
        except ValueError:
            return ""
    return ""


def _feed_items(feed: tuple[str, str, str, str]) -> list[dict]:
    vendor, product, feed_url, kind = feed
    FEED_HEALTH[feed_url] = "pending"
    try:
        response = requests.get(feed_url, headers=HEADERS, timeout=12)
        response.raise_for_status()
        if kind == "rss":
            root = ElementTree.fromstring(response.content)
            items = []
            for node in root.findall("./channel/item"):
                title, url = node.findtext("title", ""), node.findtext("link", "")
                if (vendor == "OpenAI" and "Product" not in [category.text for category in node.findall("category")]) or not VENDOR_WORDS[vendor].search(title) or VENDOR_HOSTS.get(urlparse(url).hostname) != vendor:
                    continue
                if vendor == "Google" and (re.search(r"\btips?\b|responsibly|for developers|\bmodel\b", title, re.I) and not re.search(r"\bapp\b|workspace|vids|meet|docs|sheets|slides|live|notebook", title, re.I)):
                    continue
                published = ""
                try:
                    from email.utils import parsedate_to_datetime
                    published = _date(parsedate_to_datetime(node.findtext("pubDate", "")).astimezone(ZoneInfo("Asia/Shanghai")).date().isoformat())
                except (TypeError, ValueError):
                    pass
                items.append({"vendor": vendor, "product": product, "title": title, "published": published,
                              "url": url, "kind": "launch", "source_text": BeautifulSoup(node.findtext("description", ""), "html.parser").get_text(" ", strip=True),
                              "image_url": first_source_image(node.findtext("description", ""), url), "feed_verified": True})
                if len(items) >= 12:
                    break
            return items
        soup = BeautifulSoup(response.content, "html.parser")
        if kind == "notes":
            items = []
            if "cloud.tencent.com/document/" in feed_url:
                for row in soup.select("tr"):
                    cells = row.find_all("td")
                    if len(cells) < 3:
                        continue
                    published = _date(cells[-1].get_text(" ", strip=True))
                    body = cells[1].get_text(" ", strip=True)[:1800]
                    if published and len(body) >= 40:
                        items.append({"vendor": vendor, "product": product, "title": f"{product} {cells[0].get_text(' ', strip=True)} 更新", "published": published,
                                      "url": f"{feed_url}#update-{published}-{len(items)}", "kind": "update", "source_text": body, "feed_verified": True})
                    if len(items) >= 8:
                        break
                return items
            if "developers.openai.com/codex/" in feed_url:
                for row in soup.select("li"):
                    body = row.get_text(" ", strip=True)
                    published = _date(body[:40])
                    if published and len(body) >= 40:
                        items.append({"vendor": vendor, "product": product, "title": body[:110], "published": published,
                                      "url": f"{feed_url}#update-{published}-{len(items)}", "kind": "update", "source_text": body[:1800], "feed_verified": True})
                    if len(items) >= 8:
                        break
                return items
            for heading in soup.select("h2, h3, h4"):
                heading_text = heading.get_text(" ", strip=True).replace("\u200b", "").strip()
                published = _date(heading_text)
                if not published:
                    continue
                details = []
                for sibling in heading.parent.next_siblings:
                    if getattr(sibling, "name", None) in {"h2", "h3", "h4"} or (getattr(sibling, "name", None) == "div" and sibling.find(["h2", "h3", "h4"])):
                        break
                    if hasattr(sibling, "get_text"):
                        details.append(sibling.get_text(" ", strip=True))
                    if len(" ".join(details)) > 1600:
                        break
                body = " ".join(details)[:1800] or heading.parent.get_text(" ", strip=True)[:1800]
                if len(body) < 40:
                    continue
                title = f"{product} · {heading_text}"
                items.append({"vendor": vendor, "product": product, "title": title, "published": published,
                              "url": f"{feed_url}#update-{published}-{len(items)}", "kind": "update", "source_text": body, "feed_verified": True})
                if len(items) >= 8:
                    break
            if not items:
                for heading in soup.select("h2, h3"):
                    heading_text = heading.get_text(" ", strip=True)
                    match = re.search(r"(20\d{2})\s*年\s*(\d{1,2})\s*月", heading_text)
                    if match:
                        published = f"{match.group(1)}-{int(match.group(2)):02d}"
                    else:
                        match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})", heading_text, re.I)
                        published = datetime.strptime(match.group(), "%B %Y").strftime("%Y-%m") if match else ""
                    if not published or published > datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m"):
                        continue
                    details = []
                    for sibling in heading.next_siblings:
                        if getattr(sibling, "name", None) == heading.name or (heading.name == "h3" and getattr(sibling, "name", None) == "h2"):
                            break
                        if hasattr(sibling, "get_text"):
                            details.append(sibling.get_text(" ", strip=True))
                    body = " ".join(details)[:1800]
                    if len(body) >= 12:
                        items.append({"vendor": vendor, "product": product, "title": f"{product} · {heading_text}", "published": published,
                                      "url": f"{feed_url}#update-{published}-{len(items)}", "kind": "update", "source_text": body, "feed_verified": True})
                    if len(items) >= 6:
                        break
            return items
        found = []
        for link in soup.select("a[href]"):
            title = link.get_text(" ", strip=True)
            url = urljoin(feed_url, link.get("href", "")).split("?", 1)[0].split("#", 1)[0]
            if not VENDOR_WORDS[vendor].search(title) or len(title) < 16 or url == feed_url or len(title) > 180:
                continue
            if VENDOR_HOSTS.get(urlparse(url).hostname) != vendor:
                continue
            path = urlparse(url).path
            if not (re.search(r"/20\d{2}/|/news/[^/]+|/blog/[^/]+|/changelog/20\d{2}-\d{2}-\d{2}-", path)
                    or (vendor == "Google" and "/products/" in path and path.count("/") >= 5)
                    or (vendor == "Alibaba Cloud" and re.search(r"/document-\d+", path))):
                continue
            if url in {item[2] for item in PRODUCTS}:
                continue
            found.append({"vendor": vendor, "product": product, "title": title, "published": "", "url": url, "kind": "launch"})
            if len(found) >= 8:
                break
        return found
    except (requests.RequestException, ElementTree.ParseError) as exc:
        FEED_HEALTH[feed_url] = "error"
        logger.warning("AI app feed unavailable %s: %s", feed_url, exc)
        return []


def _github_repository_items() -> list[dict]:
    items = []
    for vendor, product, repository in GITHUB_REPOSITORIES:
        url = f"https://github.com/{repository}"
        FEED_HEALTH[url] = "pending"
        try:
            response = requests.get(f"https://api.github.com/repos/{repository}", headers=HEADERS, timeout=12)
            response.raise_for_status()
            repo = response.json()
            if repo.get("full_name", "").casefold() != repository.casefold() or repo.get("html_url", "").rstrip("/").casefold() != url.casefold():
                FEED_HEALTH[url] = "error"
                continue
            description = str(repo.get("description") or "").strip()
            source_text = description
            try:
                readme = requests.get(f"https://raw.githubusercontent.com/{repository}/{repo.get('default_branch') or 'main'}/README.md", headers=HEADERS, timeout=12)
                readme.raise_for_status()
                source_text = f"{source_text}\n{readme.text[:5000]}".strip()
            except requests.RequestException:
                pass
            source_text = f"{source_text}\nGitHub stars: {repo.get('stargazers_count', 0)}; forks: {repo.get('forks_count', 0)}; language: {repo.get('language') or 'unknown'}".strip()
            published = _date(str(repo.get("pushed_at") or repo.get("created_at") or ""))
            if not published or not source_text:
                FEED_HEALTH[url] = "empty"
                continue
            items.append({"vendor": vendor, "product": product, "title": f"{product} 推理框架动态", "published": published,
                          "url": url, "kind": "update", "source_text": source_text, "feed_verified": True})
            FEED_HEALTH[url] = "matched"
        except (requests.RequestException, ValueError) as exc:
            FEED_HEALTH[url] = "error"
            logger.warning("Official GitHub repository unavailable %s: %s", repository, exc)
    return items


def discover() -> list[dict]:
    found = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for feed, feed_items in zip(FEEDS, pool.map(_feed_items, FEEDS)):
            if FEED_HEALTH.get(feed[2]) != "error":
                FEED_HEALTH[feed[2]] = "matched" if feed_items else "empty"
            for item in feed_items:
                found.setdefault(item["url"], item)
    for item in _github_repository_items():
        found.setdefault(item["url"], item)
    for vendor, title, published, url in SEEDS:
        found.setdefault(url, {"vendor": vendor, "title": title, "published": published, "url": url, "kind": "launch", "discovery_seed": True})
    for vendor, title, url in PRODUCT_SEEDS:
        found.setdefault(url, {"vendor": vendor, "title": title, "published": "", "url": url, "kind": "product"})
    for query in ("agent", "Meta AI", "Vibes", "glasses"):
        try:
            response = requests.get("https://about.fb.com/wp-json/wp/v2/search", params={"search": query, "per_page": 20}, headers=HEADERS, timeout=10)
            response.raise_for_status()
            for item in response.json():
                url = item.get("url", "").split("?", 1)[0]
                if urlparse(url).hostname == "about.fb.com" and "/news/" in url:
                    title = BeautifulSoup(item.get("title", ""), "html.parser").get_text(" ", strip=True)
                    if VENDOR_WORDS["Meta"].search(title):
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
            cursor.execute("""SELECT vendor, title, link AS url, published_date::text AS published
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
        if item not in selected and counts.get(item["vendor"], 0) < 16:
            selected.append(item)
            counts[item["vendor"]] = counts.get(item["vendor"], 0) + 1
    return selected[:180]


def _source(item: dict) -> dict | None:
    url = item["url"]
    official_github_repo = any(item.get("vendor") == vendor and url.rstrip("/").casefold() == f"https://github.com/{repo}".casefold()
                               for vendor, _, repo in GITHUB_REPOSITORIES)
    if url in EXCLUDED_APPLICATION_URLS or urlparse(url).scheme != "https" or (VENDOR_HOSTS.get(urlparse(url).hostname) != item.get("vendor") and not official_github_repo):
        return None
    if item.get("source_text") and item.get("feed_verified"):
        return {**item, "source_verified": True}
    try:
        response = requests.get(url, headers=HEADERS, timeout=12)
        response.raise_for_status()
        if VENDOR_HOSTS.get(urlparse(response.url).hostname) != item["vendor"]:
            return None
        soup = BeautifulSoup(response.content, "html.parser")
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
        if not body or (not PRODUCT_WORDS.search(title) and not APP_WORDS.search(title) and item.get("kind") != "product" and url not in {seed[3] for seed in SEEDS}) or (MODEL_ONLY.search(title) and not re.search(r"agent|智能体|assistant|助手|copilot|应用|app|kiro|codex|codebuddy|qoder", title, re.I)) or (not item.get("kind") and not LAUNCH_WORDS.search(title)):
            return None
        meta_date = soup.find("meta", attrs={"property": "article:published_time"}) or soup.find("meta", attrs={"name": "date"})
        time_node = soup.find("time")
        published = ("" if item.get("discovery_seed") else item.get("published")) or _date((meta_date or {}).get("content", "")) or _date((time_node or {}).get("datetime", "")) or _date((time_node.get_text(" ", strip=True) if time_node else "")) or ("" if item.get("discovery_seed") else _date(item.get("title", "")))
        return {**item, "title": title, "published": published, "source_text": body, "image_url": first_source_image(response.content.decode("utf-8", errors="ignore"), response.url), "source_verified": True}
    except requests.RequestException as exc:
        logger.warning("Agent source unavailable %s: %s", url, exc)
        if url in SEED_EXCERPTS:
            return {**item, "source_text": SEED_EXCERPTS[url], "source_verified": False}
        return None


def analyze(item: dict) -> dict:
    from services.prompt_service import published_prompt
    active_prompt = published_prompt("ai_application_analysis")
    expected_version = active_prompt["version"] if active_prompt else None
    result = {key: item[key] for key in ("vendor", "title", "published", "url")}
    result["kind"] = item.get("kind", "launch")
    result["source_text"] = item.get("source_text", "")[:300]
    result["analysis"] = None
    source_fingerprint = _source_fingerprint(item)
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("ai_application:" + item["url"],))
            cursor.execute("""SELECT source_fingerprint, analyzed_source_fingerprint, analysis_status,
                                     source_updated_at, analyzed_at
                              FROM vendor_ai_applications WHERE vendor=%s AND url=%s""",
                           (item["vendor"], item["url"]))
            application = cursor.fetchone()
            stale = _analysis_is_stale(application)
            cursor.execute("SELECT id, analysis, prompt_name, prompt_version FROM intelligence_analysis WHERE kind='ai_application' AND source_key=%s", (item["url"],))
            existing = cursor.fetchone()
            if (not stale and existing and existing.get("prompt_version") == expected_version
                    and _parse_structured(existing["analysis"])):
                result.update(analysis=existing["analysis"], analysis_id=existing["id"],
                              prompt_name=existing.get("prompt_name"), prompt_version=existing.get("prompt_version"))
                _upsert_application(cursor, item, {"summary": existing["analysis"], "capability": "", "opportunity": "", "limitation": ""}, "done", update_analysis_time=False)
            elif settings.CHAT_API_KEY:
                analysis, prompt_name, prompt_version = _analyze_with_retry(item, return_metadata=True)
                if analysis:
                    cursor.execute("""SELECT source_fingerprint, vendor, name AS title, kind,
                                             published_at AS published, source_text
                                      FROM vendor_ai_applications WHERE vendor=%s AND url=%s FOR UPDATE""",
                                   (item["vendor"], item["url"]))
                    current = cursor.fetchone()
                    current_snapshot_fingerprint = _source_fingerprint(dict(current)) if current else None
                    if current_snapshot_fingerprint != source_fingerprint:
                        result.update(analysis=None, analysis_stale=True)
                        return result
                    fields = _parse_structured(analysis)
                    composed = _compose_analysis(fields)
                    cursor.execute("""INSERT INTO intelligence_analysis (kind, source_key, analysis,prompt_name,prompt_version)
                        VALUES ('ai_application',%s,%s,%s,%s)
                        ON CONFLICT (kind, source_key) DO UPDATE SET analysis=EXCLUDED.analysis,
                            prompt_name=EXCLUDED.prompt_name,prompt_version=EXCLUDED.prompt_version,created_at=NOW()
                        RETURNING id""", (item["url"], composed, prompt_name, prompt_version))
                    result.update(analysis=composed, analysis_id=cursor.fetchone()["id"],
                                  prompt_name=prompt_name, prompt_version=prompt_version)
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


def _analyze_with_retry(item: dict, return_metadata: bool = False) -> str | tuple[str | None, str | None, int | None] | None:
    """Call the AI provider for a structured analysis, retrying with backoff."""
    from services.prompt_service import published_prompt
    active = published_prompt("ai_application_analysis")
    prompt_name = active["prompt_name"] if active else None
    prompt_version = active["version"] if active else None
    system_prompt = active["system_prompt"] if active else "你是技术情报分析师。只依据给定官方原文，输出完整 JSON（不要 markdown 代码块），字段：summary（一句话概括产品/发布）、capability（能做什么）、opportunity（与云和智能体生态相关的机会）、limitation（一项尚需验证的限制）。用中文叙述，保留品牌、产品和模型的正式名称；普通英文术语译为中文。区分产品页、发布公告和未来计划；使用具体日期，避免今日、昨天、近日等相对时间；不要推测采用率，不要使用来源外事实。每个字段不超过100字。"
    user_prompt = f"厂商：{item['vendor']}\n标题：{item['title']}\n官方链接：{item['url']}\n原文：{item['source_text'][:600]}"
    if active and active.get("user_prompt_template"):
        user_prompt = active["user_prompt_template"].replace("{{vendor}}", item["vendor"]).replace("{{title}}", item["title"]).replace("{{url}}", item["url"]).replace("{{evidence}}", item["source_text"][:600])
    delays = (2, 5, 10)
    for attempt, delay in enumerate(delays, start=1):
        try:
            analysis = ai_service.chat_complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=1200, timeout=120, temperature=0.2,
            ).strip()
            if _parse_structured(analysis):
                return (analysis, prompt_name, prompt_version) if return_metadata else analysis
        except Exception as exc:
            logger.warning("Agent analysis attempt %d failed %s: %s", attempt, item["url"], exc)
        if attempt < len(delays):
            time.sleep(delay)
    return (None, prompt_name, prompt_version) if return_metadata else None


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


def _source_fingerprint(item: dict) -> str:
    payload = {key: item.get(key) or "" for key in ("vendor", "title", "kind", "published")}
    payload["source_text"] = (item.get("source_text") or "")[:2000]
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _analysis_is_stale(row: dict | None) -> bool:
    if not row or row.get("analysis_status") != "done" or not row.get("analyzed_at"):
        return True
    source_fingerprint = row.get("source_fingerprint")
    analyzed_fingerprint = row.get("analyzed_source_fingerprint")
    if not source_fingerprint or not analyzed_fingerprint or source_fingerprint != analyzed_fingerprint:
        return True
    source_updated_at = row.get("source_updated_at")
    analyzed_at = row.get("analyzed_at")
    return bool(source_updated_at and analyzed_at and source_updated_at > analyzed_at)


def _upsert_application(cursor, item: dict, fields: dict, status: str = "done", update_analysis_time: bool = True) -> None:
    """Persist a discovered application with its structured analysis, upserting by (vendor, url)."""
    cursor.execute("""
        INSERT INTO vendor_ai_applications
            (vendor, name, url, kind, published_at, category, summary, capability, opportunity, limitation, source_text,
             analysis_status, analyzed_at, analysis_model, source_fingerprint, analyzed_source_fingerprint)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CASE WHEN %s='done' AND %s THEN NOW() END,%s,%s,CASE WHEN %s='done' THEN %s END)
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
            analyzed_at = COALESCE(EXCLUDED.analyzed_at, vendor_ai_applications.analyzed_at),
            analysis_model = EXCLUDED.analysis_model,
            source_fingerprint = EXCLUDED.source_fingerprint,
            analyzed_source_fingerprint = COALESCE(EXCLUDED.analyzed_source_fingerprint, vendor_ai_applications.analyzed_source_fingerprint),
            updated_at = NOW()
        WHERE vendor_ai_applications.source_fingerprint IS NULL
           OR vendor_ai_applications.source_fingerprint = EXCLUDED.source_fingerprint
           OR (vendor_ai_applications.name IS NOT DISTINCT FROM EXCLUDED.name
               AND vendor_ai_applications.kind IS NOT DISTINCT FROM EXCLUDED.kind
               AND vendor_ai_applications.published_at IS NOT DISTINCT FROM EXCLUDED.published_at
               AND vendor_ai_applications.source_text IS NOT DISTINCT FROM EXCLUDED.source_text)
    """, (item["vendor"], item.get("title"), item["url"], item.get("kind", "launch"),
          item.get("published") or None, None, fields.get("summary"), fields.get("capability"),
          fields.get("opportunity"), fields.get("limitation"), (item.get("source_text") or "")[:2000],
          status, status, update_analysis_time, settings.CHAT_MODEL, _source_fingerprint(item), status, _source_fingerprint(item)))


def _read_structured(limit: int | None = 180) -> list[dict]:
    """Read persisted applications from the database, newest announcements first."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, vendor, name, url, kind, published_at, summary, capability, opportunity, limitation, source_text,
                       (SELECT raw.content->>'image_url' FROM intelligence_raw_items raw
                        WHERE raw.canonical_url=vendor_ai_applications.url AND raw.source_key='ai_app_official'
                        ORDER BY raw.observed_at DESC, raw.id DESC LIMIT 1) AS image_url,
                       analysis_status, analyzed_at, source_updated_at, source_fingerprint, analyzed_source_fingerprint
                FROM vendor_ai_applications
                ORDER BY (published_at IS NULL OR published_at = '') ASC, published_at DESC, id DESC
                LIMIT %s
            """, (limit,))
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
        analysis_stale = _analysis_is_stale(row)
        fields = {"summary": "" if analysis_stale else row.get("summary") or "",
                  "capability": "" if analysis_stale else row.get("capability") or "",
                  "opportunity": row.get("opportunity") or "", "limitation": row.get("limitation") or ""}
        if analysis_stale:
            fields.update(opportunity="", limitation="")
        if not _parse_structured(fields["summary"]):
            fields = {key: "" for key in fields}
        title = row.get("name") or ""
        if not re.search(r"[\u4e00-\u9fff]", title) and len(title.split()) > 2 and fields["summary"]:
            title = fields["summary"].split("。", 1)[0][:64]
        items.append({"vendor": row["vendor"], "title": title,
                      "published": row.get("published_at") or "", "url": row["url"],
                      "kind": row.get("kind") or "launch", "source_text": (row.get("source_text") or "")[:300],
                      "image_url": row.get("image_url") or "",
                      "analysis": _compose_analysis(fields), "analysis_id": row["id"],
                      "analysis_status": "stale" if analysis_stale else row.get("analysis_status"),
                      "analysis_stale": analysis_stale, "analyzed_at": row.get("analyzed_at"),
                      "source_updated_at": row.get("source_updated_at"),
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
    from services.source_registry_service import record_source_health, source_enabled
    from services.intelligence_data_service import store_ai_application
    source_key = "ai_app_official"
    if not source_enabled(source_key):
        return 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        sources = [item for item in pool.map(_source, discover()) if item]
    ingested = 0
    with get_db() as conn:
        cursor = conn.cursor()
        for item in sources:
            cursor.execute("""
                INSERT INTO vendor_ai_applications
                    (vendor, name, url, kind, published_at, source_text, analysis_status, source_fetched_at,
                     source_fingerprint, source_updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,'pending',NOW(),%s,NOW())
                ON CONFLICT (vendor, url) DO UPDATE SET
                    name = EXCLUDED.name,
                    kind = EXCLUDED.kind,
                    published_at = EXCLUDED.published_at,
                    source_text = EXCLUDED.source_text,
                    source_fetched_at = NOW(),
                    analysis_status = CASE WHEN vendor_ai_applications.source_fingerprint IS DISTINCT FROM EXCLUDED.source_fingerprint THEN 'pending' ELSE vendor_ai_applications.analysis_status END,
                    analyzed_at = CASE WHEN vendor_ai_applications.source_fingerprint IS DISTINCT FROM EXCLUDED.source_fingerprint THEN NULL ELSE vendor_ai_applications.analyzed_at END,
                    source_updated_at = CASE WHEN vendor_ai_applications.source_fingerprint IS DISTINCT FROM EXCLUDED.source_fingerprint THEN NOW() ELSE vendor_ai_applications.source_updated_at END,
                    source_fingerprint = EXCLUDED.source_fingerprint,
                    updated_at = NOW()
            """, (item["vendor"], item.get("title"), item["url"], item.get("kind", "launch"),
                  item.get("published"), (item.get("source_text") or "")[:2000], _source_fingerprint(item)))
            ingested += 1
            if item.get("source_verified") and item.get("kind") != "product":
                store_ai_application(cursor, item)
    record_source_health(source_key, "healthy")
    return ingested


def refresh_official_sources() -> dict:
    """Refresh dated official application evidence for the daily scheduler."""
    try:
        total = _ingest()
        return {"status": "success", "total": total}
    except Exception as exc:
        from services.source_registry_service import record_source_health
        record_source_health("ai_app_official", "failed", str(exc))
        raise


def _pending_rows(batch: int) -> list[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, vendor, name AS title, url, kind, published_at AS published, source_text
            FROM vendor_ai_applications
            WHERE (analysis_status = 'pending' OR analyzed_at IS NULL
               OR source_fingerprint IS NULL OR analyzed_source_fingerprint IS NULL
               OR source_fingerprint IS DISTINCT FROM analyzed_source_fingerprint
               OR source_updated_at > analyzed_at)
              AND source_text IS NOT NULL AND btrim(source_text) <> ''
            ORDER BY id LIMIT %s
        """, (batch,))
        return [dict(row) for row in cursor.fetchall()]


def _analyze_pending_snapshot() -> list[dict]:
    rows = _pending_rows(180)
    for index, row in enumerate(rows):
        analyze({"vendor": row["vendor"], "title": row["title"], "url": row["url"],
                 "kind": row["kind"], "published": row["published"], "source_text": row["source_text"]})
        if index + 1 < len(rows):
            time.sleep(3)
    return _read_structured()


def latest() -> list[dict]:
    """Refresh official sources, analyze pending rows, then return persisted results."""
    try:
        _ingest()
        return _analyze_pending_snapshot()
    except Exception as exc:
        logger.warning("Agent refresh failed: %s", exc)
        return _read_structured()


def analyze_stored_pending() -> list[dict]:
    """Analyze only persisted source snapshots; does not fetch external sources."""
    try:
        return _analyze_pending_snapshot()
    except Exception as exc:
        logger.warning("Stored agent analysis failed: %s", exc)
        return _read_structured()


def snapshot(limit: int | None = 180, refresh: bool = True) -> tuple[list[dict], bool]:
    global _refresh_future, _refresh_hour
    future = None
    if refresh:
        hour = int(datetime.now(timezone.utc).timestamp() // 3600)
        with _refresh_lock:
            if _refresh_hour != hour or _refresh_future is None:
                _refresh_future = _refresh_pool.submit(latest)
                _refresh_hour = hour
            future = _refresh_future
    rows = _read_structured(limit)
    if rows:
        return rows, bool(future and not future.done())
    if future and future.done():
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
    return fallback, bool(future and not future.done())
