from datetime import datetime, timezone

from services import recall_benchmark_service


def test_recall_report_uses_only_labeled_relevant_independent_samples(monkeypatch):
    observed_at = datetime.now(timezone.utc)
    rows = [
        {"id": 1, "title": "Captured signal", "reference_source": "Independent list", "is_relevant": True,
         "reference_at": observed_at, "raw_id": 10, "source_key": "hacker_news", "event_id": 8,
         "represented": True},
        {"id": 2, "title": "Missed signal", "reference_source": "Independent list", "is_relevant": True,
         "reference_at": observed_at, "raw_id": None, "source_key": None, "event_id": None,
         "represented": False},
        {"id": 3, "title": "Labeled non-hot", "reference_source": "Independent list", "is_relevant": False,
         "reference_at": observed_at, "raw_id": 11, "source_key": "hacker_news", "event_id": 9,
         "represented": True},
    ]

    class Cursor:
        def execute(self, query, params):
            assert "reference.reference_at+INTERVAL '24 hours'" in query
            assert params == (30,)
        def fetchall(self): return rows
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(recall_benchmark_service, "get_db", Connection)

    report = recall_benchmark_service.recall_report()

    assert (report["sample_count"], report["relevant_count"], report["found_count"]) == (3, 2, 1)
    assert (report["missed_count"], report["recall_rate"], report["event_rate"]) == (1, 50.0, 50.0)
    assert report["items"][0]["found"] is True
    assert report["items"][1]["found"] is False
