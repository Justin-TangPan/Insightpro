"""Opt-in PostgreSQL coverage for the V2 intelligence data path."""
from __future__ import annotations

import asyncio
import hashlib
import os
import re
from uuid import uuid4
from urllib.parse import urlparse

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("INSIGHT_POSTGRES_TEST_URL"),
    reason="set INSIGHT_POSTGRES_TEST_URL to an isolated migrated PostgreSQL database",
)


def test_source_to_event_data_path(monkeypatch):
    from db import get_db
    from routers import intelligence_v2
    from services import discovery_service, entity_service, event_service, source_registry_service

    test_url = os.environ["INSIGHT_POSTGRES_TEST_URL"]
    parsed_url = urlparse(test_url)
    database_name = parsed_url.path.lstrip("/").lower()
    if parsed_url.hostname not in {"localhost", "127.0.0.1", "::1"} or not any(
        label in database_name for label in ("test", "integration")
    ):
        pytest.fail("INSIGHT_POSTGRES_TEST_URL must target a loopback PostgreSQL database named for testing")
    monkeypatch.setenv("DIRECT_URL", test_url)
    suffix = uuid4().hex[:12]
    actor = "00000000-0000-0000-0000-000000000001"
    title = f"V2 Integration Agent {suffix}"
    repo = f"insight-pro/v2-integration-{suffix}"
    entity_key = f"github:{repo}"
    source_keys = [f"test_github_{suffix}", f"test_community_{suffix}"]
    normalized = re.sub(r"[\W_]+", "", title.casefold())
    candidate_key = hashlib.sha256(normalized.encode()).hexdigest()
    event_key = f"discovery:{candidate_key}"

    try:
        for source_key, adapter, url in (
            (source_keys[0], "github_search_api", "https://api.github.com/search/repositories"),
            (source_keys[1], "hacker_news_api", "https://hacker-news.firebaseio.com/v0/topstories.json"),
        ):
            source_registry_service.create_source({
                "source_key": source_key, "name": source_key, "adapter": adapter, "base_url": url,
                "business_scopes": ["technology_ecosystem"], "authority": "P1", "priority": 10,
                "cron": "45 9 * * *",
            }, actor)
            source_registry_service.set_source_enabled(source_key, True, actor)

        for index, source_key in enumerate(source_keys):
            discovery_service._store_discovery_raw(source_key, [{
                "external_id": f"{repo}:{suffix}:{index}", "url": f"https://github.com/{repo}",
                "title": title, "content": {"kind": "repository", "full_name": repo,
                    "stars": 3000 + index, "forks": 200},
            }])

        monkeypatch.setattr(discovery_service, "_collect_discovery_feeds", lambda: {})
        assert discovery_service.discover_candidates()["discovered"] == 1
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id,source_count FROM intelligence_candidates WHERE candidate_key=%s", (candidate_key,))
            candidate = cursor.fetchone()
        assert candidate["source_count"] == 2

        approved = discovery_service.approve_candidate(candidate["id"], ["technology_ecosystem"], actor)
        event = event_service.get_event(approved["event_id"])
        entity = entity_service.get_entity_detail(entity_key)
        assert len(event["evidence"]) == 2
        assert event["scores"]["hot_score"]["version"] == "signal_hot_v1"
        assert entity["entity"]["entity_type"] == "repository"
        assert len(entity["metrics"]) == 4
        coverage = asyncio.run(intelligence_v2.coverage(None))["benchmark_coverage"]
        by_source = {item["source_key"]: item for item in coverage["by_source"]}
        assert all(by_source[key]["observed"] == by_source[key]["represented"] == 1 for key in source_keys)
    finally:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM intelligence_candidates WHERE candidate_key=%s", (candidate_key,))
            cursor.execute("DELETE FROM intelligence_events WHERE event_key=%s", (event_key,))
            cursor.execute("DELETE FROM intelligence_metric_snapshots WHERE entity_key=%s", (entity_key,))
            cursor.execute("DELETE FROM intelligence_raw_items WHERE source_key=ANY(%s)", (source_keys,))
            cursor.execute("DELETE FROM intelligence_source_objects WHERE source_key=ANY(%s)", (source_keys,))
            cursor.execute("DELETE FROM intelligence_entities WHERE entity_key=%s", (entity_key,))
            cursor.execute("DELETE FROM intelligence_audit WHERE object_key=ANY(%s)", (source_keys,))
            cursor.execute("DELETE FROM intelligence_sources WHERE source_key=ANY(%s)", (source_keys,))


