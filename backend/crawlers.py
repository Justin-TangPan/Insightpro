"""
Crawlers Module for InsightPro
==============================
Real web crawlers for industry news, policy updates, and commercial intelligence.
All crawlers follow: try live crawl → fallback to DB cache → fallback to empty.

Data sources:
- 36氪 (36kr.com) — 科技/商业新闻
- 财联社 (cls.cn) — 财经快讯
- 澎湃新闻 (thepaper.cn) — 时政/政策
- 第一财经 (yicai.com) — 产业/商业
- 雷锋网 (leiphone.com) — AI/科技产业
- 机器之心 (jiqizhixin.com) — AI 行业
- 中国政府网 (gov.cn) — 政策法规
- 工信部 (miit.gov.cn) — 产业政策
"""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup
import json
import re
import os
from urllib.parse import urljoin
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from db import get_db

import time
from functools import wraps
from datetime import datetime


def retry(max_retries=3, base_delay=1.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"[Crawler] {func.__name__} 重试 {attempt+1}/{max_retries}, 等待 {delay}s")
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


class CrawlerMonitor:
    def __init__(self):
        self.history: list[dict] = []

    def record(self, name: str, success: bool, items_count: int, duration_ms: int, error: str = ""):
        entry = {"name": name, "timestamp": datetime.now().isoformat(), "success": success, "items_count": items_count, "duration_ms": duration_ms, "error": error[:200] if error else ""}
        self.history.append(entry)
        if len(self.history) > 1000:
            self.history = self.history[-500:]

    def health_report(self) -> dict:
        if not self.history:
            return {"status": "no_data", "total_crawls": 0}
        recent = self.history[-100:]
        success_rate = sum(1 for h in recent if h["success"]) / len(recent) * 100
        consecutive_failures = 0
        for h in reversed(self.history):
            if not h["success"]:
                consecutive_failures += 1
            else:
                break
        return {
            "status": "healthy" if success_rate >= 80 else "degraded" if success_rate >= 50 else "unhealthy",
            "total_crawls": len(self.history),
            "recent_success_rate": f"{success_rate:.0f}%",
            "consecutive_failures": consecutive_failures,
            "last_24h_count": sum(1 for h in self.history if h["timestamp"].startswith(datetime.now().strftime("%Y-%m-%d"))),
        }


crawler_monitor = CrawlerMonitor()


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}

TIMEOUT = 12


# ──────────────────────────────────────────────
# 通用工具
# ──────────────────────────────────────────────

def _clean(text: str) -> str:
    """清理文本：去除多余空白"""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()


def _is_quality_item(item: dict) -> bool:
    """Reject empty, mojibake and non-traceable records before persistence."""
    title = _clean(str(item.get("title") or ""))
    url = str(item.get("url") or item.get("link") or "")
    if len(title) < 6 or not url.startswith(("http://", "https://")):
        return False
    mojibake_markers = ("ä¸", "å®", "æ", "è", "é", "ï¿½", "�")
    return not any(marker in title for marker in mojibake_markers)


def _safe_get(url: str, **kwargs) -> requests.Response | None:
    start = time.time()
    try:
        timeout = kwargs.pop('timeout', TIMEOUT)
        resp = requests.get(url, headers=HEADERS, timeout=timeout, **kwargs)
        resp.raise_for_status()
        crawler_monitor.record(url.split('/')[2], True, 1, int((time.time() - start) * 1000))
        return resp
    except Exception as e:
        crawler_monitor.record(url.split('/')[2], False, 0, int((time.time() - start) * 1000), str(e))
        print(f"[Crawler] GET {url} failed: {e}")
        return None


def _init_table(table_name: str, schema: str, indexes: list[str] = None):
    """通用建表（schema 已由 reconcile_schema.py 管理，保留为 no-op 兼容）"""
    pass


def _store_items(table: str, columns: list[str], items: list[dict], date_col: str, dedup_cols: list[str] = None):
    """通用数据入库（去重，ON CONFLICT DO NOTHING）"""
    if not items:
        return 0
    placeholders = ", ".join(["%s"] * len(columns))
    col_str = ", ".join(columns)
    sql = f"INSERT INTO {table} ({col_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    count = 0
    with get_db() as conn:
        c = conn.cursor()
        for item in items:
            values = []
            for col in columns:
                val = item.get(col, "")
                if isinstance(val, (list, dict)):
                    val = json.dumps(val, ensure_ascii=False)
                values.append(val)
            try:
                c.execute(sql, values)
                if c.rowcount > 0:
                    count += 1
            except Exception:
                pass
    return count


# ──────────────────────────────────────────────
# 爬虫 1: 36氪 — 科技商业新闻
# ──────────────────────────────────────────────

