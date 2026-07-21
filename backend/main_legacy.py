"""
Legacy functions used by routers during migration.
Will be gradually emptied as functions move to services/* or crawlers/*.
"""
import sys
import json
import re
import httpx
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from db import get_db
from settings import settings

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')


# ─── GitHub Crawler ───
def scrape_github_trending(since="daily", spoken_language="") -> list:
    url = f"https://github.com/trending?since={since}"
    if spoken_language:
        url += f"&spoken_language_code={spoken_language}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    items = []
    for article in soup.select("article.Box-row"):
        h2 = article.select_one("h2 a")
        if not h2:
            continue
        repo_path = h2.get("href", "").strip("/")
        repo_url = f"https://github.com/{repo_path}"
        desc_el = article.select_one("p")
        description = desc_el.get_text(strip=True) if desc_el else ""
        lang_el = article.select_one("[itemprop='programmingLanguage']")
        language = lang_el.get_text(strip=True) if lang_el else "N/A"
        stars_forks = article.select("a.Link--muted")
        stars = stars_forks[0].get_text(strip=True) if len(stars_forks) > 0 else "0"
        forks = stars_forks[1].get_text(strip=True) if len(stars_forks) > 1 else "0"
        today_stars_el = article.select_one("span.d-inline-block.float-sm-right")
        today_stars = today_stars_el.get_text(strip=True) if today_stars_el else ""
        items.append({
            "repo_name": repo_path, "repo_url": repo_url,
            "description": description, "language": language,
            "stars": stars, "forks": forks,
            "today_stars": today_stars, "category": since,
        })
    return items


def refresh_and_store():
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    total = 0
    for period in ["daily", "weekly", "monthly"]:
        try:
            items = scrape_github_trending(since=period)
            with get_db() as conn:
                c = conn.cursor()
                for item in items:
                    c.execute("""
                        INSERT INTO github_trending
                        (scrape_date, scrape_time, repo_name, repo_url, description, language, stars, forks, today_stars, category)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (scrape_date, category, repo_name) DO NOTHING
                    """, (date_str, time_str, item["repo_name"], item["repo_url"],
                          item["description"], item["language"], item["stars"],
                          item["forks"], item["today_stars"], item["category"]))
            total += len(items)
        except Exception as e:
            print(f"[GitHub] {period} 抓取失败: {e}")
    with get_db() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO scrape_log (scrape_date, scrape_time, status, items_count) VALUES (%s, %s, %s, %s)",
                  (date_str, time_str, "success" if total > 0 else "failed", total))
    print(f"[GitHub] 刷新完成，共 {total} 项")


# ─── Business Evaluation ───
BUSINESS_EVAL_SYSTEM_PROMPT = """你是开源项目解决方案实践业务评估专家。采用四维评估模型对每个 GitHub 项目评分（每维 0-10 分，总分 = 0.25*(d1+d2+d3+d4)）：
【D1 服务端属性 25%】【D2 营销价值 25%】【D3 场景价值 25%】【D4 云上部署价值 25%】
等级：8-10 强烈推荐 / 6-7.9 值得做 / 4-5.9 勉强可做 / 0-3.9 不建议。
你必须只输出一个 JSON 数组。每个元素：{"repo_name":"owner/repo","d1":数字,"d2":数字,"d3":数字,"d4":数字,"total":数字,"level":"...","recommendation":"...","reasoning":"..."}"""


def _parse_eval_json(raw: str) -> list:
    if not raw:
        return []
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        return json.loads(text[start:end+1])
    except Exception:
        return []


def evaluate_trending_business(limit: int = 10) -> dict:
    if not settings.CHAT_API_KEY:
        return {"status": "skipped", "count": 0}
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M:%S")
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT repo_name, repo_url, description, language, stars FROM github_trending WHERE scrape_date = %s AND category = 'daily' ORDER BY id LIMIT %s", (date_str, limit))
        rows = c.fetchall()
    if not rows:
        return {"status": "skipped", "count": 0}
    project_lines = [f"{i+1}. {r['repo_name']} | Stars={r['stars'] or 'N/A'} | {r['description'] or ''}" for i, r in enumerate(rows)]
    user_prompt = "对以下 GitHub Trending 项目逐一进行四维业务价值评估，严格按指定 JSON 数组格式输出：\n\n" + "\n".join(project_lines)
    try:
        resp = httpx.post(settings.CHAT_API_URL,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.CHAT_API_KEY}"},
            json={"model": settings.CHAT_MODEL, "messages": [
                {"role": "system", "content": BUSINESS_EVAL_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ], "temperature": 0.2, "max_tokens": 4096}, timeout=120)
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[business-eval] AI 调用失败: {e}")
        return {"status": "error", "count": 0}
    results = _parse_eval_json(raw)
    if not results:
        return {"status": "error", "count": 0}
    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM trending_business_eval WHERE scrape_date = %s", (date_str,))
        for item in results:
            rn = item.get("repo_name", "")
            if not rn:
                continue
            match = next((r for r in rows if r["repo_name"] == rn), None)
            c.execute("INSERT INTO trending_business_eval (scrape_date, repo_name, repo_url, language, stars, d1, d2, d3, d4, total, level, recommendation, reasoning, eval_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (date_str, rn, match["repo_url"] if match else None, match["language"] if match else None, match["stars"] if match else None,
                 item.get("d1"), item.get("d2"), item.get("d3"), item.get("d4"), item.get("total"), item.get("level"), item.get("recommendation"), item.get("reasoning"), time_str))
    print(f"[business-eval] 完成，共 {len(results)} 项")
    return {"status": "success", "count": len(results), "date": date_str}


