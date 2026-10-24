from datetime import datetime, timedelta

from services import email_dashboard, email_service, email_technical_dashboard


def test_subscriber_schedule_and_sent_html(monkeypatch):
    monday = email_service.SHANGHAI_TZ.localize(datetime(2026, 8, 24, 9, 5))
    subscriber = {
        "id": 1,
        "email": "reader@example.com",
        "weekdays": [0, 2, 4],
        "send_time": "09:05",
        "last_sent_at": monday - timedelta(days=1),
    }
    assert email_service.subscriber_is_due(subscriber, monday)
    assert email_service.subscriber_is_due(subscriber, monday.replace(hour=9, minute=6))
    assert not email_service.subscriber_is_due(subscriber, monday.replace(hour=9, minute=4))
    assert not email_service.subscriber_is_due({**subscriber, "last_sent_at": monday}, monday)

    sent = []
    monkeypatch.setattr(email_service, "get_subscribers", lambda: [subscriber])
    monkeypatch.setattr(email_service, "daily_digest_ready", lambda _: True)
    monkeypatch.setattr(email_service, "build_daily_digest_html", lambda language: f"<html>{language}</html>")
    monkeypatch.setattr(email_service, "build_technical_digest_html", lambda language: f"<technical>{language}</technical>")
    monkeypatch.setattr(email_service, "send_email", lambda email, subject, html: sent.append((email, html)) or True)

    sent_briefs = set()

    class Cursor:
        def execute(self, query, params=()):
            if "SELECT delivery_type" in query:
                self.rows = [{"delivery_type": kind} for kind in sent_briefs]
            elif "INSERT INTO email_delivery_attempts" in query and params[4] == "sent":
                sent_briefs.add(params[3])
            else:
                self.rows = []

        def fetchall(self):
            return getattr(self, "rows", [])

    class Connection:
        def cursor(self):
            return Cursor()

    class Context:
        def __enter__(self):
            return Connection()

        def __exit__(self, *_):
            pass

    monkeypatch.setattr(email_service, "get_db", Context)
    assert email_service.send_scheduled_digests(monday) == {"sent": 1, "total": 1, "deliveries": 2}
    assert sent == [("reader@example.com", "<html>zh</html>"), ("reader@example.com", "<technical>zh</technical>")]

    monkeypatch.setattr(email_service, "daily_digest_ready", lambda _: False)
    assert email_service.send_scheduled_digests(monday.replace(hour=9, minute=6)) == {"sent": 0, "total": 0}
    assert len(sent) == 2


def test_scheduled_email_retries_only_the_failed_brief(monkeypatch):
    now = email_service.SHANGHAI_TZ.localize(datetime(2026, 8, 24, 9, 5))
    subscriber = {"id": 2, "email": "retry@example.com", "weekdays": [0], "send_time": "09:05",
                  "last_sent_at": now - timedelta(days=1)}
    delivered = set()
    calls = []

    class Cursor:
        def execute(self, query, params=()):
            if "SELECT delivery_type" in query:
                self.rows = [{"delivery_type": kind} for kind in delivered]
            elif "INSERT INTO email_delivery_attempts" in query:
                kind, status = params[3], params[4]
                if status == "sent":
                    delivered.add(kind)
            else:
                self.rows = []

        def fetchall(self):
            return getattr(self, "rows", [])

    class Connection:
        def cursor(self): return Cursor()

    class Context:
        def __enter__(self): return Connection()
        def __exit__(self, *_): pass

    results = iter((True, False, True))
    monkeypatch.setattr(email_service, "get_subscribers", lambda: [subscriber])
    monkeypatch.setattr(email_service, "daily_digest_ready", lambda _: True)
    monkeypatch.setattr(email_service, "_digest_messages", lambda *_: [("business", "b"), ("technical", "t")])
    monkeypatch.setattr(email_service, "send_email", lambda email, subject, html: calls.append(subject) or next(results))
    monkeypatch.setattr(email_service, "get_db", Context)

    assert email_service.send_scheduled_digests(now) == {"sent": 0, "total": 1, "deliveries": 1}
    assert email_service.send_scheduled_digests(now) == {"sent": 1, "total": 1, "deliveries": 1}
    assert calls == ["business", "technical", "technical"]


def test_manual_email_run_records_each_brief_delivery(monkeypatch):
    subscriber = {"id": 3, "email": "manual@example.com", "language": "zh"}
    attempts = []

    class Cursor:
        def execute(self, query, params=()):
            if "INSERT INTO email_delivery_attempts" in query:
                attempts.append(params)

    class Connection:
        def cursor(self): return Cursor()

    class Context:
        def __enter__(self): return Connection()
        def __exit__(self, *_): pass

    monkeypatch.setattr(email_service, "get_subscribers", lambda: [subscriber])
    monkeypatch.setattr(email_service, "_digest_messages", lambda *_: [("business", "b"), ("technical", "t")])
    monkeypatch.setattr(email_service, "send_email", lambda *_: True)
    monkeypatch.setattr(email_service, "get_db", Context)

    result = email_service.send_daily_digest()

    assert result == {"sent": 1, "total": 1, "deliveries": 2}
    assert [(row[3], row[4]) for row in attempts] == [("business", "sent"), ("technical", "sent")]