def crawl_36kr() -> list[dict]:
    """抓取 36氪首页热门资讯"""
    items = []
    # 策略1: 36kr newsflash API
    try:
        resp = _safe_get("https://36kr.com/newsflashes", timeout=10)
        if resp:
            soup = BeautifulSoup(resp.text, "html.parser")
            # 尝试从 script 标签中提取 JSON 数据
            scripts = soup.find_all("script")
            for script in scripts:
                text = script.string or ""
                if "newsflashListData" in text or "itemList" in text:
                    # 提取 JSON
                    match = re.search(r'itemList["\']?\s*:\s*(\[.*?\])', text, re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                            for item in data[:15]:
                                title = item.get("title", "") or item.get("entity", {}).get("title", "")
                                summary = item.get("description", "") or item.get("entity", {}).get("description", "")
                                url = item.get("newsUrl", "") or f"https://36kr.com/newsflashes"
                                if title:
                                    items.append({
                                        "source": "36氪",
                                        "title": _clean(title),
                                        "summary": _clean(summary)[:200],
                                        "url": url,
                                        "category": "科技商业",
                                    })
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        print(f"[Crawler] 36kr API failed: {e}")

    # 策略2: 解析页面 HTML
    if not items:
        try:
            resp = _safe_get("https://36kr.com/")
            if resp:
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.select("a.article-item-title, a[class*='title']")[:15]:
                    title = _clean(a.get_text())
                    href = a.get("href", "")
                    if title and len(title) > 5:
                        if not href.startswith("http"):
                            href = f"https://36kr.com{href}"
                        items.append({
                            "source": "36氪",
                            "title": title,
                            "summary": "",
                            "url": href,
                            "category": "科技商业",
                        })
        except Exception:
            pass

    return items[:15]


# ──────────────────────────────────────────────
# 爬虫 2: 财联社 — 财经快讯
# ──────────────────────────────────────────────

def crawl_cls() -> list[dict]:
    """抓取财联社电报快讯"""
    items = []
    try:
        # 财联社有公开 API
        resp = _safe_get(
            "https://www.cls.cn/nodeapi/updateTelegraphList",
            params={"app": "CailianpressWeb", "os": "web", "sv": "7.7.5", "rn": "20"}
        )
        if resp:
            data = resp.json()
            roll_data = data.get("data", {}).get("roll_data", [])
            for item in roll_data[:20]:
                title = _clean(item.get("title", "") or item.get("brief", ""))
                content = _clean(item.get("content", "") or item.get("brief", ""))
                if not title and content:
                    title = content[:60]
                if title:
                    items.append({
                        "source": "财联社",
                        "title": title,
                        "summary": content[:200],
                        "url": f"https://www.cls.cn/detail/{item.get('id', '')}",
                        "category": "财经快讯",
                    })
    except Exception as e:
        print(f"[Crawler] CLS API failed: {e}")

    # 降级: 解析页面
    if not items:
        try:
            resp = _safe_get("https://www.cls.cn/telegraph")
            if resp:
                soup = BeautifulSoup(resp.text, "html.parser")
                for el in soup.select("[class*='telegraph-content'], [class*='item']")[:15]:
                    title_el = el.select_one("span, p, a")
                    if title_el:
                        title = _clean(title_el.get_text())
                        if title and len(title) > 5:
                            items.append({
                                "source": "财联社",
                                "title": title,
                                "summary": "",
                                "url": "https://www.cls.cn/telegraph",
                                "category": "财经快讯",
                            })
        except Exception:
            pass

    return items[:20]


# ──────────────────────────────────────────────
# 爬虫 3: 第一财经 — 产业商业
# ──────────────────────────────────────────────

def crawl_yicai() -> list[dict]:
    """抓取第一财经最新报道"""
    items = []
    try:
        resp = _safe_get("https://www.yicai.com/news/")
        if resp:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("a.f-ff0, a[class*='title'], h2 a, h3 a")[:15]:
                title = _clean(a.get_text())
                href = a.get("href", "")
                if title and len(title) > 5:
                    if not href.startswith("http"):
                        href = f"https://www.yicai.com{href}"
                    items.append({
                        "source": "第一财经",
                        "title": title,
                        "summary": "",
                        "url": href,
                        "category": "产业商业",
                    })
    except Exception as e:
        print(f"[Crawler] Yicai failed: {e}")
    return items[:15]


# ──────────────────────────────────────────────
# 爬虫 4: 雷锋网 / 机器之心 — AI 产业
# ──────────────────────────────────────────────

def crawl_ai_news() -> list[dict]:
    """抓取 AI 产业新闻（雷锋网 + 机器之心）"""
    items = []

    # 雷锋网
    try:
        resp = _safe_get("https://www.leiphone.com/")
        if resp:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("a[class*='title'], h3 a, .lph-article-compo-title a")[:10]:
                title = _clean(a.get_text())
                href = a.get("href", "")
                if title and len(title) > 5:
                    if not href.startswith("http"):
                        href = f"https://www.leiphone.com{href}"
                    items.append({
                        "source": "雷锋网",
                        "title": title,
                        "summary": "",
                        "url": href,
                        "category": "AI产业",
                    })
    except Exception:
        pass

    # 机器之心
    try:
        resp = _safe_get("https://www.jiqizhixin.com/")
        if resp:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("a[class*='title'], h4 a, .article-title a")[:10]:
                title = _clean(a.get_text())
                href = a.get("href", "")
                if title and len(title) > 5:
                    if not href.startswith("http"):
                        href = f"https://www.jiqizhixin.com{href}"
                    items.append({
                        "source": "机器之心",
                        "title": title,
                        "summary": "",
                        "url": href,
                        "category": "AI产业",
                    })
    except Exception:
        pass

    return items[:15]


# ──────────────────────────────────────────────
# 爬虫 5: 政策法规（中国政府网 + 工信部）
# ──────────────────────────────────────────────

def crawl_policy() -> list[dict]:
    """抓取最新政策法规（多源）"""
    items = []

    # 策略1: 国务院政策 API（搜索接口，返回 JSON）
    try:
        resp = _safe_get(
            "https://sousuo.www.gov.cn/search-gov/data",
            params={
                "t": "zhengcelibrary_gw",
                "q": "",
                "timetype": "timeqb",
                "mintime": "",
                "maxtime": "",
                "sort": "time",
                "sortType": "1",
                "searchfield": "title",
                "pcodeJig498": "",
                "childtype": "",
                "subchildtype": "",
                "tsbq": "",
                "pubtimeyear": "",
                "puborg": "",
                "searchfield": "title",
                "p": "0",
                "n": "15",
                "inpro": "",
            }
        )
        if resp:
            data = resp.json()
            results = data.get("searchVO", {}).get("listVO", [])
            for item in results[:15]:
                title = _clean(item.get("title", ""))
                url = item.get("url", "") or item.get("purl", "")
                pubtime = item.get("pubtime", "")
                if title:
                    items.append({
                        "source": "国务院",
                        "title": title,
                        "summary": f"发布时间: {pubtime}" if pubtime else "",
                        "url": url or "https://www.gov.cn/zhengce/",
                        "category": "国家政策",
                        "severity": "high",
                    })
    except Exception as e:
        print(f"[Crawler] Gov API failed: {e}")

    # 策略2: 解析国务院政策页面
    if not items:
        try:
            resp = _safe_get("https://www.gov.cn/zhengce/zuixin/")
            if resp:
                resp.encoding = 'utf-8'
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.select("a")[:50]:
                    title = _clean(a.get_text())
                    href = a.get("href", "")
                    if title and len(title) > 8:
                        if not href.startswith("http"):
                            href = f"https://www.gov.cn{href}"
                        items.append({
                            "source": "国务院",
                            "title": title,
                            "summary": "",
                            "url": href,
                            "category": "国家政策",
                            "severity": "high",
                        })
        except Exception:
            pass

    # 策略3: 新华网政策频道
    try:
        resp = _safe_get("http://www.news.cn/politics/")
        if resp:
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("a")[:30]:
                title = _clean(a.get_text())
                href = a.get("href", "")
                if title and len(title) > 10 and any(kw in title for kw in ["政策", "方案", "意见", "通知", "办法", "规划", "行动", "指导", "条例", "规定", "发布", "实施"]):
                    if not href.startswith("http"):
                        href = f"http://www.news.cn{href}"
                    items.append({
                        "source": "新华网",
                        "title": title,
                        "summary": "",
                        "url": href,
                        "category": "国家政策",
                        "severity": "high",
                    })
    except Exception:
        pass

    return items[:20]


# ──────────────────────────────────────────────
# 爬虫 6: 云厂商动态（官方博客/公告）
# ──────────────────────────────────────────────

def _is_news_like(title: str, href: str) -> bool:
    """判断链接是否像新闻文章（而非导航/产品/登录页）"""
    if not title or len(title) < 10:
        return False
    # 排除导航/工具类标题
    nav_words = ["登录", "注册", "Contact", "Products", "产品", "解决方案", "定价", "价格",
                 "文档", "控制台", "首页", "关于", "关于我们", "加入", "招聘", "联系",
                 "AI Assistant", "Marketplace", "Sign in", "Sign up", "搜索", "菜单", "更多",
                 "Privacy", "隐私", "条款", "协议", "Cookie", "RSS", "订阅", "FAQ", "帮助",
                 "反馈", "投诉", "版权", "声明", "网站地图", "跳转", "Contact Us", "Services",
                 "Resources", "Get Started", "Try Free", "Create Account", "Subscribe"]
    for w in nav_words:
        if w in title:
            return False
    # 排除工具类 href
    href_lower = href.lower()
    bad_href = ["/help/", "/faq", "/feed", "/privacy", "/policy", "/agreement",
                "/login", "/signup", "/register", "/console", "/dashboard"]
    for b in bad_href:
        if b in href_lower:
            return False
    # href 含新闻特征
    news_patterns = ["news", "whats-new", "announcement", "article", "blog",
                     "/post/", "dynamic", "zixun", "dongtai", "/info/news",
                     "campaign", "event", "launch", "release", "update",
                     "insight", "story", "case", "customer", "success"]
    href_match = any(p in href_lower for p in news_patterns)
    # 标题含新闻关键词
    news_kw = ["发布", "上线", "推出", "更新", "升级", "合作", "签约", "落地", "入选",
               "大会", "峰会", "论坛", "报告", "白皮书", "案例", "客户", "开源",
               "支持", "增强", "新增", "集成", "联合", "战略", "开服", "降价",
               "免费", "试用", "正式", "全面", "赋能", "实战", "解读", "盘点", "揭晓",
               "Launch", "Release", "Update", "Announce", "Introducing", "New",
               "Partnership", "Case Study", "Customer Story", "Success"]
    title_match = any(k in title for k in news_kw)
    return href_match or title_match


def _crawl_vendor_news(vendor: str, source: str, news_urls: list[str], base: str, limit: int = 4) -> list[dict]:
    """通用厂商新闻抓取：尝试多个 news_urls，过滤新闻链接"""
    out = []
    for url in news_urls:
        resp = _safe_get(url)
        if not resp:
            continue
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, "html.parser")
        seen = set()
        for a in soup.select("a[href]")[:120]:
            title = _clean(a.get_text())
            href = a.get("href", "")
            if not title or title in seen:
                continue
            if not _is_news_like(title, href):
                continue
            if not href.startswith("http"):
                href = f"{base}{href}"
            seen.add(title)
            cooperation = any(word in title.lower() for word in [
                "合作", "携手", "联合", "签约", "客户", "案例", "伙伴",
                "customer", "case study", "partner", "partnership",
            ])
            out.append({
                "vendor": vendor, "source": source,
                "title": title, "summary": "", "url": href,
                "category": "合作案例" if cooperation else "产品动态",
            })
            if len(out) >= limit:
                return out
        if out:
            break
    return out


