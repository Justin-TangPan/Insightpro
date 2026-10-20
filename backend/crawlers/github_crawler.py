"""GitHub Trending scraper and persistence."""
import logging

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from db import get_db

logger = logging.getLogger(__name__)


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
            logger.warning("GitHub %s scrape failed: %s", period, e)
    with get_db() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO scrape_log (scrape_date, scrape_time, status, items_count) VALUES (%s, %s, %s, %s)",
                  (date_str, time_str, "success" if total > 0 else "failed", total))
    logger.info("GitHub refresh done, %d items", total)


def _fetch_github_readme(repo_name: str, fallback: str = "") -> str:
    try:
        response = requests.get(
            f"https://api.github.com/repos/{repo_name}/readme",
            headers={
                "Accept": "application/vnd.github.raw+json",
                "User-Agent": "InsightPro",
            },
            timeout=15,
        )
        response.raise_for_status()
        return response.text[:6000]
    except Exception as e:
        logger.debug("README fetch failed for %s: %s", repo_name, e)
        return fallback
