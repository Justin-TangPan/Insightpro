from datetime import date, datetime
from services import radar_service
from services import email_service
from services import email_dashboard
from services import agent_launch_service


def test_snapshot_counts_five_directions(monkeypatch):
    class Cursor:
        def __init__(self):
            self.calls = 0

        def execute(self, *_):
            self.calls += 1

        def fetchall(self):
            if self.calls == 1:
                return [
                    {"title": "Browser Agent launch", "summary": "", "url": "https://example.com/a", "day": "2026-10-19", "source": "Vendor"},
                    {"title": "Browser Agent launch", "summary": "", "url": "https://example.com/a", "day": "2026-10-19", "source": "Vendor"},
                    {"title": "New AI browser app", "summary": "", "url": "https://example.com/b", "day": "2026-10-10", "source": "Vendor"},
                ]
            return [{"title": "GPU runtime", "summary": "", "url": "https://example.com/c", "day": "2026-10-19", "source": "GitHub", "evaluation": 9, "action": "研究"}]

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(radar_service, "get_db", lambda: Connection())
    monkeypatch.setattr(agent_launch_service, "snapshot", lambda: ([], False))
    snapshot = radar_service.build_radar_snapshot(date(2026, 10, 19))
    assert snapshot["today_count"] == 2
    assert snapshot["recent_count"] == 2
    assert snapshot["evaluated_count"] == 1
    assert len(snapshot["categories"]) == 5
    assert len(snapshot["top_signals"]) == 1


def test_business_email_uses_homepage_snapshot_and_escapes_content():
    snapshot = {
        "as_of": "2026-10-25T10:05:00+08:00",
        "focus": {"type": "新产品", "event": {"id": "event:12", "title": "Focus <launch>", "summary": "Released", "why": "Business impact", "vendor": "Vendor", "sources": [{"url": "https://example.com/focus"}]}},
        "keypoints": [],
        "insights": [{"label": "厂商动态", "event": {"why": "Core judgment"}}],
        "boards": [{"name": name, "events": [{"title": "Board item", "summary": "Homepage board summary", "sources": []}]} for name in ("技术生态", "AI 应用", "解决方案", "社区洞察", "友商动态")],
        "vendors": [], "latest": [],
    }
    html = email_dashboard.build_html(snapshot=snapshot)
    assert "Focus &lt;launch&gt;" in html
    assert "Core judgment" in html
    assert "Homepage board summary" in html and "小雷达首页商业情报简报" in html
    assert all(name in html for name in ("技术生态", "AI 应用", "解决方案", "社区洞察", "友商动态"))
    assert all(title in html for title in ("近期焦点", "本期核心判断", "五大业务摘要", "重点动态", "厂商关注 / 友商动态摘要", "最新动态", "查看完整首页"))
    assert 'href="https://example.com/focus"' in html


def test_digest_starts_at_scheduled_window():
    now = email_service.SHANGHAI_TZ.localize(datetime(2026, 10, 19, 9, 5))
    assert not email_service.daily_digest_ready(now)
    assert email_service.daily_digest_ready(now.replace(hour=10, minute=5))


def test_product_hunt_feed_selects_recent_ai_apps():
    xml = b'''<feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>VoiceNote</title><published>2026-10-18T12:00:00Z</published>
        <content type="html">&lt;p&gt;AI voice notes for your day&lt;/p&gt;</content>
        <link rel="alternate" href="https://www.producthunt.com/products/voicenote" /></entry>
      <entry><title>GPU Index</title><published>2026-10-18T12:00:00Z</published>
        <content type="html">&lt;p&gt;AI GPU infrastructure database&lt;/p&gt;</content>
        <link rel="alternate" href="https://www.producthunt.com/products/gpu-index" /></entry>
      <entry><title>Old App</title><published>2026-09-01T12:00:00Z</published>
        <content type="html">&lt;p&gt;AI agent for notes&lt;/p&gt;</content>
        <link rel="alternate" href="https://www.producthunt.com/products/old-app" /></entry>
    </feed>'''
    apps = radar_service._parse_product_hunt_feed(xml, date(2026, 10, 19))
    assert [app["title"] for app in apps] == ["VoiceNote"]
    assert "语音" in apps[0]["summary"]
    assert "切换 AI Agent" in radar_service._app_brief("Switch AI agents without re-explaining your work")[0]


