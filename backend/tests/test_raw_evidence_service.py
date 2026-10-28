"""Opt-in database checks for immutable Raw versions; always roll back."""
import os
from ipaddress import ip_address
from urllib.parse import urlparse
from uuid import uuid4

import psycopg2
import pytest
from psycopg2.extras import RealDictCursor

from services.raw_evidence_service import store_raw_version


@pytest.mark.skipif(not os.getenv("INSIGHT_POSTGRES_TEST_URL"), reason="isolated PostgreSQL URL required")
def test_source_object_versions_keep_prior_event_evidence():
    url = os.environ["INSIGHT_POSTGRES_TEST_URL"]
    parsed = urlparse(url)
    host = parsed.hostname or ""
    assert "test" in parsed.path.lower() and (host == "localhost" or ip_address(host).is_private)
    conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
    suffix = uuid4().hex[:12]
    try:
        cursor = conn.cursor()
        sources = (f"w1_{suffix}_a", f"w1_{suffix}_b")
        for source in sources:
            cursor.execute("INSERT INTO intelligence_sources(source_key,name,adapter) VALUES (%s,%s,'test')", (source, source))
        source_url = f"https://example.test/{suffix}"
        first = store_raw_version(cursor, source_key=sources[0], url=source_url, title="Test",
                                  content={"text": "one"}, content_hash="one")
        entity_key = f"w1:{suffix}"
        cursor.execute("INSERT INTO intelligence_entities(entity_key,entity_type,canonical_name) VALUES (%s,'test','Test')", (entity_key,))
        cursor.execute("""INSERT INTO intelligence_events(event_key,entity_key,event_type,title,status)
            VALUES (%s,%s,'historical_update','Test','active') RETURNING id""", (f"w1:event:{suffix}", entity_key))
        historical_event = cursor.fetchone()["id"]
        cursor.execute("INSERT INTO intelligence_event_evidence(event_id,raw_item_id) VALUES (%s,%s)",
                       (historical_event, first["id"]))
        cursor.execute("""UPDATE intelligence_events SET analysis_status='fresh',analysis_version=content_version
            WHERE id=%s""", (historical_event,))
        same = store_raw_version(cursor, source_key=sources[0], url=source_url, title="Test",
                                 content={"text": "one"}, content_hash="one")
        second = store_raw_version(cursor, source_key=sources[0], url=source_url, title="Test",
                                   content={"text": "two"}, content_hash="two")
        other = store_raw_version(cursor, source_key=sources[1], url=source_url, title="Test",
                                  content={"text": "one"}, content_hash="one")
        native_first = store_raw_version(cursor, source_key=sources[1], url=f"https://example.test/native/{suffix}",
                                         external_native_id=f"official-{suffix}", title="Native",
                                         content={"text": "one"}, content_hash="native-one")
        native_second = store_raw_version(cursor, source_key=sources[1], url=f"https://example.test/renamed/{suffix}",
                                          external_native_id=f"official-{suffix}", title="Native",
                                          content={"text": "two"}, content_hash="native-two")
        assert (first["change"], same["change"], second["change"], other["change"]) == (
            "new", "no_change", "changed", "new")
        assert same["id"] == first["id"] and second["id"] != first["id"]
        cursor.execute("SELECT source_object_id FROM intelligence_raw_items WHERE id=ANY(%s) ORDER BY id",
                       ([native_first["id"], native_second["id"]],))
        assert len({row["source_object_id"] for row in cursor.fetchall()}) == 1
        cursor.execute("SELECT analysis_status FROM intelligence_events WHERE id=%s", (historical_event,))
        assert cursor.fetchone()["analysis_status"] == "fresh"
        cursor.execute("SELECT raw_item_id FROM intelligence_event_evidence WHERE event_id=%s", (historical_event,))
        assert cursor.fetchone()["raw_item_id"] == first["id"]
        cursor.execute("""INSERT INTO intelligence_events(event_key,entity_key,event_type,title,status)
            VALUES (%s,%s,'historical_update','Test','pending_review') RETURNING id""",
            (f"w1:pending:{suffix}", entity_key))
        pending_event = cursor.fetchone()["id"]
        cursor.execute("INSERT INTO intelligence_event_evidence(event_id,raw_item_id) VALUES (%s,%s)",
                       (pending_event, first["id"]))
        cursor.execute("UPDATE intelligence_events SET analysis_status='fresh',analysis_version=content_version WHERE id=%s",
                       (pending_event,))
        cursor.execute("INSERT INTO intelligence_event_evidence(event_id,raw_item_id) VALUES (%s,%s)",
                       (pending_event, second["id"]))
        cursor.execute("SELECT analysis_status FROM intelligence_events WHERE id=%s", (pending_event,))
        assert cursor.fetchone()["analysis_status"] == "stale"
        assert (first["content_version"], second["content_version"]) == (1, 2)
        cursor.execute("""SELECT id,source_key,current_raw_id,current_version FROM intelligence_source_objects
            WHERE source_key=ANY(%s) ORDER BY source_key""", (list(sources),))
        objects = cursor.fetchall()
        assert len(objects) == 3 and objects[0]["current_raw_id"] == second["id"]
        assert objects[0]["current_version"] == 2 and objects[1]["current_version"] == 1
        cursor.execute("SELECT id FROM intelligence_raw_items WHERE source_object_id=%s ORDER BY source_version", (objects[0]["id"],))
        assert [row["id"] for row in cursor.fetchall()] == [first["id"], second["id"]]
        with pytest.raises(ValueError, match="stable source URL"):
            store_raw_version(cursor, source_key=sources[0], url="", title="Unknown", content={}, content_hash="x")
        cursor.execute("SAVEPOINT immutable_check")
        with pytest.raises(psycopg2.Error, match="Raw evidence is immutable"):
            cursor.execute("UPDATE intelligence_raw_items SET title='Modified' WHERE id=%s", (first["id"],))
        cursor.execute("ROLLBACK TO SAVEPOINT immutable_check")
    finally:
        conn.rollback()
        conn.close()
