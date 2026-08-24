from datetime import datetime, timedelta

from services import email_service


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
    assert not email_service.subscriber_is_due(subscriber, monday.replace(hour=9, minute=6))
    assert not email_service.subscriber_is_due({**subscriber, "last_sent_at": monday}, monday)

    sent = []
    monkeypatch.setattr(email_service, "get_subscribers", lambda: [subscriber])
    monkeypatch.setattr(email_service, "build_daily_digest_html", lambda: "<html>exact-preview-html</html>")
    monkeypatch.setattr(email_service, "send_email", lambda email, subject, html: sent.append((email, html)) or True)

    class Cursor:
        def execute(self, *_):
            pass

    class Connection:
        def cursor(self):
            return Cursor()

    class Context:
        def __enter__(self):
            return Connection()

        def __exit__(self, *_):
            pass

    monkeypatch.setattr(email_service, "get_db", Context)
    assert email_service.send_scheduled_digests(monday) == {"sent": 1, "total": 1}
    assert sent == [("reader@example.com", "<html>exact-preview-html</html>")]
