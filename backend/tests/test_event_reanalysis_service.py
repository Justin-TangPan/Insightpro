import pytest

from services import event_reanalysis_service as service


def test_reanalysis_rejects_implicit_history_and_oversized_selection():
    with pytest.raises(ValueError):
        service.start_reanalysis("selected", "actor", event_ids=[])
    with pytest.raises(ValueError):
        service.start_reanalysis("active", "actor", event_ids=[1])
    with pytest.raises(ValueError):
        service.start_reanalysis("selected", "actor", event_ids=list(range(501)))


def test_reanalysis_selection_is_bounded_and_tracked(monkeypatch):
    statements = []

    class Cursor:
        def execute(self, sql, params=()): statements.append((sql, params))
        def fetchall(self): return [{"id": 3}, {"id": 2}]
        def fetchone(self): return {"id": 9}

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()

    monkeypatch.setattr(service, "get_db", Connection)
    result = service.start_reanalysis("pending_review", "actor", "solutions")
    assert result == {"run_id": 9, "event_ids": [3, 2]}
    assert "LIMIT 500" in statements[0][0]
    assert statements[0][1] == ["solutions", "solutions"]
    assert "INSERT INTO platform_task_runs" in statements[1][0]