def test_technical_email_uses_repository_facts_and_escapes_source_text(monkeypatch):
    monkeypatch.setattr(email_technical_dashboard, "_rows", lambda: [{
        "repo_name": "org/project", "repo_url": "https://github.com/org/project",
        "description": "Agent toolkit <script>alert(1)</script>", "language": "Python",
        "stars": "12.4k", "forks": "800", "today_stars": "500 stars today",
        "total": 8, "recommendation": "值得验证", "reasoning": "项目支持工具调用。",
    }])

    html = email_technical_dashboard.build_html()

    assert "技术项目洞察" in html and "Trending Repo" in html
    assert "500 stars today" in html and "Developer Tool" not in html
    assert "&lt;script&gt;" in html and "<script>alert(1)</script>" not in html


def test_technical_email_prefers_canonical_repository_events(monkeypatch):
    from services import repository_service
    monkeypatch.setattr(repository_service, "list_trending_repositories", lambda *_: {
        "source": "event_store", "items": [{
            "repo_name": "org/v2-project", "repo_url": "https://github.com/org/v2-project", "description": "Verified summary",
            "language": "Rust", "stars": "2k", "forks": "100", "today_stars": "220", "category": "daily",
            "entity_key": "github:org/v2-project", "event_id": 33,
                "scores": {"hot_score": {"stars_delta": 320}, "business_evaluation": {"total": 8.2, "d4": 7.5,
                    "recommendation": "验证落地", "summary": "适合评估", "technical_assessment": {
                        "engineering_maturity": {"score": 7, "reasoning": "有活跃贡献与发布", "evidence_keys": ["contributors_count", "latest_release_tag"]},
                        "innovation": {"score": None, "reasoning": "证据不足", "evidence_keys": []},
                        "deployability": {"score": 6, "reasoning": "公开许可证", "evidence_keys": ["license"]}}}},
            "pushed_at": "2026-10-22T10:00:00Z", "topics": ["agent", "mcp"],
            "contributors_count": 32, "latest_release": {"tag_name": "v1.4.0", "published_at": "2026-10-20T00:00:00Z", "major_release": True},
            "repository_metadata_available": True,
        }],
    })

    rows = email_technical_dashboard._rows()
    html = email_technical_dashboard.build_html()

    assert rows[0]["entity_key"] == "github:org/v2-project"
    assert rows[0]["total"] == 8.2
    assert rows[0]["reasoning"] == "适合评估"
    assert rows[0]["stars_delta"] == 320
    assert rows[0]["engineering_score"] == 7.5
    assert "工程交付评估（AI）</b> 7.5" in html
    assert "工程成熟度" in html and "贡献者" in html and "部署" in html
    assert "2026-10-22T10:00:00Z" in html
    assert "agent, mcp" in html
    assert "贡献者: 32" in html
    assert "v1.4.0" in html
    assert "重大版本" in html


def test_business_email_links_v2_focus_to_its_event_detail(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr("services.event_service.list_events", lambda *_: {"items": []})
    monkeypatch.setattr(email_dashboard, "settings", SimpleNamespace(BASE_URL="https://insight.example"))
    monkeypatch.setattr(email_dashboard, "current_analyses", lambda _: {"apps": {
        "analysis_version": 4, "judgment": "有新变化。", "focus": {
            "title": "New AI product", "url": "https://vendor.example/update", "event_id": 55,
            "meta": "Official", "why": "值得关注。", "analysis": "官方更新了产品。",
            "impact": "可能影响市场。", "caveat": "后续采用情况待核实。",
        }
    }})
    monkeypatch.setattr("services.radar_service.build_intelligence_radar", lambda _: {"events": []})

    html = email_dashboard.build_html()

    assert 'href="https://insight.example/events/55"' in html
    assert 'href="https://vendor.example/update"' in html


def test_business_email_uses_a_compact_shared_event_brief(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(email_dashboard, "settings", SimpleNamespace(BASE_URL="https://insight.example"))
    monkeypatch.setattr(email_dashboard, "current_analyses", lambda _: {"apps": {
        "focus": {"event_id": 55, "impact": "可能改变企业采购优先级。"}
    }})
    monkeypatch.setattr("services.event_service.list_events", lambda *_: {"items": [
        {"id": 55, "title": "New AI product", "summary": "Official launch", "business_scopes": ["ai_applications"],
         "scores": {"hot_score": {"value": 82}}, "source_count": 2, "evidence_count": 3},
        {"id": 56, "title": "New developer framework", "summary": "Release observed", "business_scopes": ["technology_ecosystem"],
         "scores": {}, "source_count": 1, "evidence_count": 1},
    ]})

    html = email_dashboard.build_html()

    assert "今日 AI 市场简报" in html
    assert 'href="https://insight.example/events/55"' in html
    assert "热度评分 82" in html and "2 个来源" in html and "3 条证据" in html
    assert "可能改变企业采购优先级。" in html
    assert "Overall assessment" not in html and "总体判断" not in html
