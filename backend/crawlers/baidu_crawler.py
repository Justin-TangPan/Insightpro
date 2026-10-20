"""Baidu hot search scraper."""
import json
import logging
import re

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from db import get_db

logger = logging.getLogger(__name__)


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
                                    items.append({"rank": len(items)+1, "title": title, "hot": str(hs) if hs else "Hot", "link": f"https://www.baidu.com/s?wd={title}"})
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
                            items.append({"rank": len(items)+1, "title": title, "hot": "Hot", "link": f"https://www.baidu.com/s?wd={title}"})
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
        return [{"rank": 1, "title": "Loading data...", "hot": "---", "link": "#"}]
    except Exception as e:
        logger.warning("Baidu hotsearch failed: %s", e)
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM baidu_hotsearch WHERE scrape_date = %s ORDER BY rank LIMIT 10", (datetime.now().strftime("%Y-%m-%d"),))
                rows = c.fetchall()
            if rows: return [dict(r) for r in rows]
        except Exception as fallback_err:
            logger.debug("Baidu hotsearch DB fallback also failed: %s", fallback_err)
        return [{"rank": 1, "title": "Hot search load failed", "hot": "---", "link": "#"}]