def crawl_cloud_vendors() -> list[dict]:
    """抓取各云厂商最新动态（针对真实新闻页 + 新闻链接过滤）"""
    items = []

    # 策略1: 阿里云 — 官方博客 + 新闻页
    items += _crawl_vendor_news(
        "阿里云", "阿里云",
        [
            "https://www.alibabacloud.com/blog",          # 官方博客
            "https://www.alibabacloud.com/zh/news",       # 新闻中心
            "https://www.alibabacloud.com/campaign",      # 活动/发布
        ],
        "https://www.alibabacloud.com", limit=6,
    )

    # 策略2: 腾讯云 — 开发者社区 + 新闻
    items += _crawl_vendor_news(
        "腾讯云", "腾讯云",
        [
            "https://cloud.tencent.com/developer/column",  # 技术专栏
            "https://cloud.tencent.com/developer/news",    # 新闻
            "https://cloud.tencent.com/product/news",      # 产品新闻
        ],
        "https://cloud.tencent.com", limit=6,
    )

    # 策略3: 火山引擎 — 首页 + 新闻过滤（docs 页有反爬）
    items += _crawl_vendor_news(
        "火山云", "火山云",
        ["https://www.volcengine.com/"],
        "https://www.volcengine.com", limit=4,
    )

    # 策略4: AWS 中国 — 新闻页 + 博客
    items += _crawl_vendor_news(
        "AWS", "AWS",
        [
            "https://aws.amazon.com/cn/about-aws/whats-new/",
            "https://aws.amazon.com/cn/blogs/china/",      # 中国区博客
            "https://aws.amazon.com/cn/new/",
        ],
        "https://aws.amazon.com", limit=6,
    )

    # 策略5: Microsoft Azure — 官方客户案例 + 博客
    items += _crawl_vendor_news(
        "Azure", "Microsoft Azure",
        [
            "https://www.microsoft.com/en-us/customers",
            "https://azure.microsoft.com/en-us/blog/",
        ],
        "https://www.microsoft.com", limit=6,
    )

    return items