def test_rss_source_reaches_candidate_event_and_coverage(monkeypatch):
    from db import get_db
    from routers import intelligence_v2
    from services import discovery_service, event_service, source_registry_service

    test_url = os.environ["INSIGHT_POSTGRES_TEST_URL"]
    parsed_url = urlparse(test_url)
    database_name = parsed_url.path.lstrip("/").lower()
    if parsed_url.hostname not in {"localhost", "127.0.0.1", "::1"} or not any(
        label in database_name for label in ("test", "integration")
    ):
        pytest.fail("INSIGHT_POSTGRES_TEST_URL must target a loopback PostgreSQL database named for testing")
    monkeypatch.setenv("DIRECT_URL", test_url)
    suffix = uuid4().hex[:12]
    actor = "00000000-0000-0000-0000-000000000001"
    title = f"V2 RSS Discovery Signal {suffix}"
    source_keys = [f"test_rss_{suffix}_a", f"test_rss_{suffix}_b"]
    candidate_key = hashlib.sha256(re.sub(r"[\W_]+", "", title.casefold()).encode()).hexdigest()
    event_key = f"discovery:{candidate_key}"
    payload = f'''<rss version="2.0"><channel><item><guid>{suffix}</guid><title>{title}</title><link>https://example.test/signals/{suffix}</link><description>Feed-backed evidence</description></item></channel></rss>'''.encode()

    class Response:
        content = payload
        status_code = 200
        def raise_for_status(self): pass

    try:
        for source_key in source_keys:
            source_registry_service.create_source({
                "source_key": source_key, "name": source_key, "adapter": "rss_feed",
                "base_url": f"https://feed.example.test/{source_key}.xml",
                "business_scopes": ["technology_ecosystem"], "authority": "P1", "priority": 10,
                "cron": "45 9 * * *",
            }, actor)
            source_registry_service.set_source_enabled(source_key, True, actor)

        monkeypatch.setattr(discovery_service, "requests", type("Requests", (), {"get": staticmethod(lambda *_args, **_kwargs: Response())}))
        monkeypatch.setattr(source_registry_service, "list_sources", lambda: [
            {"source_key": key, "enabled": True, "adapter": "rss_feed",
             "base_url": f"https://feed.example.test/{key}.xml",
             "schedule": {"task_key": "discovery_sentinel_daily"}}
            for key in source_keys
        ])
        result = discovery_service.discover_candidates()
        assert result["discovered"] == 1
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id,source_count FROM intelligence_candidates WHERE candidate_key=%s", (candidate_key,))
            candidate = cursor.fetchone()
        assert candidate["source_count"] == 2

        approved = discovery_service.approve_candidate(candidate["id"], ["technology_ecosystem"], actor)
        assert len(event_service.get_event(approved["event_id"])["evidence"]) == 2
        coverage = asyncio.run(intelligence_v2.coverage(None))["benchmark_coverage"]
        by_source = {item["source_key"]: item for item in coverage["by_source"]}
        assert all(by_source[key]["observed"] == by_source[key]["represented"] == 1 for key in source_keys)
    finally:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM intelligence_candidates WHERE candidate_key=%s", (candidate_key,))
            cursor.execute("DELETE FROM intelligence_events WHERE event_key=%s", (event_key,))
            cursor.execute("DELETE FROM intelligence_metric_snapshots WHERE entity_key LIKE %s", (f"url:%{suffix}",))
            cursor.execute("DELETE FROM intelligence_raw_items WHERE source_key=ANY(%s)", (source_keys,))
            cursor.execute("DELETE FROM intelligence_source_objects WHERE source_key=ANY(%s)", (source_keys,))
            cursor.execute("DELETE FROM intelligence_entities WHERE canonical_url=%s", (f"https://example.test/signals/{suffix}",))
            cursor.execute("DELETE FROM intelligence_audit WHERE object_key=ANY(%s)", (source_keys,))
            cursor.execute("DELETE FROM intelligence_sources WHERE source_key=ANY(%s)", (source_keys,))


