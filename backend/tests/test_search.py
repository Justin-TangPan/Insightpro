from routers.search import _rank, _snippet, _tokens


def test_search_tokens_ranking_and_snippet():
    assert _tokens("  AI   agent AI  ") == ["ai", "agent"]
    assert _rank({"title": "AI Agent 平台"}, "AI Agent", ["ai", "agent"])[0] == 1
    assert _rank({"title": "云上应用"}, "AI Agent", ["ai", "agent"])[0] == 4
    item = {"search_text": "统一可观测性平台支持日志、指标和链路追踪"}
    assert "可观测性" in _snippet(item, ["可观测性"])
    assert "search_text" not in item
