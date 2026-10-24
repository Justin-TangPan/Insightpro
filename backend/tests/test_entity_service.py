from services import entity_service


def test_entity_detail_returns_events_evidence_metrics_and_trends(monkeypatch):
    class Cursor:
        def __init__(self):
            self.one = {"entity_key": "github:org/repo", "entity_type": "repository", "canonical_name": "org/repo", "metadata": {}}
            self.many = iter(([{"id": 1}], [{"id": 10}], [{"metric_key": "stars", "metric_value": 12}], []))

        def execute(self, query, params):
            self.last_query = query
            self.params = params

        def fetchone(self):
            value, self.one = self.one, None
            return value

        def fetchall(self):
            return next(self.many)

    class Connection:
        def __init__(self): self.value = Cursor()
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return self.value

    connection = Connection()
    monkeypatch.setattr(entity_service, "get_db", lambda: connection)
    monkeypatch.setattr(entity_service, "trends_for_entity", lambda cursor, key: {"windows": {"1h": {}}})

    result = entity_service.get_entity_detail("github:org/repo")

    assert result["entity"]["entity_type"] == "repository"
    assert result["events"] == [{"id": 1}]
    assert result["evidence"] == [{"id": 10}]
    assert result["metrics"] == [{"metric_key": "stars", "metric_value": 12}]
    assert result["trends"] == {"windows": {"1h": {}}}
