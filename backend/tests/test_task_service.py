from services import task_service


def test_ai_brief_pipeline_finishes_before_default_email_window():
    schedules = {task.key: task.cron for task in task_service.TASKS}

    assert schedules["github_daily"] == {"hour": 8, "minute": 30}
    assert schedules["trending_business_eval_daily"] == {"hour": 8, "minute": 35}
    assert schedules["project_briefs_zh_daily"] == {"hour": 8, "minute": 55}


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
    assert sum("status='success'" in sql for sql, _ in statements) == 1
