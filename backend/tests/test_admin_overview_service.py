from datetime import datetime
from zoneinfo import ZoneInfo
from services import admin_overview_service


def test_overview_counts_one_multi_business_event_once(monkeypatch):
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    class Cursor:
        def execute(self, sql, *_): self.sql = sql
        def fetchall(self):
            if "FROM intelligence_sources" in self.sql:
                return [{"source_key": "official", "name": "Official", "business_scopes": ["ai_applications", "competitor_dynamics"],
                         "health_status": "healthy", "last_success_at": now, "last_error": None, "enabled": True, "raw_today": 3}]
            return [{"id": 9, "business_scopes": ["ai_applications", "competitor_dynamics"],
                     "status": "active", "first_seen_at": now, "published_at": now}]
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(admin_overview_service, "get_db", Connection)
    monkeypatch.setattr(admin_overview_service, "list_tasks", lambda: [])
    report = admin_overview_service.overview()
    assert report["raw_today"] == 3
    assert report["published_today"] == 1
    assert sum(item["published_today"] for item in report["domains"]) == 2


def test_overview_counts_tasks_without_last_run(monkeypatch):
    class Cursor:
        def execute(self, sql, *_): self.sql = sql
        def fetchall(self): return []
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(admin_overview_service, "get_db", Connection)
    monkeypatch.setattr(admin_overview_service, "list_tasks", lambda: [
        {"business_scopes": ["ai_applications"], "last_run": None},
        {"business_scopes": ["ai_applications"], "last_run": {"status": "failed"}},
    ])
    report = admin_overview_service.overview()
    assert report["failed_tasks"] == 1
    assert next(item for item in report["domains"] if item["key"] == "ai_applications")["failed_tasks"] == 1
