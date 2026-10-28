from services.community_insight_service import _tech


def test_community_feed_prefers_technical_topics():
    items = [
        {"title": "娱乐新闻", "summary": "明星动态", "url": "https://example.com/entertainment"},
        {"title": "AI Agent 越界之后", "summary": "沙箱与安全", "url": "https://example.com/agent"},
    ]
    result = _tech(items)
    assert [item["title"] for item in result] == [items[1]["title"]]
    assert result[0]["topic_category"] == "Agent 与框架"


def test_community_feed_drops_generic_tech_and_invalid_links():
    items = [
        {"title": "科技行业观察", "summary": "开发者工具更新", "url": "https://example.com/news"},
        {"title": "AI 推理框架更新", "summary": "开源推理框架", "url": "javascript:alert(1)"},
    ]
    assert _tech(items) == []


def test_community_feed_classifies_ai_infrastructure():
    items = [{"title": "新一代 AI Infra 推理服务", "summary": "支持模型部署", "url": "https://example.com/infra"}]
    result = _tech(items)
    assert result[0]["topic_category"] == "AI Infra"
    assert result[0]["relevance"] == "high"


def test_community_feed_rejects_generic_node_agent_mentions():
    items = [{"title": "Komari 部署实战：节点 Agent 接入", "summary": "监控节点状态", "url": "https://example.com/komari"}]
    assert _tech(items) == []


def test_get_community_insights_reads_active_events(monkeypatch):
    from services import community_insight_service as community

    rows = [
        {"id": 1, "title": "AI Agent", "url": "https://example.com/agent", "summary": "s",
         "topic_category": "Agent 与框架", "relevance": "high", "published_at": None,
         "observed_at": None, "source_key": "community_zhihu"},
        {"id": 2, "title": "AI Infra", "url": "https://example.com/infra", "summary": "s",
         "topic_category": "AI Infra", "relevance": "high", "published_at": None,
         "observed_at": None, "source_key": "community_csdn"},
    ]

    class Cursor:
        def execute(self, sql, params=None):
            pass

        def fetchall(self):
            return rows

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(community, "get_db", lambda: Conn())
    result = community.get_community_insights()
    assert result["count"] == 2
    labels = {item["source"] for item in result["items"]}
    assert labels == {"知乎", "CSDN"}
    assert {item["title"] for item in result["items"]} == {"AI Agent", "AI Infra"}


def test_manual_community_refresh_updates_only_the_selected_source(monkeypatch):
    from services import community_insight_service as community
    calls, stored, health = [], [], []
    monkeypatch.setattr(community, "_cache", (1, [{"old": True}], (("old", "url"),)))
    monkeypatch.setattr(community, "list_sources", lambda: [
        {"source_key": "community_zhihu", "base_url": "https://example.test/zhihu", "enabled": True},
        {"source_key": "community_csdn", "base_url": "https://example.test/csdn", "enabled": True},
    ])
    monkeypatch.setitem(community.FEEDS, "community_zhihu", lambda url: calls.append(url) or [{"source": "知乎", "title": "AI Agent", "url": "https://example.test/item#fragment"}])
    monkeypatch.setattr(community, "store_community_raw", lambda rows: stored.extend(rows) or len(rows))
    monkeypatch.setattr(community, "record_source_health", lambda *args: health.append(args))
    result = community.refresh_community_source("community_zhihu")
    assert result["total"] == result["stored"] == 1
    assert calls == ["https://example.test/zhihu"]
    assert stored[0]["url"] == "https://example.test/item"
    assert stored[0]["published_at"] is None and stored[0]["observed_at"]
    assert health[0][0] == "community_zhihu"
    assert community._cache == (0, [], ())
