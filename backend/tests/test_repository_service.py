from datetime import date, datetime, timezone

from services import repository_service


def test_trending_repositories_reads_shared_events_and_entity_data(monkeypatch):
    observed_at = datetime(2026, 10, 23, 1, tzinfo=timezone.utc)

    class Cursor:
        def __init__(self): self.calls = 0
        def execute(self, *_): self.calls += 1
        def fetchall(self):
            return [{"entity_key": "github:org/repo", "repo_name": "org/repo", "repo_url": "https://github.com/org/repo",
                     "language": "Python", "content": {"description": "Agent toolkit", "stars": "3k", "forks": "50",
                     "today_stars": "250", "rank": 2}, "observed_at": observed_at, "event_id": 4,
                     "discovery_content": {"pushed_at": "2026-10-22T10:00:00Z", "topics": ["agent", "mcp"]},
                     "metadata_content": {"contributors_count": 12, "latest_release": {"tag_name": "v1.0.0"},
                                          "license": "MIT", "pushed_at": "2026-10-22T10:00:00Z",
                                          "topics": ["agent", "mcp"]}}]
    class Connection:
        def __enter__(self): self.value = Cursor(); return self
        def __exit__(self, *_): pass
        def cursor(self): return self.value

    monkeypatch.setattr(repository_service, "get_db", Connection)
    result = repository_service.list_trending_repositories("daily")

    assert result["source"] == "event_store"
    assert result["date"] == date(2026, 10, 23).isoformat()
    assert result["items"][0]["entity_key"] == "github:org/repo"
    assert result["items"][0]["event_id"] == 4
    assert result["items"][0]["stars"] == "3k"
    assert result["items"][0]["pushed_at"] == "2026-10-22T10:00:00Z"
    assert result["items"][0]["topics"] == ["agent", "mcp"]
    assert result["items"][0]["contributors_count"] == 12
    assert result["items"][0]["latest_release"]["tag_name"] == "v1.0.0"
    assert result["items"][0]["license"] == "MIT"


def test_trending_repositories_uses_legacy_read_when_v2_has_no_rows(monkeypatch):
    class Cursor:
        def __init__(self): self.calls = 0
        def execute(self, *_): self.calls += 1
        def fetchall(self):
            if self.calls == 1: return []
            return [{"repo_name": "org/legacy", "repo_url": "https://github.com/org/legacy", "description": "Old snapshot",
                     "language": "Go", "stars": "500", "forks": "20", "today_stars": "10",
                     "category": "daily", "scrape_date": date(2026, 10, 22)}]
    class Connection:
        def __enter__(self): self.value = Cursor(); return self
        def __exit__(self, *_): pass
        def cursor(self): return self.value

    monkeypatch.setattr(repository_service, "get_db", Connection)
    result = repository_service.list_trending_repositories("daily")

    assert result["source"] == "v1_compatibility"
    assert result["items"][0]["repo_name"] == "org/legacy"
    assert "entity_key" not in result["items"][0]
