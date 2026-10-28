import pytest
from services import event_service


def test_publish_requires_evidence_and_records_audit(monkeypatch):
    statements = []
    event = {"id": 4, "status": "pending_review", "business_scopes": ["ai_applications", "competitor_dynamics"], "title": "Agent launch", "scores": {"ai_analysis": {"what_happened": "Agent launched"}}, "analysis_status": "fresh", "entity_key": "entity", "event_key": "discovery:x", "last_seen_at": None}
    class Cursor:
        def execute(self, sql, params=()): statements.append((sql, params)); self.sql = sql
        def fetchone(self):
            if "SELECT id,status,business_scopes,title" in self.sql: return event
            if "SELECT COUNT(*)" in self.sql: return {"count": 2}
            if "RETURNING *" in self.sql: return {**event, "status": "active"}
            raise AssertionError(self.sql)
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(event_service, "get_db", Connection)
    monkeypatch.setattr(event_service, "persist_event_hot_score", lambda *args: {"value": 50})
    published = event_service.publish_event(4, "00000000-0000-0000-0000-000000000001")
    assert published["status"] == "active"
    assert any("published_at=NOW()" in sql for sql, _ in statements)
    assert any("event_published" in sql for sql, _ in statements)


def test_unreviewed_event_cannot_be_made_public_with_generic_patch(monkeypatch):
    class Cursor:
        def execute(self, sql, params=()): pass
        def fetchone(self): return {"status": "pending_review"}
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(event_service, "get_db", Connection)
    with pytest.raises(ValueError, match="publish action"):
        event_service.update_event(4, {"status": "active"}, "00000000-0000-0000-0000-000000000001")


def test_stale_analysis_cannot_be_published(monkeypatch):
    class Cursor:
        def execute(self, sql, params=()): pass
        def fetchone(self):
            return {"id": 4, "status": "pending_review", "business_scopes": ["solutions"],
                    "title": "Solution", "scores": {"ai_analysis": {"what_happened": "Changed"}},
                    "analysis_status": "stale"}
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(event_service, "get_db", Connection)
    with pytest.raises(ValueError, match="stale"):
        event_service.publish_event(4, "00000000-0000-0000-0000-000000000001")