# ──────────────────────────────────────────────
# 聚合采集器：并行爬取所有源
# ──────────────────────────────────────────────

def crawl_all_news() -> dict:
    """
    并行爬取所有新闻源，返回分类结果。
    {source_name: [items], ...}
    """
    results = {}
    crawlers = {
        "36kr": crawl_36kr,
        "cls": crawl_cls,
        "yicai": crawl_yicai,
        "ai_news": crawl_ai_news,
        "policy": crawl_policy,
        "cloud_vendors": crawl_cloud_vendors,
    }

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fn): name for name, fn in crawlers.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                items = future.result()
                results[name] = items
                print(f"[Crawler] {name}: {len(items)} items")
            except Exception as e:
                print(f"[Crawler] {name} failed: {e}")
                results[name] = []

    return results


# ──────────────────────────────────────────────
# 数据存储：爬取结果写入 SQLite
# ──────────────────────────────────────────────

def init_crawler_tables():
    """爬虫数据表（industry_news / policy_updates / cloud_vendor_news）由 reconcile_schema.py 统一创建。"""
    pass


def store_crawl_results(results: dict) -> dict:
    """将爬取结果存入数据库，返回统计"""
    today = datetime.now().strftime("%Y-%m-%d")
    stats = {}

    # 36氪 + 财联社 + 第一财经 + AI产业 → industry_news
    news_items = []
    for key in ["36kr", "cls", "yicai", "ai_news"]:
        for item in results.get(key, []):
            item["crawl_date"] = today
            if _is_quality_item(item):
                news_items.append(item)
    count = _store_items(
        "industry_news",
        ["crawl_date", "source", "title", "summary", "url", "category"],
        news_items,
        "crawl_date"
    )
    stats["industry_news"] = count

    # 政策 → policy_updates
    policy_items = results.get("policy", [])
    for item in policy_items:
        item["crawl_date"] = today
    policy_items = [item for item in policy_items if _is_quality_item(item)]
    count = _store_items(
        "policy_updates",
        ["crawl_date", "source", "title", "summary", "url", "category", "severity"],
        policy_items,
        "crawl_date"
    )
    stats["policy_updates"] = count

    # 云厂商 → cloud_vendor_news
    cloud_items = results.get("cloud_vendors", [])
    for item in cloud_items:
        item["crawl_date"] = today
    cloud_items = [item for item in cloud_items if _is_quality_item(item)]
    count = _store_items(
        "cloud_vendor_news",
        ["crawl_date", "vendor", "title", "summary", "url", "category"],
        cloud_items,
        "crawl_date"
    )
    stats["cloud_vendor_news"] = count

    return stats


