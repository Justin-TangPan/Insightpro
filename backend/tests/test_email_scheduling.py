from datetime import datetime
from email import message_from_string

from services import email_dashboard, email_service, email_technical_dashboard


def test_smtp_sender_header_is_rfc_encoded(monkeypatch):
    sent = []
    class SMTP:
        def __init__(self, *_, **__): pass
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def login(self, *_): pass
        def sendmail(self, sender, recipients, message): sent.append((sender, message))
    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", SMTP)
    monkeypatch.setattr(email_service.settings, "SMTP_USER", "sender@example.com")
    monkeypatch.setattr(email_service.settings, "SMTP_PASSWORD", "test-password")
    monkeypatch.setattr(email_service.settings, "EMAIL_FROM", "sender@example.com")
    assert email_service.send_email("reader@example.com", "Test", "<p>hello</p>")
    sender, message = sent[0]
    assert sender == "sender@example.com"
    assert message_from_string(message)["From"].startswith("=?utf-8?")


def _sub(kind, ident, weekdays, send_time, tz="Asia/Shanghai", enabled=True):
    return {"id": ident, "email_type": kind, "weekdays": weekdays, "send_time": send_time,
            "timezone": tz, "enabled": enabled}


def test_independent_schedules_and_disabled_briefs():
    now = email_service.SHANGHAI_TZ.localize(datetime(2026, 8, 24, 8, 30))
    assert email_service._subscription_due(_sub("business", 1, [0], "08:30"), now)
    assert not email_service._subscription_due(_sub("technical", 2, [0, 2, 4], "09:00"), now)
    assert not email_service._subscription_due(_sub("business", 1, [0], "08:30", enabled=False), now)
    assert email_service._subscription_due(_sub("technical", 2, [6], "14:30", "Pacific/Honolulu"), now)


def test_selected_preview_sends_only_its_exact_html(monkeypatch):
    subscriber = {"id": 9, "email": "reader@example.com", "language": "zh",
                  "subscriptions": [_sub("business", 1, [0], "08:30"), _sub("technical", 2, [0], "09:00")]}
    sent = []
    monkeypatch.setattr(email_service, "get_business_snapshot", lambda _: {"id": "preview", "language": "zh", "email_type": "technical", "html": "<h1>Previewed</h1>"})
    monkeypatch.setattr(email_service, "send_email", lambda email, subject, html: sent.append(html) or True)
    monkeypatch.setattr(email_service, "_record_brief_delivery", lambda *args: None)
    result = email_service.send_subscriber_briefs(subscriber, snapshot_id="preview", email_type="technical")
    assert result["deliveries"] == 1
    assert sent == ["<h1>Previewed</h1>"]


def test_scheduler_sends_each_type_on_its_own_day(monkeypatch):
    now = email_service.SHANGHAI_TZ.localize(datetime(2026, 8, 24, 8, 30))
    subscriber = {"id": 1, "email": "reader@example.com", "language": "zh",
                  "subscriptions": [_sub("business", 1, [0], "08:30"), _sub("technical", 2, [0, 2, 4], "09:00")]}
    sent = []
    monkeypatch.setattr(email_service, "get_subscribers", lambda: [subscriber])
    monkeypatch.setattr(email_service, "_sent_briefs", lambda *_: set())
    monkeypatch.setattr(email_service, "create_email_snapshot", lambda kind, language: (kind, f"<{kind}>"))
    monkeypatch.setattr(email_service, "send_email", lambda email, subject, html: sent.append(html) or True)
    monkeypatch.setattr(email_service, "_record_brief_delivery", lambda *args: None)
    monkeypatch.setattr("services.daily_ai_brief_service.read", lambda *_: {"date": "2026-08-24", "version": 1, "status": "success", "headline": {"title": "发布新模型"}})
    monkeypatch.setattr("services.daily_ai_brief_service.mark_email_status", lambda *args: None)

    class Cursor:
        def execute(self, *_): pass
        def fetchone(self): return None
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(email_service, "get_db", Connection)
    assert email_service.send_scheduled_digests(now) == {"sent": 1, "total": 1, "deliveries": 1}
    assert sent == ["<business>"]


def test_business_email_waits_when_only_previous_day_brief_exists(monkeypatch):
    now = email_service.SHANGHAI_TZ.localize(datetime(2026, 8, 24, 10, 5))
    subscriber = {"id": 1, "email": "reader@example.com", "language": "zh",
                  "subscriptions": [_sub("business", 1, [0], "10:05")]}
    monkeypatch.setattr(email_service, "get_subscribers", lambda: [subscriber])
    monkeypatch.setattr(email_service, "_sent_briefs", lambda *_: set())
    monkeypatch.setattr("services.daily_ai_brief_service.read", lambda *_: {"date": "2026-08-23", "version": 3, "status": "success", "headline": {"title": "旧头条"}})
    monkeypatch.setattr(email_service, "send_email", lambda *_: (_ for _ in ()).throw(AssertionError("sent stale brief")))
    result = email_service.send_scheduled_digests(now)
    assert result["status"] == "blocked" and result["blocked"] == 1


def test_retry_business_email_only_targets_failed_deliveries(monkeypatch):
    class Cursor:
        def execute(self, *_): pass
        def fetchall(self): return [{"subscriber_id": 2}]
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    subscribers = [{"id": ident, "subscriptions": [_sub("business", ident, [0], "10:05")]} for ident in (1, 2)]
    sent = []
    monkeypatch.setattr(email_service, "get_db", Connection)
    monkeypatch.setattr(email_service, "get_subscribers", lambda: subscribers)
    monkeypatch.setattr(email_service, "send_subscriber_briefs", lambda subscriber, **_: sent.append(subscriber["id"]) or {"sent": 1, "total": 1, "deliveries": 1})
    assert email_service.retry_business_emails()["deliveries"] == 1
    assert sent == [2]


def test_retry_reuses_failed_html_snapshot(monkeypatch):
    subscriber = {"id": 2, "email": "retry@example.com", "language": "zh",
                  "subscriptions": [_sub("technical", 2, [0], "09:00")]}
    sent = []
    monkeypatch.setattr(email_service, "_sent_briefs", lambda *_: set())
    monkeypatch.setattr(email_service, "get_business_snapshot", lambda _: {"id": "failed-id", "html": "<stored>"})
    monkeypatch.setattr(email_service, "create_email_snapshot", lambda *_: (_ for _ in ()).throw(AssertionError("rebuilt")))
    monkeypatch.setattr(email_service, "send_email", lambda email, subject, html: sent.append(html) or True)
    monkeypatch.setattr(email_service, "_record_brief_delivery", lambda *args: None)
    class Cursor:
        def execute(self, *_): pass
        def fetchone(self): return {"snapshot_id": "failed-id"}
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(email_service, "get_db", Connection)
    assert email_service.send_subscriber_briefs(subscriber, skip_sent=True)["deliveries"] == 1
    assert sent == ["<stored>"]


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
    from services import page_snapshot_service
    monkeypatch.setattr(page_snapshot_service, "get_page_snapshot", lambda *_: {"content": {
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
    }})

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


def test_business_email_links_homepage_focus(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(email_dashboard, "settings", SimpleNamespace(BASE_URL="https://insight.example"))
    snapshot = {"as_of": "2026-10-25T10:05:00+08:00", "focus": {"event": {"id": "event:55", "title": "New AI product", "sources": []}},
                "keypoints": [], "insights": [], "boards": [], "vendors": [], "latest": []}
    html = email_dashboard.build_html(snapshot=snapshot)
    assert 'href="https://insight.example/events/55"' in html
