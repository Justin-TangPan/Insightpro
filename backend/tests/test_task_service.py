from services import task_service


def test_ai_brief_pipeline_finishes_before_default_email_window():
    schedules = {task.key: task.cron for task in task_service.TASKS}

    assert schedules["github_daily"] == {"hour": 8, "minute": 30}
    assert schedules["trending_business_eval_daily"] == {"hour": 8, "minute": 35}
    assert schedules["project_briefs_zh_daily"] == {"hour": 8, "minute": 55}
    assert schedules["ai_applications_daily"] == {"hour": 9, "minute": 30}
    assert schedules["board_insights_daily"] == {"hour": 10, "minute": 0}
    assert schedules["radar_event_analysis_daily"] == {"hour": 10, "minute": 15}


def test_task_schedule_uses_a_consistent_registry_cron(monkeypatch):
    class Cursor:
        def execute(self, *_): pass
        def fetchall(self): return [{"source_key": "github_trending", "adapter": "github_trending", "enabled": True,
                                    "schedule": {"cron": "15 7 * * *"}}]
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()

    monkeypatch.setattr(task_service, "_RUNTIME_CRONS", {})
    monkeypatch.setattr(task_service, "get_db", Connection)
    task_service.load_source_schedules()

    assert task_service._RUNTIME_CRONS == {"github_daily": "15 7 * * *"}
    assert str(task_service.task_trigger(task_service.TASK_BY_KEY["github_daily"]).fields[5]) == "7"


def test_source_task_mapping_supports_legacy_schedule_and_request_cache_sources():
    assert task_service.source_task_key({"adapter": "github_trending", "schedule": {}}) == "github_daily"
    assert task_service.source_task_key({"adapter": "product_hunt_feed", "schedule": {}}) == "discovery_sentinel_daily"
    assert task_service.source_task_key({"adapter": "community_zhihu", "schedule": {"task_key": "daily_crawl"}}) is None


def test_required_source_tasks_include_registered_sources(monkeypatch):
    from services import source_registry_service
    monkeypatch.setattr(source_registry_service, "list_sources", lambda: [
        {"adapter": "github_trending", "enabled": True, "schedule": {}},
        {"adapter": "community_zhihu", "enabled": True, "schedule": {}},
        {"adapter": "product_hunt_feed", "enabled": True, "schedule": {}},
        {"adapter": "arxiv_api", "enabled": False, "schedule": {}},
    ])
    assert task_service.required_source_tasks() == (
        "github_daily", "daily_crawl", "competitor_daily", "discovery_sentinel_daily")


def test_task_runner_records_one_success(monkeypatch):
    statements = []

    class Cursor:
        def execute(self, sql, params=()):
            statements.append((sql, params))
            self.row = {"acquired": True} if "pg_try_advisory_lock" in sql else {"id": 7}

        def fetchone(self):
            return self.row

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(task_service, "get_db", Connection)
    result = task_service.run_task("cleanup", "manual", lambda: {"deleted": 3})

    assert result == {"deleted": 3}
    assert sum("INSERT INTO platform_task_runs" in sql for sql, _ in statements) == 1
    updates = [params for sql, params in statements if "UPDATE platform_task_runs SET status=%s" in sql]
    assert updates[0][0] == "success"


def test_task_runner_records_partial_results_as_failed_with_details(monkeypatch):
    statements = []

    class Cursor:
        def execute(self, sql, params=()):
            statements.append((sql, params))
            self.row = {"acquired": True} if "pg_try_advisory_lock" in sql else {"id": 8}
        def fetchone(self): return self.row
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()

    monkeypatch.setattr(task_service, "get_db", Connection)
    result = {"status": "partial", "discovered": 4, "source_errors": {"github": "timeout"}}

    assert task_service.run_task("discovery_sentinel_daily", "manual", lambda: result) == result
    update = next(params for sql, params in statements if "UPDATE platform_task_runs SET status=%s" in sql)
    assert update[0] == "failed"
    assert update[2] == '{"github": "timeout"}'


def test_partial_task_records_a_visible_reason_when_no_source_error_is_provided(monkeypatch):
    statements = []
    class Cursor:
        def execute(self, sql, params=()):
            statements.append((sql, params))
            self.row = {"acquired": True} if "pg_try_advisory_lock" in sql else {"id": 9}
        def fetchone(self): return self.row
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(task_service, "get_db", Connection)

    task_service.run_task("cleanup", "manual", lambda: {"status": "partial_success", "count": 1})

    update = next(params for sql, params in statements if "UPDATE platform_task_runs SET status=%s" in sql)
    assert update[2] == "Task returned partial_success"


def test_orphaned_task_runs_are_repaired_only_when_advisory_lock_is_free(monkeypatch):
    statements = []
    lock_available = True

    class Cursor:
        rowcount = 2
        def execute(self, sql, params=()):
            statements.append((sql, params))
            if "SELECT DISTINCT task_key" in sql:
                self.rows = [{"task_key": "discovery_sentinel_daily"}]
            elif "pg_try_advisory_lock" in sql:
                self.row = {"acquired": lock_available}
        def fetchall(self): return self.rows
        def fetchone(self): return self.row
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(task_service, "get_db", Connection)

    assert task_service.recover_orphaned_runs() == 2
    assert any("SET status='failed'" in sql for sql, _ in statements)
    assert any("pg_advisory_unlock" in sql for sql, _ in statements)

    statements.clear()
    lock_available = False
    assert task_service.recover_orphaned_runs() == 0
    assert not any("SET status='failed'" in sql for sql, _ in statements)


def test_cleanup_unlinks_old_children_and_preserves_canonical_rows_used_by_recent_data(monkeypatch):
    from services import maintenance_service

    statements = []
    class Cursor:
        def execute(self, sql, params=()): statements.append((sql, params))
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return Cursor()
    monkeypatch.setattr(maintenance_service, "get_db", Connection)

    maintenance_service.cleanup_old_data()

    evaluation_cleanup = [sql for sql, _ in statements if "trending_business_eval" in sql]
    assert "UPDATE trending_business_eval SET analysis_id=NULL" in evaluation_cleanup[0]
    assert "recent.analysis_id=old.id" in evaluation_cleanup[1]
    assert "recent.scrape_date >= %s" in evaluation_cleanup[1]
