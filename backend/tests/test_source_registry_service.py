import pytest

from services import source_registry_service


def test_create_source_registers_supported_adapter_disabled_and_audited(monkeypatch):
    statements = []
    row = {"source_key": "custom_hn", "name": "Custom HN", "adapter": "hacker_news_api",
           "base_url": "https://example.test/v0/topstories.json", "enabled": False}

    class Cursor:
        def execute(self, query, params=()):
            statements.append((query, params))
            self.query = query
        def fetchone(self):
            if "SELECT schedule FROM intelligence_sources" in self.query:
                return {"schedule": {"task_key": "discovery_sentinel_daily", "cron": "45 9 * * *"}}
            return row
        def fetchall(self):
            return [{"source_key": "custom_hn", "schedule": {"task_key": "discovery_sentinel_daily", "cron": "45 9 * * *"}}]
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()

    monkeypatch.setattr(source_registry_service, "get_db", Connection)
    created = source_registry_service.create_source({
        "source_key": "custom_hn", "name": "Custom HN", "adapter": "hacker_news_api",
        "base_url": "https://example.test/v0/topstories.json", "business_scopes": ["technology_ecosystem"],
        "authority": "P1", "priority": 50, "cron": "15 8 * * *",
    }, "00000000-0000-0000-0000-000000000001")

    assert created["enabled"] is False
    assert "discovery_sentinel_daily" in statements[0][1][-1]
    assert any("source_created" in query for query, _ in statements)
    assert any("source_schedule_changed" in query for query, _ in statements)


def test_create_source_rejects_unsupported_adapter_before_database_access(monkeypatch):
    monkeypatch.setattr(source_registry_service, "get_db",
                        lambda: (_ for _ in ()).throw(AssertionError("database should not be touched")))

    with pytest.raises(ValueError, match="not supported"):
        source_registry_service.create_source({
            "source_key": "custom_feed", "name": "Custom Feed", "adapter": "unknown",
            "base_url": "https://example.test/feed", "business_scopes": ["technology_ecosystem"],
            "authority": "P1", "priority": 50, "cron": "45 9 * * *",
        }, "00000000-0000-0000-0000-000000000001")


def test_rss_feed_is_a_supported_discovery_source():
    assert "rss_feed" in source_registry_service.DISCOVERY_ADAPTERS


def test_source_edit_can_change_name_and_collector_url_with_audit(monkeypatch):
    statements = []
    class Cursor:
        def execute(self, query, params=()):
            statements.append((query, params))
            self.query = query
        def fetchone(self):
            if "SELECT name,base_url" in self.query:
                return {"name": "Old", "base_url": "https://old.example/feed",
                        "priority": 10, "authority": "P1", "business_scopes": ["technology_ecosystem"]}
            return {"source_key": "source_a", "name": "New", "base_url": "https://new.example/feed",
                    "priority": 10, "authority": "P1", "business_scopes": ["technology_ecosystem"]}
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()

    monkeypatch.setattr(source_registry_service, "get_db", Connection)
    updated = source_registry_service.update_source("source_a", {
        "name": "New", "base_url": "https://new.example/feed",
    }, "00000000-0000-0000-0000-000000000001")

    assert updated["base_url"] == "https://new.example/feed"
    assert any("source_updated" in query for query, _ in statements)


def test_source_edit_rejects_non_https_url_before_database_access(monkeypatch):
    monkeypatch.setattr(source_registry_service, "get_db",
                        lambda: (_ for _ in ()).throw(AssertionError("database should not be touched")))

    with pytest.raises(ValueError, match="HTTPS"):
        source_registry_service.update_source("source_a", {"base_url": "http://example.test/feed"},
                                              "00000000-0000-0000-0000-000000000001")


def test_source_schedule_update_propagates_to_sources_sharing_a_collector(monkeypatch):
    statements = []

    class Cursor:
        def execute(self, query, params=()):
            statements.append((query, params))
            self.query = query

        def fetchone(self):
            return {"schedule": {"task_key": "discovery_sentinel_daily", "cron": "45 9 * * *"}}

        def fetchall(self):
            return [
                {"source_key": "hacker_news", "schedule": {"task_key": "discovery_sentinel_daily", "cron": "45 9 * * *"}},
                {"source_key": "product_hunt", "schedule": {"task_key": "discovery_sentinel_daily", "cron": "45 9 * * *"}},
            ]

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()

    monkeypatch.setattr(source_registry_service, "get_db", Connection)

    result = source_registry_service.update_source_schedule("hacker_news", "15 8 * * *", "user-id")

    assert result == {"task_key": "discovery_sentinel_daily", "cron": "15 8 * * *",
                     "source_keys": ["hacker_news", "product_hunt"]}
    assert sum("UPDATE intelligence_sources SET" in query for query, _ in statements) == 2
    assert sum("source_schedule_changed" in query for query, _ in statements) == 2


def test_source_schedule_rejects_invalid_cron_before_database_access(monkeypatch):
    monkeypatch.setattr(source_registry_service, "get_db",
                        lambda: (_ for _ in ()).throw(AssertionError("database should not be touched")))

    with pytest.raises(ValueError):
        source_registry_service.update_source_schedule("hacker_news", "not a cron", "user-id")


def test_source_connection_test_is_bounded_and_audited(monkeypatch):
    statements = []
    class Response:
        status_code = 200
        closed = False
        def close(self): self.closed = True

    response = Response()
    def request(url, **kwargs):
        assert url == "https://example.com/feed"
        assert kwargs["timeout"] == 8
        assert kwargs["allow_redirects"] is False
        assert kwargs["stream"] is True
        return response

    class Cursor:
        def execute(self, query, params=()):
            statements.append((query, params))
        def fetchone(self): return {"name": "Example", "adapter": "rss", "base_url": "https://example.com/feed"}
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()

    monkeypatch.setattr(source_registry_service, "get_db", Connection)
    monkeypatch.setattr(source_registry_service.requests, "get", request)

    result = source_registry_service.test_source_connection("example", "00000000-0000-0000-0000-000000000001")

    assert result["ok"] is True
    assert result["status_code"] == 200
    assert response.closed
    assert any("source_connection_tested" in query for query, _ in statements)
