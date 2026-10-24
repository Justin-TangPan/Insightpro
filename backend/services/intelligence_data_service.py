"""Small write path from existing collectors into the additive V2 data model."""
from __future__ import annotations

import hashlib
import json
import re

from db import get_db
from services.scoring_service import persist_github_hot_score
from services.data_semantics import time_fields, published_date, explicit_timestamp, map_taxonomy


def parse_metric(value: str | int | float | None) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if not value:
        return None
    match = re.search(r"[\d,.]+\s*[kKmM]?", str(value))
    if not match:
        return None
    token = match.group().replace(",", "").replace(" ", "")
    multiplier = 1_000_000 if token[-1:].lower() == "m" else 1_000 if token[-1:].lower() == "k" else 1
    return float(token[:-1] if multiplier != 1 else token) * multiplier


def store_github_signal(cursor, item: dict, scrape_date: str, scrape_time: str, rank: int) -> None:
    repo = item["repo_name"].strip().lower()
    entity_key = f"github:{repo}"
    observed_at = f"{scrape_date} {scrape_time}"
    content = {**item, "rank": rank}
    content_hash = hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    cursor.execute("""
        INSERT INTO intelligence_raw_items (source_key, external_id, canonical_url, title, content, content_hash, observed_at)
        VALUES ('github_trending', %s, %s, %s, %s::jsonb, %s, %s::timestamp AT TIME ZONE 'Asia/Shanghai')
        ON CONFLICT (source_key, external_id) DO NOTHING
        RETURNING id
    """, (f"{scrape_date}:{scrape_time}:{item['category']}:{repo}", item["repo_url"], item["repo_name"],
          json.dumps(content, ensure_ascii=False), content_hash, observed_at))
    inserted = cursor.fetchone()
    if inserted:
        raw_item_id = inserted["id"]
    else:
        cursor.execute("SELECT id FROM intelligence_raw_items WHERE source_key='github_trending' AND external_id=%s",
                       (f"{scrape_date}:{scrape_time}:{item['category']}:{repo}",))
        raw_item_id = cursor.fetchone()["id"]

    cursor.execute("""
        INSERT INTO intelligence_entities (entity_key, entity_type, canonical_name, canonical_url, metadata)
        VALUES (%s, 'repository', %s, %s, %s::jsonb)
        ON CONFLICT (entity_key) DO UPDATE SET canonical_name=EXCLUDED.canonical_name,
          canonical_url=EXCLUDED.canonical_url, metadata=EXCLUDED.metadata, updated_at=NOW()
    """, (entity_key, item["repo_name"], item["repo_url"], json.dumps({"language": item.get("language")}, ensure_ascii=False)))
    cursor.execute("""SELECT event.id FROM intelligence_event_evidence evidence
        JOIN intelligence_events event ON event.id=evidence.event_id AND event.status='active'
        WHERE evidence.raw_item_id=%s ORDER BY event.id LIMIT 1""", (raw_item_id,))
    linked = cursor.fetchone()
    if linked:
        event_id = linked["id"]
    else:
        cursor.execute("""
            INSERT INTO intelligence_events (event_key, entity_key, event_type, business_scopes, title, first_seen_at, last_seen_at)
            VALUES (%s, %s, 'github_trending', ARRAY['technology_ecosystem'], %s,
                    %s::timestamp AT TIME ZONE 'Asia/Shanghai',
                    %s::timestamp AT TIME ZONE 'Asia/Shanghai')
            ON CONFLICT (event_key) DO UPDATE SET title=EXCLUDED.title,
              first_seen_at=LEAST(intelligence_events.first_seen_at, EXCLUDED.first_seen_at),
              last_seen_at=GREATEST(intelligence_events.last_seen_at, EXCLUDED.last_seen_at), updated_at=NOW()
            RETURNING id, merged_into_id
        """, (f"github-trending:{repo}", entity_key, item["repo_name"], observed_at, observed_at))
        event = cursor.fetchone()
        event_id = event["merged_into_id"] or event["id"]
        if event["merged_into_id"]:
            cursor.execute("""UPDATE intelligence_events SET
                first_seen_at=LEAST(first_seen_at, %s::timestamp AT TIME ZONE 'Asia/Shanghai'),
                last_seen_at=GREATEST(last_seen_at, %s::timestamp AT TIME ZONE 'Asia/Shanghai'), updated_at=NOW()
                WHERE id=%s""", (observed_at, observed_at, event_id))
        cursor.execute("""
            INSERT INTO intelligence_event_evidence (event_id, raw_item_id)
            VALUES (%s, %s) ON CONFLICT DO NOTHING
        """, (event_id, raw_item_id))

    metrics = {
        "stars": parse_metric(item.get("stars")),
        "forks": parse_metric(item.get("forks")),
        f"trending_growth_{item['category']}": parse_metric(item.get("today_stars")),
        f"rank_{item['category']}": float(rank),
    }
    for metric_key, metric_value in metrics.items():
        if metric_value is None:
            continue
        cursor.execute("""
            INSERT INTO intelligence_metric_snapshots
              (entity_key, source_key, raw_item_id, metric_key, metric_value, observed_at)
            VALUES (%s, 'github_trending', %s, %s, %s, %s::timestamp AT TIME ZONE 'Asia/Shanghai')
            ON CONFLICT (entity_key, source_key, metric_key, observed_at)
            DO UPDATE SET raw_item_id=EXCLUDED.raw_item_id, metric_value=EXCLUDED.metric_value
        """, (entity_key, raw_item_id, metric_key, metric_value, observed_at))
    if not linked and item["category"] == "daily" and metrics["stars"] is not None:
        persist_github_hot_score(cursor, entity_key, event_id)