def run_daily_crawl() -> dict:
    """
    每日全量爬取入口：爬取 → 存储 → 返回统计。
    由 scheduler 在每天早上 9 点调用。
    """
    now = datetime.now()
    print(f"[{now.strftime('%H:%M:%S')}] 开始每日全量爬取...")

    results = crawl_all_news()
    stats = store_crawl_results(results)

    total = sum(stats.values())
    elapsed = (datetime.now() - now).total_seconds()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 每日爬取完成: {total} 条新数据, 耗时 {elapsed:.1f}s")

    # 写入爬取日志
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO scrape_log (scrape_date, scrape_time, status, items_count)
            VALUES (%s, %s, %s, %s)
        """, (now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
              "success" if total > 0 else "empty", total))

    return stats


# ──────────────────────────────────────────────
# 查询接口（供 main.py API 调用）
# ──────────────────────────────────────────────

def get_industry_news(days: int = 7, source: str = None, limit: int = 50) -> list[dict]:
    """获取行业新闻"""
    with get_db() as conn:
        c = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        query = "SELECT * FROM industry_news WHERE crawl_date >= %s"
        params = [cutoff]
        if source:
            query += " AND source = %s"
            params.append(source)
        query += " ORDER BY crawl_date DESC, id DESC LIMIT %s"
        params.append(limit)
        c.execute(query, params)
        return [dict(r) for r in c.fetchall()]


def get_policy_updates(days: int = 30, limit: int = 50) -> list[dict]:
    """获取政策法规"""
    with get_db() as conn:
        c = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        c.execute("SELECT * FROM policy_updates WHERE crawl_date >= %s ORDER BY crawl_date DESC, id DESC LIMIT %s",
                  (cutoff, limit))
        return [dict(r) for r in c.fetchall()]


def get_cloud_vendor_news(days: int = 7, vendor: str = None, limit: int = 50) -> list[dict]:
    """获取云厂商动态"""
    with get_db() as conn:
        c = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        query = "SELECT * FROM cloud_vendor_news WHERE crawl_date >= %s"
        params = [cutoff]
        if vendor:
            query += " AND vendor = %s"
            params.append(vendor)
        query += " ORDER BY crawl_date DESC, id DESC LIMIT %s"
        params.append(limit)
        c.execute(query, params)
        return [dict(r) for r in c.fetchall()]


def get_homepage_stats() -> dict:
    """获取首页看板统计数据（从数据库实时聚合）"""
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    stats = {}
    with get_db() as conn:
        c = conn.cursor()

        # 行业新闻数（本周）
        try:
            c.execute("SELECT COUNT(*) AS cnt FROM industry_news WHERE crawl_date >= %s", (week_ago,))
            stats["news_count"] = c.fetchone()["cnt"]
        except Exception:
            stats["news_count"] = 0

        # GitHub Trending 项目数（今天）
        try:
            c.execute("SELECT COUNT(*) AS cnt FROM github_trending WHERE scrape_date = %s", (today,))
            stats["trending_today"] = c.fetchone()["cnt"]
        except Exception:
            stats["trending_today"] = 0

        # 百度热搜数（今天）
        try:
            c.execute("SELECT COUNT(*) AS cnt FROM baidu_hotsearch WHERE scrape_date = %s", (today,))
            stats["hotsearch_today"] = c.fetchone()["cnt"]
        except Exception:
            stats["hotsearch_today"] = 0

        # 友商动态数（本周）
        try:
            c.execute("SELECT COUNT(*) AS cnt FROM competitor_news WHERE scrape_date >= %s", (week_ago,))
            stats["competitor_count"] = c.fetchone()["cnt"]
        except Exception:
            stats["competitor_count"] = 0

        # 招标信息数
        try:
            c.execute("SELECT COUNT(*) AS cnt FROM bidding_opportunities WHERE bid_date >= %s", (week_ago,))
            bidding_count = c.fetchone()["cnt"]
            if not bidding_count:
                c.execute("SELECT COUNT(*) AS cnt FROM bidding_opportunities")
                bidding_count = c.fetchone()["cnt"]
            stats["bidding_count"] = bidding_count
        except Exception:
            stats["bidding_count"] = 0

        # 需求信号数
        try:
            c.execute("SELECT COUNT(*) AS cnt FROM demand_signals WHERE signal_date >= %s", (week_ago,))
            stats["demand_count"] = c.fetchone()["cnt"]
        except Exception:
            stats["demand_count"] = 0

        # 政策法规数
        try:
            c.execute("SELECT COUNT(*) AS cnt FROM policy_updates WHERE crawl_date >= %s", (week_ago,))
            stats["policy_count"] = c.fetchone()["cnt"]
        except Exception:
            stats["policy_count"] = 0

        # 云厂商动态数
        try:
            c.execute("SELECT COUNT(*) AS cnt FROM cloud_vendor_news WHERE crawl_date >= %s", (week_ago,))
            stats["cloud_news_count"] = c.fetchone()["cnt"]
        except Exception:
            stats["cloud_news_count"] = 0

        # GitHub trending 总历史记录数
        try:
            c.execute("SELECT COUNT(*) AS cnt FROM github_trending")
            stats["trending_total"] = c.fetchone()["cnt"]
        except Exception:
            stats["trending_total"] = 0

        # 爬取日志 - 最近一次状态
        try:
            c.execute("SELECT status, items_count, scrape_time FROM scrape_log ORDER BY id DESC LIMIT 1")
            row = c.fetchone()
            if row:
                stats["last_crawl"] = {"status": row["status"], "count": row["items_count"], "time": row["scrape_time"]}
            else:
                stats["last_crawl"] = None
        except Exception:
            stats["last_crawl"] = None

    return stats


def get_homepage_modules() -> list[dict]:
    """
    获取首页各模块预览数据（每个模块最新 3 条）。
    从多个表聚合，返回结构化数据供前端渲染。
    """
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    modules = []
    with get_db() as conn:
        c = conn.cursor()

        # 1. 市场情报 - 从 demand_signals 取
        try:
            c.execute("SELECT title, summary FROM demand_signals WHERE signal_date >= %s ORDER BY relevance_score DESC LIMIT 3", (week_ago,))
            rows = c.fetchall()
            modules.append({
                "id": "market",
                "label": "市场情报",
                "href": "/insights/demand",
                "items": [{"title": r["title"], "tag": "情报"} for r in rows] if rows else [],
            })
        except Exception:
            modules.append({"id": "market", "label": "市场情报", "href": "/insights/market", "items": []})

        # 2. 行业全景 - 从 industry_news 取
        try:
            c.execute("SELECT title, source, category FROM industry_news WHERE crawl_date >= %s ORDER BY id DESC LIMIT 3", (week_ago,))
            rows = c.fetchall()
            modules.append({
                "id": "industry",
                "label": "行业全景",
                "href": "/insights/industry",
                "items": [{"title": r["title"], "tag": r["source"]} for r in rows] if rows else [],
            })
        except Exception:
            modules.append({"id": "industry", "label": "行业全景", "href": "/insights/industry", "items": []})

        # 3. 技术热点 - 从 github_trending 取
        try:
            c.execute("SELECT repo_name, language, today_stars FROM github_trending WHERE scrape_date = %s AND category = 'daily' ORDER BY id LIMIT 3", (today,))
            rows = c.fetchall()
            modules.append({
                "id": "hotspots",
                "label": "技术热点",
                "href": "/insights/hotspots",
                "items": [{"title": r["repo_name"], "tag": r["language"] or "Trending"} for r in rows] if rows else [],
            })
        except Exception:
            modules.append({"id": "hotspots", "label": "技术热点", "href": "/insights/hotspots", "items": []})

        # 4. 解决方案洞察 - 阿里云技术解决方案
        try:
            c.execute("""
                SELECT title, category, first_seen_date, last_changed_date
                FROM aliyun_solutions WHERE is_active=TRUE
                ORDER BY last_changed_date DESC, id DESC LIMIT 3
            """)
            rows = c.fetchall()
            modules.append({
                "id": "solutions",
                "label": "解决方案洞察",
                "href": "/insights/solutions",
                "items": [{
                    "title": r["title"],
                    "tag": "NEW" if r["first_seen_date"] == today else r["category"],
                } for r in rows] if rows else [],
            })
        except Exception:
            modules.append({"id": "solutions", "label": "解决方案洞察", "href": "/insights/solutions", "items": []})

        # 5. 友商洞察 - 从 competitor_news / cloud_vendor_news 取
        try:
            c.execute("SELECT title, vendor, category FROM cloud_vendor_news WHERE crawl_date >= %s ORDER BY id DESC LIMIT 3", (week_ago,))
            rows = c.fetchall()
            if not rows:
                c.execute("SELECT title, vendor, category FROM competitor_news WHERE scrape_date >= %s ORDER BY id DESC LIMIT 3", (week_ago,))
                rows = c.fetchall()
            modules.append({
                "id": "competitors",
                "label": "友商洞察",
                "href": "/insights/competitors",
                "items": [{"title": r["title"], "tag": r["vendor"]} for r in rows] if rows else [],
            })
        except Exception:
            modules.append({"id": "competitors", "label": "友商洞察", "href": "/insights/competitors", "items": []})

        # 5. 政策法规 - 从 policy_updates 取
        try:
            c.execute("SELECT title, source, severity FROM policy_updates WHERE crawl_date >= %s ORDER BY id DESC LIMIT 3", (week_ago,))
            rows = c.fetchall()
            modules.append({
                "id": "policy",
                "label": "政策法规",
                "href": "/insights/policy",
                "items": [{"title": r["title"], "tag": r["source"]} for r in rows] if rows else [],
            })
        except Exception:
            modules.append({"id": "policy", "label": "政策法规", "href": "/insights/policy", "items": []})

        # 6. 商业机会 - 从 bidding_opportunities 取
        try:
            c.execute("SELECT title, industry, budget FROM bidding_opportunities WHERE bid_date >= %s ORDER BY relevance_score DESC LIMIT 3", (week_ago,))
            rows = c.fetchall()
            if not rows:
                c.execute("SELECT title, industry, budget FROM bidding_opportunities ORDER BY relevance_score DESC NULLS LAST, id DESC LIMIT 3")
                rows = c.fetchall()
            modules.append({
                "id": "opportunities",
                "label": "商业机会",
                "href": "/insights/opportunities",
                "items": [{"title": r["title"], "tag": r["industry"]} for r in rows] if rows else [],
            })
        except Exception:
            modules.append({"id": "opportunities", "label": "商业机会", "href": "/insights/opportunities", "items": []})

        # 7. 商业快讯 - 从 industry_news 取最新
        try:
            c.execute("SELECT title, source FROM industry_news ORDER BY id DESC LIMIT 3")
            rows = c.fetchall()
            modules.append({
                "id": "news",
                "label": "商业快讯",
                "href": "/insights/news",
                "items": [{"title": r["title"], "tag": r["source"]} for r in rows] if rows else [],
            })
        except Exception:
            modules.append({"id": "news", "label": "商业快讯", "href": "/insights/news", "items": []})

        # 8. 招标信息 - 从 bidding_opportunities 取
        try:
            c.execute("SELECT title, industry FROM bidding_opportunities WHERE bid_date >= %s ORDER BY id DESC LIMIT 3", (week_ago,))
            rows = c.fetchall()
            if not rows:
                c.execute("SELECT title, industry FROM bidding_opportunities ORDER BY id DESC LIMIT 3")
                rows = c.fetchall()
            modules.append({
                "id": "bidding",
                "label": "招标信息",
                "href": "/insights/bidding",
                "items": [{"title": r["title"], "tag": r["industry"]} for r in rows] if rows else [],
            })
        except Exception:
            modules.append({"id": "bidding", "label": "招标信息", "href": "/insights/bidding", "items": []})

    return modules


# ──────────────────────────────────────────────
# 爬虫 7: 招标信息爬虫（搜索公开招标公告）
# ──────────────────────────────────────────────

def crawl_bidding() -> list[dict]:
    """抓取公开招标信息（从中国政府采购网等公开源）"""
    items = []

    # 策略1: 中国政府购买服务信息平台
    sources = [
        ("http://www.ccgp.gov.cn/cggg/zygg/", "中央采购"),
        ("http://www.ccgp.gov.cn/cggg/dfgg/", "地方采购"),
    ]
    seen_titles = set()
    for url, source_name in sources:
        try:
            resp = _safe_get(url, timeout=15)
            if resp:
                resp.encoding = 'utf-8'
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.select("a[href*='zbgg'], a[href*='cggg'], a[class*='title'], li a")[:20]:
                    title = _clean(a.get_text())
                    href = a.get("href", "")
                    if title and len(title) > 10 and title not in seen_titles:
                        seen_titles.add(title)
                        href = urljoin(url, href)
                        parent_text = _clean(a.parent.get_text(" ", strip=True)) if a.parent else ""
                        date_match = re.search(r"20\d{2}-\d{2}-\d{2}", parent_text)
                        # 尝试提取行业分类
                        industry = "政务"
                        for kw, ind in [("医疗", "医疗"), ("医院", "医疗"), ("卫生", "医疗"),
                                         ("学校", "教育"), ("教育", "教育"), ("大学", "教育"),
                                         ("交通", "交通"), ("公路", "交通"), ("地铁", "交通"),
                                         ("能源", "能源"), ("电力", "能源"), ("电网", "能源"),
                                         ("制造", "制造"), ("工业", "制造"), ("工厂", "制造"),
                                         ("金融", "金融"), ("银行", "金融"), ("保险", "金融"),
                                         ("农业", "农业"), ("农村", "农业"), ("农", "农业"),
                                         ("零售", "零售"), ("超市", "零售"), ("电商", "零售")]:
                            if kw in title:
                                industry = ind
                                break
                        items.append({
                            "source": source_name,
                            "bid_date": date_match.group(0) if date_match else datetime.now().strftime("%Y-%m-%d"),
                            "industry": industry,
                            "title": title,
                            "procuring_entity": "",
                            "budget": "",
                            "deadline": "",
                            "summary": "",
                            "url": href,
                            "relevance_score": 0.7,
                        })
        except Exception:
            pass

    # 策略2: 搜索百度招标信息
    try:
        search_url = "https://www.baidu.com/s?wd=招标公告+数字化+信息化+项目&rn=15"
        resp = _safe_get(search_url, timeout=10)
        if resp:
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, "html.parser")
            for result in soup.select(".result, .c-container, [class*='result']")[:10]:
                a = result.select_one("a")
                if a:
                    title = _clean(a.get_text())
                    href = a.get("href", "")
                    if title and len(title) > 10 and "招标" in title and title not in seen_titles:
                        seen_titles.add(title)
                        industry = "政务"
                        for kw, ind in [("医疗", "医疗"), ("医院", "医疗"), ("教育", "教育"),
                                         ("交通", "交通"), ("能源", "能源"), ("电力", "能源"),
                                         ("制造", "制造"), ("金融", "金融"), ("农业", "农业")]:
                            if kw in title:
                                industry = ind
                                break
                        items.append({
                            "source": "百度招标",
                            "industry": industry,
                            "title": title,
                            "procuring_entity": "",
                            "budget": "",
                            "deadline": "",
                            "summary": "",
                            "url": href,
                            "relevance_score": 0.6,
                        })
    except Exception:
        pass

    return items[:20]


# ──────────────────────────────────────────────
# 工具: 从新闻和政策数据推导需求信号
# ──────────────────────────────────────────────

def derive_demand_signals() -> list[dict]:
    """
    从已爬取的行业新闻和政策数据中推导需求信号。
    使用多关键词权重匹配 + 综合评分生成需求信号。
    """
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    signals = []

    # 行业关键词权重表：关键词 → (行业, 权重)
    industry_keywords = [
        # 医疗（高优先级关键词排前面）
        ("医疗", "医疗", 1.0), ("医院", "医疗", 0.9), ("卫生", "医疗", 0.8),
        ("临床", "医疗", 0.7), ("影像诊断", "医疗", 0.9), ("电子病历", "医疗", 0.9),
        # 教育
        ("教育", "教育", 1.0), ("学校", "教育", 0.8), ("校园", "教育", 0.7),
        # 交通
        ("交通", "交通", 1.0), ("公路", "交通", 0.8), ("地铁", "交通", 0.9),
        ("自动驾驶", "交通", 0.9), ("低空", "交通", 0.8),
        # 能源
        ("能源", "能源", 1.0), ("电力", "能源", 0.9), ("新能源", "能源", 0.9),
        ("电网", "能源", 0.8), ("光伏", "能源", 0.8),
        # 制造
        ("制造", "制造", 1.0), ("工业", "制造", 0.9), ("工厂", "制造", 0.7),
        ("汽车", "制造", 0.8), ("质检", "制造", 0.8), ("工业互联网", "制造", 1.0),
        # 金融
        ("金融", "金融", 1.0), ("银行", "金融", 0.9), ("保险", "金融", 0.8),
        ("核心系统", "金融", 0.9), ("分布式", "金融", 0.7),
        # 农业
        ("农业", "农业", 1.0), ("农村", "农业", 0.8), ("农机", "农业", 0.7),
        # 零售
        ("零售", "零售", 1.0), ("电商", "零售", 0.9), ("供应链", "零售", 0.8),
        # 政务
        ("政务", "政务", 1.0), ("政府", "政务", 0.8), ("信创", "政务", 0.9),
        # 通用/技术
        ("AI", "通用", 0.6), ("大模型", "通用", 0.7), ("云", "通用", 0.5),
        ("数据", "通用", 0.5), ("数字化", "通用", 0.7), ("安全", "通用", 0.6),
    ]

    def match_industry(text: str) -> tuple[str, float]:
        """多关键词权重匹配：返回 (行业, 最高权重)"""
        best_industry, best_weight = "通用", 0.0
        for kw, ind, weight in industry_keywords:
            if kw in text and weight > best_weight:
                best_industry, best_weight = ind, weight
        return best_industry, best_weight

    with get_db() as conn:
        c = conn.cursor()

        # 从 industry_news 提取
        try:
            c.execute("SELECT title, summary, source, category, url FROM industry_news WHERE crawl_date >= %s ORDER BY id DESC LIMIT 50", (week_ago,))
            rows = c.fetchall()
            for row in rows:
                title = row["title"]
                summary = row["summary"] or ""
                url = row["url"]
                combined = f"{title} {summary}"

                # 多关键词权重匹配行业
                industry, ind_weight = match_industry(combined)

                # 综合相关性分数
                score = 0.4 + ind_weight * 0.2  # 基础分 + 行业匹配权重
                if any(kw in combined for kw in ["发布", "推出", "上线", "启动", "合作", "投资"]):
                    score += 0.15
                if any(kw in combined for kw in ["数字化", "AI", "智能", "云", "大数据"]):
                    score += 0.15
                if any(kw in combined for kw in ["招标", "采购", "预算"]):
                    score += 0.1

                signals.append({
                    "source_type": "news", "industry": industry,
                    "title": title, "summary": summary[:200],
                    "url": url or "", "relevance_score": min(round(score, 2), 0.95),
                    "demand_tags": ",".join([kw for kw in ["AI", "数字化", "云", "大数据", "智能", "信创", "安全", "物联网"]
                                             if kw in combined]),
                })
        except Exception:
            pass

        # 从 policy_updates 提取
        try:
            c.execute("SELECT title, summary, source, url, severity FROM policy_updates WHERE crawl_date >= %s ORDER BY id DESC LIMIT 30", (week_ago,))
            rows = c.fetchall()
            for row in rows:
                title = row["title"]
                summary = row["summary"] or ""
                url = row["url"]
                combined = f"{title} {summary}"
                industry, _ = match_industry(combined)
                if industry == "通用":
                    # 政策类默认归为政务
                    industry = "政务"
                signals.append({
                    "source_type": "policy", "industry": industry,
                    "title": title, "summary": summary[:200],
                    "url": url or "", "relevance_score": 0.85,
                    "demand_tags": "政策,数字化",
                })
        except Exception:
            pass

    return signals[:30]


if __name__ == "__main__":
    # 测试爬虫
    init_crawler_tables()
    stats = run_daily_crawl()
    print(f"\n爬取统计: {json.dumps(stats, ensure_ascii=False, indent=2)}")
    # 测试招标爬虫
    bidding = crawl_bidding()
    print(f"\n招标爬虫: {len(bidding)} 条")
    # 测试需求信号推导
    signals = derive_demand_signals()
    print(f"\n需求信号推导: {len(signals)} 条")
