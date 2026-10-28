from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("INSIGHT_POSTGRES_TEST_URL"),
    reason="set INSIGHT_POSTGRES_TEST_URL to an isolated migrated PostgreSQL database",
)


def test_labeled_recall_benchmark_distinguishes_missed_and_event_linked_signals(monkeypatch):
    from db import get_db
    from services.recall_benchmark_service import recall_report, record_reference
    from services.raw_evidence_service import store_raw_version

    test_url = os.environ["INSIGHT_POSTGRES_TEST_URL"]
    parsed = urlparse(test_url)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or not any(
        label in parsed.path.lower() for label in ("test", "integration")
    ):
        pytest.fail("INSIGHT_POSTGRES_TEST_URL must target a loopback PostgreSQL database named for testing")
    monkeypatch.setenv("DIRECT_URL", test_url)
    suffix = uuid4().hex[:12]
    actor = "00000000-0000-0000-0000-000000000001"
    captured_url = f"https://example.test/captured/{suffix}"
    missed_url = f"https://example.test/missed/{suffix}"
    reference_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    event_key = f"recall-benchmark:{suffix}"
    entity_key = f"recall-benchmark:{suffix}"
    benchmark_ids = []
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""INSERT INTO intelligence_entities(entity_key,entity_type,canonical_name,canonical_url)
                              VALUES (%s,'technology_signal',%s,%s)""", (entity_key, suffix, captured_url))
            raw_id = store_raw_version(cursor, source_key="github_trending", url=captured_url,
                                       title="captured signal", content={}, content_hash="benchmark",
                                       observed_at=reference_at + timedelta(minutes=1))["id"]
            cursor.execute("""INSERT INTO intelligence_events(event_key,entity_key,event_type,title)
                              VALUES (%s,%s,'benchmark_signal','Captured signal') RETURNING id""",
                           (event_key, entity_key))
            event_id = cursor.fetchone()["id"]
            cursor.execute("INSERT INTO intelligence_event_evidence(event_id,raw_item_id) VALUES (%s,%s)", (event_id, raw_id))

        for title, url in (("Captured signal", captured_url), ("Missed signal", missed_url)):
            saved = record_reference({"title": title, "canonical_url": url,
                                      "reference_source": f"independent-test-{suffix}",
                                      "reference_at": reference_at, "is_relevant": True,
                                      "label_reason": "Independent test label"}, actor)
            benchmark_ids.append(saved["id"])

        report = recall_report(days=1)

        assert report["relevant_count"] == 2
        assert report["found_count"] == 1
        assert report["missed_count"] == 1
        assert report["recall_rate"] == 50.0
        assert report["represented_count"] == 1
        assert report["event_rate"] == 50.0
    finally:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM intelligence_audit WHERE object_type='recall_benchmark' AND object_key=ANY(%s)",
                           ([str(item) for item in benchmark_ids],))
            cursor.execute("DELETE FROM intelligence_recall_benchmark WHERE canonical_url=ANY(%s)",
                           ([captured_url, missed_url],))
            cursor.execute("DELETE FROM intelligence_events WHERE event_key=%s", (event_key,))
            cursor.execute("DELETE FROM intelligence_raw_items WHERE id=%s", (raw_id,))
            cursor.execute("DELETE FROM intelligence_source_objects WHERE source_key='github_trending' AND identity_key=%s", (captured_url,))
            cursor.execute("DELETE FROM intelligence_entities WHERE entity_key=%s", (entity_key,))
