from datetime import datetime, timezone

from services import event_service


def test_event_listing_includes_vendor_kinds_and_source_names(monkeypatch):
    class Cursor:
        def execute(self, query, params):
            self.query = query
            self.params = params

        def fetchall(self):
            return [{"id": 5, "vendor": "OpenAI", "kinds": ["update"], "source_names": ["Official blog"]}]

    class Connection:
        def __init__(self):
            self.value = Cursor()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def cursor(self):
            return self.value

    conn = Connection()
    monkeypatch.setattr(event_service, "get_db", lambda: conn)

    result = event_service.list_events(business_scope="ai_applications")

    assert result["items"][0]["vendor"] == "OpenAI"
    assert result["items"][0]["kinds"] == ["update"]
    assert "COALESCE(entity.metadata->>'vendor', MIN(raw.content->>'vendor')) AS vendor" in conn.value.query
    assert "raw.content->>'kind'" in conn.value.query
    assert "raw.content->>'description'" in conn.value.query
    assert "source.name" in conn.value.query
    assert conn.value.params[2:4] == ("ai_applications", "ai_applications")


def test_event_presentation_uses_plain_titles_and_nonempty_source_summaries():
    project = event_service._present_event({"title": "Meloong-Git/PCL", "summary": "Minecraft 启动器 Plain Craft Launcher（PCL）。"})
    assert project["title"] == "Meloong-Git/PCL"
    assert project["summary"] == "Minecraft 启动器 Plain Craft Launcher（PCL）。"

    codex = event_service._present_event({
        "title": "2026-10-01 Codex app 26.930 New features Added moving chats to projects.",
        "summary": "2026-10-01 Codex app 26.930 New features Added moving chats to projects.",
        "published_at": "2026-10-01T00:00:00+00:00",
    })
    assert codex["title"] == "Codex app 26.930 · 新功能"
    assert codex["summary"] == "Added moving chats to projects."


def test_non_github_event_rescore_uses_generic_evidence_score(monkeypatch):
    event = {"id": 12, "entity_key": "url:abc", "event_key": "discovery:agent-topic",
             "status": "active", "scores": {"discovery_score": 64},
             "last_seen_at": datetime(2026, 10, 23, tzinfo=timezone.utc)}
    calls = []

    class Cursor:
        def execute(self, query, params=()): calls.append(query)
        def fetchone(self): return event
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()

    monkeypatch.setattr(event_service, "get_db", Connection)
    monkeypatch.setattr(event_service, "persist_signal_hot_score",
                        lambda cursor, entity_key, event_id, last_seen: {"value": 71, "version": "signal_hot_v1"})

    result = event_service.rescore_event(12, "00000000-0000-0000-0000-000000000001")

    assert result == {"event_id": 12, "hot_score": {"value": 71, "version": "signal_hot_v1"}}
    assert any("event_rescored" in query for query in calls)
