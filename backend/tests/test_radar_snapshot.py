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


def test_email_dashboard_has_five_recent_boards_and_safe_sources(monkeypatch):
    boards = list(email_dashboard.BOARDS)
    monkeypatch.setattr("services.event_service.list_events", lambda *_: {"items": []})
    monkeypatch.setattr(radar_service, "build_intelligence_radar", lambda *_: (_ for _ in ()).throw(AssertionError("Email must use the board snapshot only")))
    monkeypatch.setattr(email_dashboard, "current_analyses", lambda _: {
        board: {"judgment": f"{board} 已有变化", "focus": {
            "title": f"{board} <update>", "url": "https://example.com/" + board, "meta": "官方",
            "why": "近期热度与业务价值同时提升。", "analysis": "该项目更新了关键能力。",
            "impact": "可能增加云服务需求。", "caveat": "采用率待核实。"}}
        for board in boards})
    html = email_service.build_daily_digest_html()
    assert "五大业务情报简报" in html and "五个板块均有当日分析缓存" in html
    assert all(name in html for name in ("GitHub 技术", "AI 应用", "解决方案", "社区洞察", "厂商动态"))
    assert html.count("查看板块详情") == 5
    assert html.count("总体判断") == 5 and html.count("本期重点分析") == 5
    assert "近期热度与业务价值同时提升。" in html and "可能增加云服务需求。" in html
    assert "github &lt;update&gt;" in html and 'href="javascript:' not in html
    assert "当前社区热榜" in html and "首屏情报雷达" not in html and "data:image" not in html
    assert "Five-board intelligence brief" in email_service.build_daily_digest_html("en")


def test_business_email_does_not_fill_missing_board_focus_from_live_radar(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr("services.event_service.list_events", lambda *_: {"items": []})
    monkeypatch.setattr(email_dashboard, "settings", SimpleNamespace(BASE_URL="https://insight.example"))
    monkeypatch.setattr(email_dashboard, "current_analyses", lambda _: {
        "apps": {"analysis_version": 4, "judgment": "缓存板块结论。", "focus": None}})
    monkeypatch.setattr(radar_service, "build_intelligence_radar", lambda *_: (_ for _ in ()).throw(AssertionError("Live radar must not be mixed into email")))

    html = email_dashboard.build_html()

    assert "缓存板块结论。" in html
    assert "live-only-event" not in html
    assert "未缓存来源不作补入" in html
    assert "已展示可核实的近期来源" not in html


def test_business_email_status_is_literal_when_all_cached_boards_have_no_focus(monkeypatch):
    monkeypatch.setattr("services.event_service.list_events", lambda *_: {"items": []})
    monkeypatch.setattr(email_dashboard, "current_analyses", lambda _: {
        board: {"analysis_version": 4, "judgment": "暂无可核实信息。", "focus": None}
        for board in email_dashboard.BOARDS})
    monkeypatch.setattr(radar_service, "build_intelligence_radar", lambda *_: (_ for _ in ()).throw(AssertionError("Live radar must not be mixed into email")))

    html = email_dashboard.build_html()

    assert "五个板块均有当日分析缓存" in html
    assert "无焦点板块不补入其他来源" in html
    assert "当前没有缓存重点来源" in html


def test_digest_waits_for_analyses_then_uses_late_fallback(monkeypatch):
    now = email_service.SHANGHAI_TZ.localize(datetime(2026, 10, 19, 9, 5))
    monkeypatch.setattr(email_dashboard, "current_analyses", lambda _: {})
    assert not email_service.daily_digest_ready(now)
    assert not email_service.daily_digest_ready(now.replace(hour=10, minute=5))
    assert email_service.daily_digest_ready(now.replace(hour=11, minute=30))
    monkeypatch.setattr(email_dashboard, "current_analyses", lambda _: dict.fromkeys(email_dashboard.BOARDS, {}))
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
