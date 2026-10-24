"""GitHub Trending scraper and persistence."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo
from db import get_db
from services.intelligence_data_service import store_github_signal
from services.source_registry_service import source_enabled, record_source_health

logger = logging.getLogger(__name__)
# shortcut: enrich only daily top 8, expand after authenticated API quota and latency are measured.
REPOSITORY_METADATA_LIMIT = 8
GITHUB_HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "InsightPro/2.0"}


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


def store_github_items(cursor, items: list[dict], scrape_date: str, scrape_time: str) -> None:
    for rank, item in enumerate(items, start=1):
        cursor.execute("""
            INSERT INTO github_trending
            (scrape_date, scrape_time, repo_name, repo_url, description, language, stars, forks, today_stars, category)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (scrape_date, category, repo_name) DO NOTHING
        """, (scrape_date, scrape_time, item["repo_name"], item["repo_url"],
              item["description"], item["language"], item["stars"], item["forks"],
              item["today_stars"], item["category"]))
        store_github_signal(cursor, item, scrape_date, scrape_time, rank)


def collect_repository_metadata(repo_name: str) -> dict:
    """Collect public GitHub evidence for a small, daily top-repository sample."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo_name):
        raise ValueError("Invalid GitHub repository name")
    api_url = f"https://api.github.com/repos/{quote(repo_name, safe='/')}"
    response = requests.get(api_url, headers=GITHUB_HEADERS, timeout=12)
    response.raise_for_status()
    repo = response.json()

    contributors_response = requests.get(f"{api_url}/contributors", params={"per_page": 1},
                                         headers=GITHUB_HEADERS, timeout=12)
    contributors_response.raise_for_status()
    contributors = contributors_response.json()
    last_page = re.search(r'[?&]page=(\d+)>; rel="last"', contributors_response.headers.get("Link", ""))
    contributor_count = int(last_page.group(1)) if last_page else len(contributors)

    release_response = requests.get(f"{api_url}/releases", params={"per_page": 2}, headers=GITHUB_HEADERS, timeout=12)
    release_response.raise_for_status()
    releases = release_response.json()
    release = None
    if releases:
        latest = releases[0]
        previous_tag = releases[1].get("tag_name") if len(releases) > 1 else None
        latest_version, previous_version = _major_version(latest.get("tag_name")), _major_version(previous_tag)
        release = {key: latest.get(key) for key in ("tag_name", "name", "html_url", "published_at", "body")}
        release["body"] = (release["body"] or "")[:3000]
        release["previous_tag_name"] = previous_tag
        release["major_release"] = bool(latest_version and previous_version and latest_version > previous_version)

    return {
        "kind": "repository_metadata", "pushed_at": repo.get("pushed_at"),
        "created_at": repo.get("created_at"), "topics": repo.get("topics") or [],
        "license": (repo.get("license") or {}).get("spdx_id"),
        "open_issues_count": repo.get("open_issues_count"), "contributors_count": contributor_count,
        "latest_release": release,
    }


def _major_version(tag: str | None) -> int | None:
    match = re.fullmatch(r"[vV]?(\d+)\.(\d+)(?:\.\d+)?(?:[-+].*)?", tag or "")
    return int(match.group(1)) if match else None