def store_community_raw(items: list[dict], taxonomy_aliases: dict[str, str] | None = None) -> int:
    source_keys = {"知乎": "community_zhihu", "百度热搜": "community_baidu",
                   "腾讯云社区": "community_tencent", "CSDN": "community_csdn"}
    with get_db() as conn:
        cursor = conn.cursor()
        for item in items:
            source_key = source_keys[item["source"]]
            times = time_fields(published_at=explicit_timestamp(item.get("published_at")), observed_at=item["observed_at"])
            content = {key: item.get(key) for key in ("title", "summary", "url", "topic_category", "relevance")}
            content["topic_category"] = map_taxonomy(content["topic_category"] or "", taxonomy_aliases)
            digest = hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            cursor.execute("""
                INSERT INTO intelligence_raw_items
                  (source_key, external_id, canonical_url, title, content, observed_at, content_hash, published_at)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s::timestamptz, %s, %s::timestamptz)
                ON CONFLICT (source_key, external_id) DO NOTHING
                RETURNING id
            """, (source_key, digest, item["url"], item["title"],
                  json.dumps(content, ensure_ascii=False), times["observed_at"], digest, times["published_at"]))
            raw = cursor.fetchone()
            if not raw:
                cursor.execute("SELECT id FROM intelligence_raw_items WHERE source_key=%s AND external_id=%s",
                               (source_key, digest))
                raw = cursor.fetchone()
            raw_id = raw["id"]
            normalized_title = " ".join(item["title"].casefold().split())
            entity_key = f"community-topic:{hashlib.sha256(normalized_title.encode()).hexdigest()}"
            cursor.execute("""INSERT INTO intelligence_entities (entity_key,entity_type,canonical_name,canonical_url)
                VALUES (%s,'topic',%s,%s) ON CONFLICT (entity_key) DO UPDATE SET updated_at=NOW()""",
                (entity_key, item["title"], item["url"]))
            cursor.execute("""INSERT INTO intelligence_events
                (event_key,entity_key,event_type,business_scopes,title,summary,first_seen_at,last_seen_at)
                VALUES (%s,%s,'community_topic',ARRAY['community_insights'],%s,%s,%s::timestamptz,%s::timestamptz)
                ON CONFLICT (event_key) DO UPDATE SET
                  summary=COALESCE(NULLIF(EXCLUDED.summary,''),intelligence_events.summary),
                  first_seen_at=LEAST(intelligence_events.first_seen_at,EXCLUDED.first_seen_at),
                  last_seen_at=GREATEST(intelligence_events.last_seen_at,EXCLUDED.last_seen_at),updated_at=NOW()
                RETURNING id""",
                (entity_key, entity_key, item["title"], item.get("summary") or "", item["observed_at"], item["observed_at"]))
            event_id = cursor.fetchone()["id"]
            cursor.execute("""INSERT INTO intelligence_event_evidence (event_id,raw_item_id)
                VALUES (%s,%s) ON CONFLICT DO NOTHING""", (event_id, raw_id))
    return len(items)


