from services import pipeline_service


def test_pipeline_holds_worker_lock_until_execution_finishes(monkeypatch):
    statements = []

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return self
        def execute(self, sql, params): statements.append((sql, params))

    monkeypatch.setattr(pipeline_service, "get_db", Connection)
    monkeypatch.setattr(pipeline_service, "_execute_pipeline", lambda *_: statements.append(("work", ())))
    pipeline_service.execute_pipeline(9, "solutions", [])
    assert [sql for sql, _ in statements] == [
        "SELECT pg_advisory_lock(%s)", "work", "SELECT pg_advisory_unlock(%s)"]


def test_pipeline_stops_after_failed_task_and_keeps_step_result(monkeypatch):
    saved = []
    calls = []
    monkeypatch.setattr(pipeline_service, "_save", lambda *args: saved.append(args))

    def run(key, trigger):
        calls.append(key)
        if key == "discovery_sentinel_daily":
            return {"status": "partial", "source_errors": {"rss": "timeout"}}
        return {"count": 3}

    monkeypatch.setattr(pipeline_service, "run_task", run)
    steps = pipeline_service.pipeline_steps("ai_applications")
    pipeline_service._execute_pipeline(7, "ai_applications", steps)
    assert calls == ["ai_applications_daily", "discovery_sentinel_daily"]
    assert steps[0]["result"] == {"count": 3}
    assert steps[1]["status"] == "failed"
    assert steps[2]["status"] == "pending"
    assert saved[-1][3] == "failed"


def test_community_pipeline_uses_community_collector():
    assert pipeline_service.pipeline_steps("community_insights")[0]["key"] == "community_insights_daily"


def test_pipeline_resume_skips_completed_steps(monkeypatch):
    from services import page_snapshot_service
    monkeypatch.setattr(page_snapshot_service, "publish_page_snapshots_sync", lambda: {"pages": []})
    called = []
    monkeypatch.setattr(pipeline_service, "_save", lambda *args: None)
    monkeypatch.setattr(pipeline_service, "run_task", lambda key, trigger: called.append(key) or {"count": 1})
    steps = pipeline_service.pipeline_steps("solutions")
    steps[0]["status"] = "success"
    pipeline_service._execute_pipeline(8, "solutions", steps)
    assert called == ["discovery_sentinel_daily", "radar_event_analysis_daily", "board_insights_daily"]
    assert all(step["status"] == "success" for step in steps)