def _recent_repository_metadata(repo_url: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT content FROM intelligence_raw_items
            WHERE source_key='github_trending' AND canonical_url=%s AND content->>'kind'='repository_metadata'
              AND observed_at >= NOW() - INTERVAL '24 hours'
            ORDER BY observed_at DESC,id DESC LIMIT 1""", (repo_url,))
        row = cursor.fetchone()
    return row["content"] if row else None


def _store_repository_metadata(cursor, item: dict, metadata: dict, scrape_date: str, scrape_time: str) -> None:
    repo = item["repo_name"].strip().lower()
    entity_key = f"github:{repo}"
    observed_at = f"{scrape_date} {scrape_time}"
    content_hash = hashlib.sha256(json.dumps(metadata, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    cursor.execute("""INSERT INTO intelligence_raw_items
        (source_key,external_id,canonical_url,title,content,content_hash,observed_at,published_at)
        VALUES ('github_trending',%s,%s,%s,%s::jsonb,%s,%s::timestamp AT TIME ZONE 'Asia/Shanghai',%s::timestamptz)
        ON CONFLICT (source_key,external_id) DO UPDATE SET content=EXCLUDED.content,
          content_hash=EXCLUDED.content_hash,observed_at=EXCLUDED.observed_at,published_at=EXCLUDED.published_at
        RETURNING id""", (f"repository-metadata:{repo}:{scrape_date}", item["repo_url"], item["repo_name"],
              json.dumps(metadata, ensure_ascii=False), content_hash, observed_at,
              (metadata.get("latest_release") or {}).get("published_at")))
    raw_id = cursor.fetchone()["id"]
    cursor.execute("""SELECT id FROM intelligence_events WHERE entity_key=%s AND status='active'
        ORDER BY CASE WHEN event_type='github_trending' THEN 0 ELSE 1 END,id LIMIT 1""", (entity_key,))
    repository_event = cursor.fetchone()
    if repository_event:
        cursor.execute("""INSERT INTO intelligence_event_evidence(event_id,raw_item_id)
            VALUES (%s,%s) ON CONFLICT DO NOTHING""", (repository_event["id"], raw_id))
    if metadata.get("contributors_count") is not None:
        cursor.execute("""INSERT INTO intelligence_metric_snapshots
            (entity_key,source_key,raw_item_id,metric_key,metric_value,observed_at)
            VALUES (%s,'github_trending',%s,'contributors',%s,%s::timestamp AT TIME ZONE 'Asia/Shanghai')
            ON CONFLICT (entity_key,source_key,metric_key,observed_at)
            DO UPDATE SET raw_item_id=EXCLUDED.raw_item_id,metric_value=EXCLUDED.metric_value""",
            (entity_key, raw_id, metadata["contributors_count"], observed_at))

    release = metadata.get("latest_release")
    if release and release.get("published_at") and (release.get("tag_name") or release.get("name")):
        tag = release.get("tag_name") or release["name"]
        title = f"{item['repo_name']} · {release.get('name') or tag}"
        event_type = "repository_major_release" if release.get("major_release") else "repository_release"
        cursor.execute("""INSERT INTO intelligence_events
            (event_key,entity_key,event_type,business_scopes,title,summary,event_at,published_at,first_seen_at,last_seen_at)
            VALUES (%s,%s,%s,ARRAY['technology_ecosystem'],%s,%s,%s::timestamptz,
              %s::timestamptz,%s::timestamp AT TIME ZONE 'Asia/Shanghai',%s::timestamp AT TIME ZONE 'Asia/Shanghai')
            ON CONFLICT (event_key) DO UPDATE SET title=EXCLUDED.title,summary=EXCLUDED.summary,
              event_at=EXCLUDED.event_at,published_at=EXCLUDED.published_at,
              first_seen_at=LEAST(intelligence_events.first_seen_at,EXCLUDED.first_seen_at),
              last_seen_at=GREATEST(intelligence_events.last_seen_at,EXCLUDED.last_seen_at),updated_at=NOW()
            RETURNING id""", (f"github-release:{repo}:{tag}", entity_key, event_type, title, release.get("body") or "",
                 release["published_at"], release["published_at"], observed_at, observed_at))
        release_event = cursor.fetchone()
        cursor.execute("""INSERT INTO intelligence_event_evidence(event_id,raw_item_id)
            VALUES (%s,%s) ON CONFLICT DO NOTHING""", (release_event["id"], raw_id))


def _enrich_repositories(items: list[dict], scrape_date: str, scrape_time: str) -> list[str]:
    errors = []
    for item in items[:REPOSITORY_METADATA_LIMIT]:
        try:
            metadata = _recent_repository_metadata(item["repo_url"])
            if metadata is None:
                metadata = collect_repository_metadata(item["repo_name"])
                with get_db() as conn:
                    _store_repository_metadata(conn.cursor(), item, metadata, scrape_date, scrape_time)
        except Exception as error:
            message = f"repository metadata {item['repo_name']}: {error}"
            errors.append(message)
            logger.warning("%s", message)
    return errors


def refresh_and_store():
    if not source_enabled("github_trending"):
        return {"status": "skipped", "reason": "source_disabled"}
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    total = 0
    errors = []
    daily_items = []
    for period in ["daily", "weekly", "monthly"]:
        try:
            items = scrape_github_trending(since=period)
            with get_db() as conn:
                store_github_items(conn.cursor(), items, date_str, time_str)
            if period == "daily":
                daily_items = items
            total += len(items)
        except Exception as e:
            logger.warning("GitHub %s scrape failed: %s", period, e)
            errors.append(f"{period}: {e}")
    if daily_items:
        errors.extend(_enrich_repositories(daily_items, date_str, time_str))
    with get_db() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO scrape_log (scrape_date, scrape_time, status, items_count) VALUES (%s, %s, %s, %s)",
                  (date_str, time_str, "success" if total > 0 else "failed", total))
    logger.info("GitHub refresh done, %d items", total)
    status = "failed" if not total else "degraded" if errors else "healthy"
    record_source_health("github_trending", status, "; ".join(errors) if errors else None)
    if not total:
        raise RuntimeError("GitHub Trending produced no records")
    return {"status": "success" if not errors else "partial_success", "items_count": total, "errors": errors}


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