# ─── Baidu Hot Search ───
def _fetch_baidu_hotsearch_sync():
    try:
        url = "https://top.baidu.com/board?tab=realtime"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "text/html"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        text = resp.text
        items = []
        sdata_matches = re.findall(r'<!--\s*(.*?)\s*-->', text, re.DOTALL)
        for sdata in sdata_matches:
            sdata = sdata.strip()
            if sdata.startswith('{') or sdata.startswith('['):
                try:
                    parsed = json.loads(sdata)
                    if isinstance(parsed, dict):
                        cards = parsed.get('cards', []) or []
                        for card in cards:
                            content = card.get('content', {}) or {}
                            for word in content.get('word', []):
                                title = word.get('word', '') or ''
                                hs = word.get('hotScore', '') or ''
                                if title:
                                    items.append({"rank": len(items)+1, "title": title, "hot": str(hs) if hs else "热", "link": f"https://www.baidu.com/s?wd={title}"})
                                    if len(items) >= 10: break
                    if items: break
                except Exception:
                    continue
        if not items:
            soup = BeautifulSoup(text, 'html.parser')
            for selector in ['.category-wrap_iQLoo', '[class*="category-wrap"]', '.hot-list-item']:
                els = soup.select(selector)
                if els:
                    for el in els[:10]:
                        te = el.select_one('.c-single-text-ellipsis, [class*="ellipsis"]') or el
                        title = te.get_text(strip=True) if te else ''
                        if title and len(title) > 1 and '百度' not in title and '广告' not in title:
                            items.append({"rank": len(items)+1, "title": title, "hot": "热", "link": f"https://www.baidu.com/s?wd={title}"})
                            if len(items) >= 10: break
                    if items: break
        if items:
            now = datetime.now()
            with get_db() as conn:
                c = conn.cursor()
                for it in items:
                    c.execute("INSERT INTO baidu_hotsearch (scrape_date, scrape_time, rank, title, hot, link) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (scrape_date, title) DO NOTHING",
                              (now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), it["rank"], it["title"], it["hot"], it["link"]))
            return items
        with get_db() as conn:
            c = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")
            c.execute("SELECT * FROM baidu_hotsearch WHERE scrape_date = %s ORDER BY rank LIMIT 10", (today,))
            rows = c.fetchall()
        if rows:
            return [dict(r) for r in rows]
        return [{"rank": 1, "title": "数据抓取中...", "hot": "---", "link": "#"}]
    except Exception as e:
        print(f"百度热搜失败: {e}")
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM baidu_hotsearch WHERE scrape_date = %s ORDER BY rank LIMIT 10", (datetime.now().strftime("%Y-%m-%d"),))
                rows = c.fetchall()
            if rows: return [dict(r) for r in rows]
        except Exception:
            pass
        return [{"rank": 1, "title": "热搜加载失败", "hot": "---", "link": "#"}]


# ─── Competitor News ───
def get_competitor_news(date: str = None) -> list:
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM competitor_news WHERE scrape_date = %s ORDER BY id", (date,))
        return [dict(r) for r in c.fetchall()]


def get_competitor_summary(limit_per_vendor: int = 3) -> dict:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY vendor ORDER BY scrape_date DESC, id DESC) as rn FROM competitor_news) WHERE rn <= %s ORDER BY vendor, rn", (limit_per_vendor,))
        grouped = {}
        for row in [dict(r) for r in c.fetchall()]:
            v = row["vendor"]
            if v not in grouped:
                grouped[v] = []
            grouped[v].append({"id": row["id"], "title": row["title"], "summary": row["summary"], "link": row["link"], "category": row["category"], "date": row["scrape_date"]})
        return grouped


def refresh_competitor_news():
    today = datetime.now().strftime("%Y-%m-%d")
    from crawlers import crawl_cloud_vendors
    items = crawl_cloud_vendors()
    if not items:
        print(f"[{today}] 云厂商爬虫未返回数据")
        return []
    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM competitor_news WHERE scrape_date = %s", (today,))
        for item in items:
            c.execute("INSERT INTO competitor_news (scrape_date, vendor, title, summary, link, category) VALUES (%s,%s,%s,%s,%s,%s)",
                      (today, item.get("vendor", ""), item["title"], item.get("summary", ""), item.get("url", ""), item.get("category", "产品动态")))
    return get_competitor_news(today)


# ─── Cleanup ───
def cleanup_old_data():
    cutoff_90 = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    cutoff_180 = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    with get_db() as conn:
        c = conn.cursor()
        for table in ["github_trending", "trending_business_eval", "baidu_hotsearch", "scrape_log", "competitor_news"]:
            c.execute(f"DELETE FROM {table} WHERE scrape_date < %s", (cutoff_90,))
        c.execute("DELETE FROM demand_signals WHERE signal_date < %s", (cutoff_90,))
        c.execute("DELETE FROM bidding_opportunities WHERE bid_date < %s", (cutoff_90,))
        c.execute("DELETE FROM demand_reports WHERE report_date < %s", (cutoff_90,))
        c.execute("DELETE FROM page_visits WHERE created_at < %s", (cutoff_180,))


# ─── Deep Research wrapper ───
async def deep_research(query: str, max_iter: int = 2) -> dict:
    try:
        from deep_searcher_integration import deep_research as dr
        return await dr(query, max_iter=max_iter)
    except Exception as e:
        return {"answer": f"深度研究出错: {e}", "sources": []}
