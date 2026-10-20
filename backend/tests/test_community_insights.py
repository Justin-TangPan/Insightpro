from services.community_insight_service import _tech


def test_community_feed_prefers_technical_topics():
    items = [
        {"title": "娱乐新闻", "summary": "明星动态"},
        {"title": "AI Agent 越界之后", "summary": "沙箱与安全"},
    ]
    assert _tech(items) == [items[1]]