def test_solution_analysis_omits_catalog_metadata():
    analysis = radar_service._analysis_text(
        "Solution value: 方案帮助企业降低模型部署复杂度。; Open-source projects: example/repo; Alibaba Cloud resources: ACS")
    assert analysis == "方案帮助企业降低模型部署复杂度。"


def test_deepseek_github_update_is_a_vendor_radar_event(monkeypatch):
    queries = []
    class Cursor:
        def __init__(self):
            self.sql = ""
        def execute(self, sql, params=()):
            self.sql = sql
            queries.append((sql, params))
        def fetchall(self):
            if "FROM competitor_news" in self.sql:
                return [{"vendor": "DeepSeek", "title": "DeepInfer 推理框架动态", "summary": "DeepSeek 官方发布动态。",
                         "url": "https://github.com/deepseek-ai/DeepInfer", "happened_at": "2026-10-20",
                         "board": "competitors", "category": ""}]
            if "FROM vendor_ai_applications" in self.sql:
                return [
                    {"vendor": "DeepSeek", "title": "DeepInfer 推理框架动态", "summary": "开源推理框架。",
                     "url": "https://github.com/deepseek-ai/DeepInfer", "happened_at": "2026-10-20",
                     "board": "apps", "category": ""},
                    {"vendor": "DeepSeek", "title": "DeepSeek 30 天前的官方更新", "summary": "旧版官方动态。",
                     "url": "https://github.com/deepseek-ai/older", "happened_at": "2026-09-22",
                     "board": "apps", "category": ""},
                ]
            return []

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()

    monkeypatch.setattr(radar_service, "get_db", lambda: Connection())
    monkeypatch.setattr("services.community_insight_service.get_community_insights", lambda: {"items": []})
    monkeypatch.setattr(radar_service.ai_service, "chat_complete", lambda **_: (_ for _ in ()).throw(AssertionError("Radar reads must not call AI")))
    data = radar_service.build_intelligence_radar(datetime(2026, 10, 21, 10, 0))
    event = next(item for item in data["events"] if item["vendor"] == "DeepSeek")
    assert event["board"] == "apps"
    assert event["type"] == "AI 应用"
    assert {source["name"] for source in event["sources"]} == {"DeepSeek", "DeepSeek 官方 GitHub"}
    assert event["boards"] == ["competitors", "apps"]
    assert any(item["title"] == "DeepSeek 30 天前的官方更新" for item in data["events"])
    assert data["vendors"] == ["DeepSeek"]
    assert data["event_count"] == 2
    assert not event["analysis"]
    apps_query = next((sql, params) for sql, params in queries if "FROM vendor_ai_applications" in sql)
    assert "BETWEEN %s AND %s" in apps_query[0]
    assert apps_query[1] == ("2026-09-22", "2026-10-21")
    solutions_query = next(sql for sql, _ in queries if "FROM aliyun_solutions" in sql)
    assert "WHEN NOT is_active THEN removed_at::date" in solutions_query


def test_community_observation_is_not_counted_as_published_today(monkeypatch):
    class Cursor:
        def execute(self, *_): pass
        def fetchall(self): return []

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()

    monkeypatch.setattr(radar_service, "get_db", lambda: Connection())
    monkeypatch.setattr("services.community_insight_service.get_community_insights", lambda: {"items": [
        {"source": "知乎", "title": "AI Agent 如何安全调用工具", "summary": "当前讨论话题", "url": "https://example.com/agent",
         "observed_at": "2026-10-21T09:00"}
    ]})
    monkeypatch.setattr(radar_service.ai_service, "chat_complete", lambda **_: (_ for _ in ()).throw(AssertionError("Radar reads must not call AI")))

    data = radar_service.build_intelligence_radar(datetime(2026, 10, 21, 10, 0))
    event = next(item for item in data["events"] if item["board"] == "community")
    assert event["date_basis"] == "observed"
    assert data["today_count"] == 0