def test_repository_evaluation_is_saved_on_the_event(monkeypatch):
    from db import get_db
    from services import evaluation_service, intelligence_data_service, prompt_service
    from settings import settings
    from datetime import datetime
    from zoneinfo import ZoneInfo

    test_url = os.environ["INSIGHT_POSTGRES_TEST_URL"]
    parsed_url = urlparse(test_url)
    database_name = parsed_url.path.lstrip("/").lower()
    if parsed_url.hostname not in {"localhost", "127.0.0.1", "::1"} or not any(
        label in database_name for label in ("test", "integration")
    ):
        pytest.fail("INSIGHT_POSTGRES_TEST_URL must target a loopback PostgreSQL database named for testing")
    monkeypatch.setenv("DIRECT_URL", test_url)
    monkeypatch.setattr(settings, "CHAT_API_KEY", "")
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    scrape_date, scrape_time = now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")
    suffix = uuid4().hex[:12]
    repo_name = f"insight-pro/v2-eval-{suffix}"
    entity_key = f"github:{repo_name}"
    item = {"repo_name": repo_name, "repo_url": f"https://github.com/{repo_name}",
            "description": "Self-hosted enterprise workflow platform", "language": "Python",
            "stars": "320", "forks": "25", "today_stars": "90", "category": "daily"}
    try:
        prompt = prompt_service.published_prompt("repository_business_eval")
        assert prompt and prompt["version"] >= 2
        assert "technical_assessment" in prompt["system_prompt"]
        with get_db() as conn:
            intelligence_data_service.store_github_signal(conn.cursor(), item, scrape_date, scrape_time, 1)
        result = evaluation_service.evaluate_trending_business(1)
        assert result["source"] == "event_store" and result["count"] == 1
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT analysis FROM intelligence_analysis WHERE kind='repository_business_eval' AND source_key=%s", (entity_key,))
            analysis = cursor.fetchone()
            cursor.execute("SELECT scores->'business_evaluation' AS evaluation FROM intelligence_events WHERE entity_key=%s AND status='active'", (entity_key,))
            event = cursor.fetchone()
        assert analysis and event and event["evaluation"]["analysis_id"]
        assert evaluation_service.list_repository_business_evaluations()["items"][0]["repo_name"] == repo_name
    finally:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM trending_business_eval WHERE repo_name=%s", (repo_name,))
            cursor.execute("DELETE FROM intelligence_analysis WHERE kind='repository_business_eval' AND source_key=%s", (entity_key,))
            cursor.execute("DELETE FROM intelligence_events WHERE entity_key=%s", (entity_key,))
            cursor.execute("DELETE FROM intelligence_metric_snapshots WHERE entity_key=%s", (entity_key,))
            cursor.execute("DELETE FROM intelligence_raw_items WHERE canonical_url=%s", (item["repo_url"],))
            cursor.execute("DELETE FROM intelligence_source_objects WHERE canonical_url=%s", (item["repo_url"],))
            cursor.execute("DELETE FROM intelligence_entities WHERE entity_key=%s", (entity_key,))


def test_repository_metadata_and_release_event_are_queryable(monkeypatch):
    from db import get_db
    from crawlers.github_crawler import _store_repository_metadata
    from services.intelligence_data_service import store_github_signal
    from services.repository_service import list_trending_repositories
    from datetime import datetime
    from zoneinfo import ZoneInfo

    test_url = os.environ["INSIGHT_POSTGRES_TEST_URL"]
    parsed_url = urlparse(test_url)
    database_name = parsed_url.path.lstrip("/").lower()
    if parsed_url.hostname not in {"localhost", "127.0.0.1", "::1"} or not any(
        label in database_name for label in ("test", "integration")
    ):
        pytest.fail("INSIGHT_POSTGRES_TEST_URL must target a loopback PostgreSQL database named for testing")
    monkeypatch.setenv("DIRECT_URL", test_url)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    scrape_date, scrape_time = now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")
    suffix = uuid4().hex[:12]
    repo_name = f"insight-pro/v2-metadata-{suffix}"
    entity_key = f"github:{repo_name}"
    repo_url = f"https://github.com/{repo_name}"
    item = {"repo_name": repo_name, "repo_url": repo_url, "description": "Repository metadata check",
            "language": "Python", "stars": "100", "forks": "10", "today_stars": "20", "category": "daily"}
    metadata = {"kind": "repository_metadata", "pushed_at": now.isoformat(), "topics": ["agent"],
                "license": "MIT", "contributors_count": 17,
                "latest_release": {"tag_name": "v1.2.0", "name": "Release", "published_at": now.isoformat(), "body": "Verified release"}}
    try:
        with get_db() as conn:
            store_github_signal(conn.cursor(), item, scrape_date, scrape_time, 1)
        with get_db() as conn:
            _store_repository_metadata(conn.cursor(), item, metadata, scrape_date, scrape_time)
        result = list_trending_repositories("daily")
        row = next(item for item in result["items"] if item["entity_key"] == entity_key)
        assert row["contributors_count"] == 17 and row["license"] == "MIT"
        assert row["latest_release"]["tag_name"] == "v1.2.0"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT event_type FROM intelligence_events WHERE entity_key=%s AND status='active'", (entity_key,))
            assert "repository_release" in {record["event_type"] for record in cursor.fetchall()}
            cursor.execute("SELECT metric_value FROM intelligence_metric_snapshots WHERE entity_key=%s AND metric_key='contributors'", (entity_key,))
            assert cursor.fetchone()["metric_value"] == 17
    finally:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM intelligence_events WHERE entity_key=%s", (entity_key,))
            cursor.execute("DELETE FROM intelligence_metric_snapshots WHERE entity_key=%s", (entity_key,))
            cursor.execute("DELETE FROM intelligence_raw_items WHERE canonical_url=%s", (repo_url,))
            cursor.execute("DELETE FROM intelligence_source_objects WHERE canonical_url=%s", (repo_url,))
            cursor.execute("DELETE FROM intelligence_entities WHERE entity_key=%s", (entity_key,))