def store_catalog_change(cursor, source_key: str, row: dict) -> None:
    content = {key: row.get(key) for key in ("vendor", "category", "source_description", "summary", "change_summary", "content_snapshot", "is_active", "is_baseline", "removed_at")}
    digest = hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    entity_key = f"solution:{hashlib.sha256(row['url'].encode()).hexdigest()}"
    external_id = f"{row['url']}:{digest}"
    cursor.execute("""INSERT INTO intelligence_raw_items
        (source_key, external_id, canonical_url, title, content, content_hash)
        VALUES (%s,%s,%s,%s,%s::jsonb,%s) ON CONFLICT (source_key, external_id) DO NOTHING
        RETURNING id""", (source_key, external_id, row["url"], row["title"], json.dumps(content, ensure_ascii=False, default=str), digest))
    raw = cursor.fetchone()
    if raw:
        raw_id = raw["id"]
    else:
        cursor.execute("SELECT id FROM intelligence_raw_items WHERE source_key=%s AND external_id=%s", (source_key, external_id))
        raw_id = cursor.fetchone()["id"]
    cursor.execute("""INSERT INTO intelligence_entities (entity_key, entity_type, canonical_name, canonical_url)
        VALUES (%s,'solution',%s,%s) ON CONFLICT (entity_key) DO UPDATE SET canonical_name=EXCLUDED.canonical_name,
        updated_at=NOW()""", (entity_key, row["title"], row["url"]))
    event_key = f"solution-catalog:{entity_key}" if row.get("is_baseline") else f"solution-change:{entity_key}:{digest}"
    title = (f"{row['vendor']}方案下线：{row['title']}" if row.get("removed_at") else
             f"{row['vendor']}方案收录：{row['title']}" if row.get("is_baseline") else
             f"{row['vendor']}方案更新：{row['title']}")
    cursor.execute("""INSERT INTO intelligence_events
        (event_key, entity_key, event_type, business_scopes, title, summary)
        VALUES (%s,%s,%s,ARRAY['solutions'],%s,%s)
        ON CONFLICT (event_key) DO UPDATE SET title=EXCLUDED.title,
        summary=COALESCE(NULLIF(EXCLUDED.summary,''),intelligence_events.summary),updated_at=NOW() RETURNING id""",
        (event_key, entity_key, "solution_catalog_entry" if row.get("is_baseline") else "solution_catalog_change",
         title, row.get("change_summary") or row.get("source_description") or row.get("summary")))
    event_id = cursor.fetchone()["id"]
    cursor.execute("INSERT INTO intelligence_event_evidence (event_id,raw_item_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (event_id, raw_id))


def store_ai_application(cursor, item: dict) -> None:
    content = {key: item.get(key) for key in ("vendor", "kind", "published", "source_text", "source_verified")}
    digest = hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    entity_key = f"ai-application:{hashlib.sha256(item['url'].encode()).hexdigest()}"
    external_id = f"{item['url']}:{digest}"
    published = published_date(item.get("published"))
    cursor.execute("""INSERT INTO intelligence_raw_items
        (source_key, external_id, canonical_url, title, content, published_at, content_hash)
        VALUES ('ai_app_official',%s,%s,%s,%s::jsonb,%s::date,%s)
        ON CONFLICT (source_key, external_id) DO NOTHING RETURNING id""",
        (external_id, item["url"], item["title"], json.dumps(content, ensure_ascii=False), published, digest))
    raw = cursor.fetchone()
    if raw:
        raw_id = raw["id"]
    else:
        cursor.execute("SELECT id FROM intelligence_raw_items WHERE source_key='ai_app_official' AND external_id=%s", (external_id,))
        raw_id = cursor.fetchone()["id"]
    cursor.execute("""INSERT INTO intelligence_entities (entity_key,entity_type,canonical_name,canonical_url,metadata)
        VALUES (%s,'ai_application',%s,%s,%s::jsonb) ON CONFLICT (entity_key) DO UPDATE SET
        canonical_name=EXCLUDED.canonical_name,updated_at=NOW()""",
        (entity_key, item["title"], item["url"], json.dumps({"vendor": item["vendor"]})))
    cursor.execute("""INSERT INTO intelligence_events
        (event_key,entity_key,event_type,business_scopes,title,published_at,summary)
        VALUES (%s,%s,'official_ai_application',ARRAY['ai_applications'],%s,%s::date,%s)
        ON CONFLICT (event_key) DO UPDATE SET updated_at=NOW() RETURNING id""",
        (f"ai-app:{hashlib.sha256(item['url'].encode()).hexdigest()}", entity_key, item["title"],
         published, (item.get("source_text") or "")[:2000]))
    cursor.execute("INSERT INTO intelligence_event_evidence (event_id,raw_item_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                   (cursor.fetchone()["id"], raw_id))


def store_competitor_news(cursor, item: dict) -> None:
    url = (item.get("url") or item.get("link") or "").strip()
    title = (item.get("title") or "").strip()
    if not url or not title:
        return
    content = {key: item.get(key) for key in ("vendor", "category", "summary", "published_date")}
    digest = hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    entity_key = f"competitor:{hashlib.sha256(url.encode()).hexdigest()}"
    external_id = f"{url}:{digest}"
    cursor.execute("""INSERT INTO intelligence_raw_items
        (source_key,external_id,canonical_url,title,content,content_hash,published_at)
        VALUES ('competitor_news',%s,%s,%s,%s::jsonb,%s,%s::timestamptz)
        ON CONFLICT (source_key,external_id) DO NOTHING RETURNING id""",
        (external_id, url, title, json.dumps(content, ensure_ascii=False, default=str), digest,
         item.get("published_date")))
    raw = cursor.fetchone()
    if raw:
        raw_id = raw["id"]
    else:
        cursor.execute("SELECT id FROM intelligence_raw_items WHERE source_key='competitor_news' AND external_id=%s", (external_id,))
        raw_id = cursor.fetchone()["id"]
    cursor.execute("""INSERT INTO intelligence_entities
        (entity_key,entity_type,canonical_name,canonical_url,metadata)
        VALUES (%s,'competitor_update',%s,%s,%s::jsonb)
        ON CONFLICT (entity_key) DO UPDATE SET canonical_name=EXCLUDED.canonical_name,
          metadata=EXCLUDED.metadata,updated_at=NOW()""",
        (entity_key, title, url, json.dumps({"vendor": item.get("vendor")}, ensure_ascii=False)))
    event_key = f"competitor-news:{hashlib.sha256((url + ':' + digest).encode()).hexdigest()}"
    cursor.execute("""INSERT INTO intelligence_events
        (event_key,entity_key,event_type,business_scopes,title,summary,published_at,event_at)
        VALUES (%s,%s,'competitor_update',ARRAY['competitor_dynamics'],%s,%s,%s::timestamptz,%s::timestamptz)
        ON CONFLICT (event_key) DO UPDATE SET summary=EXCLUDED.summary,updated_at=NOW() RETURNING id""",
        (event_key, entity_key, title, item.get("summary"), item.get("published_date"), item.get("published_date")))
    event_id = cursor.fetchone()["id"]
    cursor.execute("INSERT INTO intelligence_event_evidence (event_id,raw_item_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                   (event_id, raw_id))