def test_radar_prefers_v2_event_id_and_merges_legacy_evidence(monkeypatch):
    class Cursor:
        sql = ""
        def execute(self, sql, *_): self.sql = sql
        def fetchall(self):
            if "FROM intelligence_events e" in self.sql:
                return [{"v2_event_id": 55, "title": "OpenAI launches Codex workspace",
                         "summary": "Official release", "url": "https://openai.com/index/codex-workspace",
                         "source": "Official feed", "vendor": "OpenAI", "category": "official_ai_application",
                         "board": "apps", "happened_at": "2026-10-20", "date_basis": "published", "scores": {}}]
            if "FROM competitor_news" in self.sql:
                return [{"vendor": "OpenAI", "title": "OpenAI launches Codex workspace",
                         "summary": "Same announcement", "url": "https://openai.com/index/codex-workspace",
                         "happened_at": "2026-10-20", "board": "competitors", "category": "product"}]
            return []

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()

    monkeypatch.setattr(radar_service, "get_db", lambda: Connection())
    monkeypatch.setattr("services.community_insight_service.get_community_insights", lambda: {"items": []})
    monkeypatch.setattr(radar_service.ai_service, "chat_complete",
                        lambda **_: (_ for _ in ()).throw(AssertionError("Radar reads must not call AI")))

    data = radar_service.build_intelligence_radar(datetime(2026, 10, 21, 10, 0))
    event = next(item for item in data["events"] if item.get("event_id") == 55)
    assert event["id"] == "event:55"
    assert event["boards"] == ["apps", "competitors"]
    assert {source["name"] for source in event["sources"]} == {"Official feed", "OpenAI"}


def test_radar_keeps_distinct_release_anchors_on_one_official_page(monkeypatch):
    class Cursor:
        sql = ""
        def execute(self, sql, *_): self.sql = sql
        def fetchall(self):
            if "FROM vendor_ai_applications" in self.sql:
                base = "https://www.kimi.com/code/docs/en/kimi-code/whats-new.html"
                return [
                    {"vendor": "Kimi", "title": "Kimi Code · K3.1 Pro Series is live", "summary": "Latest Model Release K3.1 Pro Series is live", "url": f"{base}#update-2026-10-23-0", "happened_at": "2026-10-23", "date_basis": "published", "board": "apps", "category": ""},
                    {"vendor": "Kimi", "title": "Kimi Code · v1.1.0", "summary": "Version update", "url": f"{base}#update-2026-10-14-0", "happened_at": "2026-10-14", "date_basis": "published", "board": "apps", "category": ""},
                ]
            return []

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return Cursor()

    monkeypatch.setattr(radar_service, "get_db", Connection)
    monkeypatch.setattr("services.community_insight_service.get_community_insights", lambda: {"items": []})
    data = radar_service.build_intelligence_radar(datetime(2026, 10, 25, 10, 0))
    kimi = [item for item in data["events"] if item["vendor"] == "Kimi"]
    assert len(kimi) == 2
    assert {item["happened_at"] for item in kimi} == {"2026-10-23", "2026-10-14"}
    assert any("K3.1 Pro" in item["title"] for item in kimi)


def test_radar_date_basis_uses_same_priority_as_selected_timestamp(monkeypatch):
    import re
    queries = []
    class Cursor:
        def execute(self, sql, *_): queries.append(sql)
        def fetchall(self): return []
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return Cursor()

    monkeypatch.setattr(radar_service, "get_db", Connection)
    monkeypatch.setattr("services.community_insight_service.get_community_insights", lambda: {"items": []})
    radar_service.build_intelligence_radar(datetime(2026, 10, 21, 10, 0))
    sql = next(query for query in queries if "FROM intelligence_events e" in query)
    compact = re.sub(r"\s+", "", sql)
    assert "COALESCE(e.published_at,e.event_at,raw.published_at,raw.observed_at)" in compact
    assert "WHENe.event_atISNOTNULLTHEN'event'WHENraw.published_atISNOTNULLTHEN'published'" in compact


def test_radar_analysis_task_caps_work(monkeypatch):
    events = [{"id": index, "analysis": ""} for index in range(100)]
    received = []
    monkeypatch.setattr(radar_service, "build_intelligence_radar", lambda: {"events": events})
    monkeypatch.setattr(radar_service, "_ensure_radar_analyses", lambda batch: received.extend(batch))

    result = radar_service.analyze_radar_events()

    assert result == {"processed": 24}
    assert len(received) == 24
