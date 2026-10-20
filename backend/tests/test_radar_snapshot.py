from datetime import date, datetime

from services import radar_service
from services import email_service
from services import agent_launch_service


def test_snapshot_counts_and_email_share_five_directions(monkeypatch):
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
    monkeypatch.setattr(radar_service, "build_radar_snapshot", lambda: snapshot)
    html = email_service.build_daily_digest_html()
    assert "<svg" not in html and "background:#ffffff" in html
    assert "Browser Agent launch" in html
    assert len(snapshot["top_signals"]) == 1
    assert "进入 InsightPro 查看完整 AI Radar" in html
    snapshot["apps"] = [{"title": "Bee", "url": "https://www.producthunt.com/products/bee", "day": "2026-10-18",
                         "summary": "个人 AI 记忆应用。", "tagline": "Personal AI memory", "why": "关注记忆体验。"}]
    html = email_service.build_daily_digest_html()
    assert "Bee" in html and "建议验证" in html


def test_digest_waits_for_radar_signal(monkeypatch):
    monkeypatch.setattr(radar_service, "build_radar_snapshot", lambda _: {"today_count": 0})
    now = email_service.SHANGHAI_TZ.localize(datetime(2026, 10, 19, 9, 5))
    assert not email_service.daily_digest_ready(now)
    monkeypatch.setattr(radar_service, "build_radar_snapshot", lambda _: {"today_count": 1})
    assert email_service.daily_digest_ready(now)


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
