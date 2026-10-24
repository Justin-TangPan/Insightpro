from datetime import date
import pytest
from services import insight_dashboard_service as service


def test_history_aggregates_real_observed_days_without_filling_gaps(monkeypatch):
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return self
        def execute(self, query, params):
            assert params == (90,)
            assert "community_insights" in query
        def fetchall(self):
            return [{"day": date(2026, 10, 22), "name": "知乎热榜", "count": 2},
                    {"day": date(2026, 10, 24), "name": "知乎热榜", "count": 3},
                    {"day": date(2026, 10, 24), "name": "CSDN 热榜", "count": 1}]
    monkeypatch.setattr(service, "get_db", Connection)
    result = service.history("community")
    assert result["points"] == [{"date": "2026-10-22", "count": 2}, {"date": "2026-10-24", "count": 4}]
    assert len(result["groups"]) == 2
    with pytest.raises(ValueError):
        service.history("unknown")
