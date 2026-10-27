from contextlib import contextmanager

from routers import search
from routers.search import _snippet, _tokens


def test_search_tokens_and_snippet():
    assert _tokens("  AI   agent AI  ") == ["ai", "agent"]
    item = {"search_text": "统一可观测性平台支持日志、指标和链路追踪"}
    assert "可观测性" in _snippet(item, ["可观测性"])
    assert "search_text" not in item


def test_search_query_covers_ai_apps_and_keeps_full_counts(monkeypatch):
    captured = {}

    class Cursor:
        def execute(self, sql, params):
            captured.update(sql=sql, params=params)
            assert sql.count("%s") == len(params)
            assert sql.count("%") == sql.count("%s")

        def fetchall(self):
            return [{
                "item_type": "ai_application", "title": "Claude Code", "source": "Anthropic",
                "url": "https://example.com/claude-code", "item_date": "2026-10-20",
                "date_basis": "published", "search_text": "Claude Code AI coding agent",
                "total": 137, "technical": 25, "solution": 20, "competitor": 15,
                "ai_application": 37, "community": 5, "requirement": 20, "managed_solution": 20,
            }]

    class Connection:
        def cursor(self):
            return Cursor()

    @contextmanager
    def fake_db():
        yield Connection()

    monkeypatch.setattr(search, "get_db", fake_db)
    result = search._search("Claude Code", "all", 2, 12, "user-1", "2026-10-01", "2026-10-22")

    assert "FROM vendor_ai_applications WHERE kind <> 'product'" in captured["sql"]
    assert "title, link AS url, summary, category, published_date" in captured["sql"]
    assert "FROM intelligence_events v2_event" in captured["sql"]
    assert "'v2:' || v2_event.id" in captured["sql"]
    assert "left(item.item_key, 3) = 'v2:'" in captured["sql"]
    assert "SELECT * FROM compatible i" in captured["sql"]
    assert "LIMIT 100" not in captured["sql"]
    assert "count(*) FILTER (WHERE item_type='ai_application')" in captured["sql"]
    assert "s.ai_application, s.community, s.requirement" in captured["sql"]
    assert captured["params"][:2] == ("user-1", "user-1")
    assert result["total"] == 137 and result["facets"]["ai_application"] == 37
    assert result["facets"]["community"] == 5
    assert result["results"][0]["date_basis"] == "published"
