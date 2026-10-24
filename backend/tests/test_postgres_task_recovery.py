from __future__ import annotations

import os
import zlib
from urllib.parse import urlparse
from uuid import uuid4

import psycopg2
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("INSIGHT_POSTGRES_TEST_URL"),
    reason="set INSIGHT_POSTGRES_TEST_URL to an isolated migrated PostgreSQL database",
)


def test_recovery_marks_only_task_runs_without_a_live_advisory_lock(monkeypatch):
    test_url = os.environ["INSIGHT_POSTGRES_TEST_URL"]
    parsed = urlparse(test_url)
    database_name = parsed.path.lstrip("/").lower()
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or not any(
        label in database_name for label in ("test", "integration")
    ):
        pytest.fail("INSIGHT_POSTGRES_TEST_URL must target a loopback PostgreSQL database named for testing")

    monkeypatch.setenv("DIRECT_URL", test_url)
    from db import get_db

    suffix = uuid4().hex[:12]
    orphan_key, active_key = f"test-orphan-{suffix}", f"test-active-{suffix}"
    lock_connection = psycopg2.connect(test_url.split("?", 1)[0])
    try:
        with lock_connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_lock(%s)", (zlib.crc32(active_key.encode()),))
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""CREATE TABLE IF NOT EXISTS platform_task_runs (
                    id bigserial PRIMARY KEY, task_key text NOT NULL, trigger text NOT NULL,
                    status text NOT NULL, started_at timestamptz NOT NULL,
                    finished_at timestamptz, error text)""")
                cursor.execute("""INSERT INTO platform_task_runs (task_key,trigger,status,started_at)
                    VALUES (%s,'test','running',NOW()),(%s,'test','running',NOW())""", (orphan_key, active_key))
        from services import task_service
        assert task_service.recover_orphaned_runs() == 1

        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT task_key,status,finished_at,error FROM platform_task_runs WHERE task_key=ANY(%s)", ([orphan_key, active_key],))
                states = {row["task_key"]: row for row in cursor.fetchall()}
        assert states[orphan_key]["status"] == "failed" and states[orphan_key]["finished_at"]
        assert states[orphan_key]["error"] == "Task process exited without recording completion"
        assert states[active_key]["status"] == "running"
        assert states[active_key]["finished_at"] is None and states[active_key]["error"] is None
    finally:
        with lock_connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", (zlib.crc32(active_key.encode()),))
        lock_connection.close()
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM platform_task_runs WHERE task_key=ANY(%s)", ([orphan_key, active_key],))
