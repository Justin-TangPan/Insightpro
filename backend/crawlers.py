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

import requests
from bs4 import BeautifulSoup
import sqlite3
import json
import re
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_PATH = os.path.join(os.path.dirname(__file__), "trending.db")

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


def _safe_get(url: str, **kwargs) -> requests.Response | None:
    """安全 HTTP GET，失败返回 None"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp
    except Exception as e:
        print(f"[Crawler] GET {url} failed: {e}")
        return None


def _init_table(table_name: str, schema: str, indexes: list[str] = None):
    """通用建表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(schema)
    if indexes:
        for idx_sql in indexes:
            c.execute(idx_sql)
    conn.commit()
    conn.close()


def _store_items(table: str, columns: list[str], items: list[dict], date_col: str, dedup_cols: list[str] = None):
    """通用数据入库（去重）"""
    if not items:
        return 0
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    placeholders = ", ".join(["?"] * len(columns))
    col_str = ", ".join(columns)
    sql = f"INSERT OR IGNORE INTO {table} ({col_str}) VALUES ({placeholders})"
    count = 0
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
    conn.commit()
    conn.close()
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

def crawl_cloud_vendors() -> list[dict]:
    """抓取各云厂商最新动态（多策略）"""
    items = []

    # 策略1: 华为云官网新闻
    try:
        resp = _safe_get("https://www.huaweicloud.com/news/")
        if resp:
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, "html.parser")
            count = 0
            for a in soup.select("a")[:50]:
                title = _clean(a.get_text())
                href = a.get("href", "")
                if title and len(title) > 8 and ("华为" in title or "云" in title or "AI" in title
                    or "发布" in title or "解决方案" in title or "客户" in title or "峰会" in title):
                    if not href.startswith("http"):
                        href = f"https://www.huaweicloud.com{href}"
                    items.append({
                        "vendor": "华为云", "source": "华为云",
                        "title": title, "summary": "", "url": href,
                        "category": "产品动态",
                    })
                    count += 1
                    if count >= 3:
                        break
    except Exception:
        pass

    # 策略2: 阿里云动态
    try:
        resp = _safe_get("https://www.aliyun.com/activity/")
        if resp:
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, "html.parser")
            count = 0
            for a in soup.select("a")[:50]:
                title = _clean(a.get_text())
                href = a.get("href", "")
                if title and len(title) > 6:
                    if not href.startswith("http"):
                        href = f"https://www.aliyun.com{href}"
                    items.append({
                        "vendor": "阿里云", "source": "阿里云",
                        "title": title, "summary": "", "url": href,
                        "category": "产品动态",
                    })
                    count += 1
                    if count >= 3:
                        break
    except Exception:
        pass

    # 策略3: 腾讯云动态
    try:
        resp = _safe_get("https://cloud.tencent.com/act")
        if resp:
            soup = BeautifulSoup(resp.text, "html.parser")
            count = 0
            for a in soup.select("a")[:50]:
                title = _clean(a.get_text())
                href = a.get("href", "")
                if title and len(title) > 6:
                    if not href.startswith("http"):
                        href = f"https://cloud.tencent.com{href}"
                    items.append({
                        "vendor": "腾讯云", "source": "腾讯云",
                        "title": title, "summary": "", "url": href,
                        "category": "产品动态",
                    })
                    count += 1
                    if count >= 3:
                        break
    except Exception:
        pass

    # 策略4: 火山引擎动态
    try:
        resp = _safe_get("https://www.volcengine.com/")
        if resp:
            soup = BeautifulSoup(resp.text, "html.parser")
            count = 0
            for a in soup.select("a")[:50]:
                title = _clean(a.get_text())
                href = a.get("href", "")
                if title and len(title) > 6:
                    if not href.startswith("http"):
                        href = f"https://www.volcengine.com{href}"
                    items.append({
                        "vendor": "火山云", "source": "火山云",
                        "title": title, "summary": "", "url": href,
                        "category": "产品动态",
                    })
                    count += 1
                    if count >= 3:
                        break
    except Exception:
        pass

    # 策略5: AWS 中国
    try:
        resp = _safe_get("https://www.amazonaws.cn/about-aws/news/")
        if resp:
            soup = BeautifulSoup(resp.text, "html.parser")
            count = 0
            for a in soup.select("a")[:50]:
                title = _clean(a.get_text())
                href = a.get("href", "")
                if title and len(title) > 8:
                    if not href.startswith("http"):
                        href = f"https://www.amazonaws.cn{href}"
                    items.append({
                        "vendor": "AWS", "source": "AWS",
                        "title": title, "summary": "", "url": href,
                        "category": "产品动态",
                    })
                    count += 1
                    if count >= 3:
                        break
    except Exception:
        pass

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
    """初始化爬虫数据表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 行业新闻（聚合 36氪/财联社/第一财经/AI产业）
    c.execute("""
        CREATE TABLE IF NOT EXISTS industry_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crawl_date TEXT NOT NULL,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT,
            category TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_indnews_date ON industry_news(crawl_date)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_indnews_unique ON industry_news(crawl_date, source, title)")

    # 政策法规
    c.execute("""
        CREATE TABLE IF NOT EXISTS policy_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crawl_date TEXT NOT NULL,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT,
            category TEXT,
            severity TEXT DEFAULT 'medium',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_policy_date ON policy_updates(crawl_date)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_policy_unique ON policy_updates(crawl_date, source, title)")

    # 云厂商动态
    c.execute("""
        CREATE TABLE IF NOT EXISTS cloud_vendor_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crawl_date TEXT NOT NULL,
            vendor TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT,
            category TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_cloudnews_date ON cloud_vendor_news(crawl_date)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_cloudnews_unique ON cloud_vendor_news(crawl_date, vendor, title)")

    conn.commit()
    conn.close()


def store_crawl_results(results: dict) -> dict:
    """将爬取结果存入数据库，返回统计"""
    today = datetime.now().strftime("%Y-%m-%d")
    stats = {}

    # 36氪 + 财联社 + 第一财经 + AI产业 → industry_news
    news_items = []
    for key in ["36kr", "cls", "yicai", "ai_news"]:
        for item in results.get(key, []):
            item["crawl_date"] = today
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO scrape_log (scrape_date, scrape_time, status, items_count)
        VALUES (?, ?, ?, ?)
    """, (now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
          "success" if total > 0 else "empty", total))
    conn.commit()
    conn.close()

    return stats


# ──────────────────────────────────────────────
# 查询接口（供 main.py API 调用）
# ──────────────────────────────────────────────

def get_industry_news(days: int = 7, source: str = None, limit: int = 50) -> list[dict]:
    """获取行业新闻"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    query = "SELECT * FROM industry_news WHERE crawl_date >= ?"
    params = [cutoff]
    if source:
        query += " AND source = ?"
        params.append(source)
    query += " ORDER BY crawl_date DESC, id DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_policy_updates(days: int = 30, limit: int = 50) -> list[dict]:
    """获取政策法规"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    c.execute("SELECT * FROM policy_updates WHERE crawl_date >= ? ORDER BY crawl_date DESC, id DESC LIMIT ?",
              (cutoff, limit))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_cloud_vendor_news(days: int = 7, vendor: str = None, limit: int = 50) -> list[dict]:
    """获取云厂商动态"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    query = "SELECT * FROM cloud_vendor_news WHERE crawl_date >= ?"
    params = [cutoff]
    if vendor:
        query += " AND vendor = ?"
        params.append(vendor)
    query += " ORDER BY crawl_date DESC, id DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_homepage_stats() -> dict:
    """获取首页看板统计数据（从数据库实时聚合）"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    stats = {}

    # 行业新闻数（本周）
    try:
        c.execute("SELECT COUNT(*) FROM industry_news WHERE crawl_date >= ?", (week_ago,))
        stats["news_count"] = c.fetchone()[0]
    except Exception:
        stats["news_count"] = 0

    # GitHub Trending 项目数（今天）
    try:
        c.execute("SELECT COUNT(*) FROM github_trending WHERE scrape_date = ?", (today,))
        stats["trending_today"] = c.fetchone()[0]
    except Exception:
        stats["trending_today"] = 0

    # 百度热搜数（今天）
    try:
        c.execute("SELECT COUNT(*) FROM baidu_hotsearch WHERE scrape_date = ?", (today,))
        stats["hotsearch_today"] = c.fetchone()[0]
    except Exception:
        stats["hotsearch_today"] = 0

    # 友商动态数（本周）
    try:
        c.execute("SELECT COUNT(*) FROM competitor_news WHERE scrape_date >= ?", (week_ago,))
        stats["competitor_count"] = c.fetchone()[0]
    except Exception:
        stats["competitor_count"] = 0

    # 招标信息数
    try:
        c.execute("SELECT COUNT(*) FROM bidding_opportunities WHERE bid_date >= ?", (week_ago,))
        stats["bidding_count"] = c.fetchone()[0]
    except Exception:
        stats["bidding_count"] = 0

    # 需求信号数
    try:
        c.execute("SELECT COUNT(*) FROM demand_signals WHERE signal_date >= ?", (week_ago,))
        stats["demand_count"] = c.fetchone()[0]
    except Exception:
        stats["demand_count"] = 0

    # 政策法规数
    try:
        c.execute("SELECT COUNT(*) FROM policy_updates WHERE crawl_date >= ?", (week_ago,))
        stats["policy_count"] = c.fetchone()[0]
    except Exception:
        stats["policy_count"] = 0

    # 云厂商动态数
    try:
        c.execute("SELECT COUNT(*) FROM cloud_vendor_news WHERE crawl_date >= ?", (week_ago,))
        stats["cloud_news_count"] = c.fetchone()[0]
    except Exception:
        stats["cloud_news_count"] = 0

    # GitHub trending 总历史记录数
    try:
        c.execute("SELECT COUNT(*) FROM github_trending")
        stats["trending_total"] = c.fetchone()[0]
    except Exception:
        stats["trending_total"] = 0

    # 爬取日志 - 最近一次状态
    try:
        c.execute("SELECT status, items_count, scrape_time FROM scrape_log ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        if row:
            stats["last_crawl"] = {"status": row[0], "count": row[1], "time": row[2]}
        else:
            stats["last_crawl"] = None
    except Exception:
        stats["last_crawl"] = None

    conn.close()
    return stats


def get_homepage_modules() -> list[dict]:
    """
    获取首页各模块预览数据（每个模块最新 3 条）。
    从多个表聚合，返回结构化数据供前端渲染。
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    modules = []

    # 1. 市场情报 - 从 demand_signals 取
    try:
        c.execute("SELECT title, summary FROM demand_signals WHERE signal_date >= ? ORDER BY relevance_score DESC LIMIT 3", (week_ago,))
        rows = c.fetchall()
        modules.append({
            "id": "market",
            "label": "市场情报",
            "href": "/insights/market",
            "items": [{"title": r["title"], "tag": "情报"} for r in rows] if rows else [],
        })
    except Exception:
        modules.append({"id": "market", "label": "市场情报", "href": "/insights/market", "items": []})

    # 2. 行业全景 - 从 industry_news 取
    try:
        c.execute("SELECT title, source, category FROM industry_news WHERE crawl_date >= ? ORDER BY id DESC LIMIT 3", (week_ago,))
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
        c.execute("SELECT repo_name, language, today_stars FROM github_trending WHERE scrape_date = ? AND category = 'daily' ORDER BY id LIMIT 3", (today,))
        rows = c.fetchall()
        modules.append({
            "id": "hotspots",
            "label": "技术热点",
            "href": "/insights/hotspots",
            "items": [{"title": r["repo_name"], "tag": r["language"] or "Trending"} for r in rows] if rows else [],
        })
    except Exception:
        modules.append({"id": "hotspots", "label": "技术热点", "href": "/insights/hotspots", "items": []})

    # 4. 友商洞察 - 从 competitor_news / cloud_vendor_news 取
    try:
        c.execute("SELECT title, vendor, category FROM cloud_vendor_news WHERE crawl_date >= ? ORDER BY id DESC LIMIT 3", (week_ago,))
        rows = c.fetchall()
        if not rows:
            c.execute("SELECT title, vendor, category FROM competitor_news WHERE scrape_date >= ? ORDER BY id DESC LIMIT 3", (week_ago,))
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
        c.execute("SELECT title, source, severity FROM policy_updates WHERE crawl_date >= ? ORDER BY id DESC LIMIT 3", (week_ago,))
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
        c.execute("SELECT title, industry, budget FROM bidding_opportunities WHERE bid_date >= ? ORDER BY relevance_score DESC LIMIT 3", (week_ago,))
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
        c.execute("SELECT title, industry FROM bidding_opportunities WHERE bid_date >= ? ORDER BY id DESC LIMIT 3", (week_ago,))
        rows = c.fetchall()
        modules.append({
            "id": "bidding",
            "label": "招标信息",
            "href": "/insights/bidding",
            "items": [{"title": r["title"], "tag": r["industry"]} for r in rows] if rows else [],
        })
    except Exception:
        modules.append({"id": "bidding", "label": "招标信息", "href": "/insights/bidding", "items": []})

    conn.close()
    return modules


if __name__ == "__main__":
    # 测试爬虫
    init_crawler_tables()
    stats = run_daily_crawl()
    print(f"\n爬取统计: {json.dumps(stats, ensure_ascii=False, indent=2)}")
