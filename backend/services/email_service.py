"""
Email service
Encapsulates email sending, subscription management, and daily digest construction.
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Optional
from pytz import timezone
from bs4 import BeautifulSoup
from db import get_db
from settings import settings

logger = logging.getLogger(__name__)
SHANGHAI_TZ = timezone("Asia/Shanghai")


def get_subscribers() -> list:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM email_subscribers WHERE active = 1 ORDER BY id")
        rows = c.fetchall()
        return [dict(r) for r in rows]


def get_subscriber(subscriber_id: int) -> Optional[dict]:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM email_subscribers WHERE id = %s AND active = 1", (subscriber_id,))
        row = c.fetchone()
        return dict(row) if row else None


def add_subscriber(email: str, name: str = "", weekdays: Optional[list[int]] = None, send_time: str = "10:05", language: str = "zh") -> bool:
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO email_subscribers (email, name, weekdays, send_time, language)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                  name = EXCLUDED.name,
                  weekdays = EXCLUDED.weekdays,
                  send_time = EXCLUDED.send_time,
                  language = EXCLUDED.language,
                  active = 1
                """,
                (email, name, weekdays or list(range(7)), send_time, "en" if language == "en" else "zh"),
            )
        return True
    except Exception:
        return False


def update_subscriber(subscriber_id: int, weekdays: list[int], send_time: str, language: str = "zh") -> Optional[dict]:
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            UPDATE email_subscribers
            SET weekdays = %s, send_time = %s, language = %s
            WHERE id = %s AND active = 1
            RETURNING *
            """,
            (weekdays, send_time, "en" if language == "en" else "zh", subscriber_id),
        )
        row = c.fetchone()
        return dict(row) if row else None


def subscriber_is_due(subscriber: dict, now: datetime) -> bool:
    """One small, testable rule used by the minute scheduler."""
    if now.weekday() not in (subscriber.get("weekdays") or []):
        return False
    if now.strftime("%H:%M") < (subscriber.get("send_time") or "")[:5]:
        return False
    last_sent = subscriber.get("last_sent_at")
    if not last_sent:
        return True
    if last_sent.tzinfo is None:
        last_sent = SHANGHAI_TZ.localize(last_sent)
    return last_sent.astimezone(SHANGHAI_TZ).date() < now.date()


def daily_digest_ready(now: datetime) -> bool:
    """Wait for today's board analyses, with a late fallback if refresh fails."""
    from services.email_dashboard import BOARDS, current_analyses

    local = now.astimezone(SHANGHAI_TZ)
    if local.strftime("%H:%M") < "10:05":
        return False
    if set(current_analyses(local.date())) >= set(BOARDS):
        return True
    return local.strftime("%H:%M") >= "11:30"


def build_daily_digest_html(language: str = "zh") -> str:
    from services.email_dashboard import build_html
    return build_html(language)


def build_technical_digest_html(language: str = "zh") -> str:
    from services.email_technical_dashboard import build_html
    return build_html(language)


def build_digest_html(template: str, language: str = "zh") -> str:
    return build_technical_digest_html(language) if template == "technical" else build_daily_digest_html(language)


def _digest_messages(language: str, day: str) -> list[tuple[str, str]]:
    labels = (("商业洞察", "Business intelligence brief"), ("技术项目洞察", "Technical project brief"))
    builders = (build_daily_digest_html, build_technical_digest_html)
    return [(f"InsightPro · {labels[index][1] if language == 'en' else labels[index][0]} ({day})", builders[index](language))
            for index in range(2)]


def _sent_briefs(subscriber_id: int, day: str) -> set[str]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT delivery_type FROM email_delivery_attempts
                          WHERE subscriber_id=%s AND delivery_date=%s AND status='sent'""",
                       (subscriber_id, day))
        return {row["delivery_type"] for row in cursor.fetchall()}


def _record_brief_delivery(subscriber: dict, day: str, delivery_type: str, sent: bool) -> None:
    with get_db() as conn:
        conn.cursor().execute("""INSERT INTO email_delivery_attempts
            (subscriber_id,recipient_email,delivery_date,delivery_type,status,attempts,last_error,sent_at,updated_at)
            VALUES (%s,%s,%s,%s,%s,1,%s,CASE WHEN %s THEN NOW() END,NOW())
            ON CONFLICT (subscriber_id,delivery_date,delivery_type) DO UPDATE SET
              recipient_email=EXCLUDED.recipient_email,status=EXCLUDED.status,
              attempts=email_delivery_attempts.attempts+1,last_error=EXCLUDED.last_error,
              sent_at=CASE WHEN EXCLUDED.status='sent' THEN NOW() ELSE email_delivery_attempts.sent_at END,
              updated_at=NOW()""",
            (subscriber["id"], subscriber["email"], day, delivery_type,
             "sent" if sent else "failed", None if sent else "SMTP delivery failed", sent))


def send_email(to_addr: str, subject: str, html_content: str) -> bool:
    """Send email via SMTP"""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD or settings.SMTP_PASSWORD == "your-qq-auth-code-here":
        logger.warning("Email not configured: please set SMTP_PASSWORD in .env (QQ mail authorization code)")
        return False
    try:
        msg = MIMEMultipart("alternative")
        soup = BeautifulSoup(html_content, "html.parser")
        plain = soup.get_text(" ", strip=True)
        links = "\n".join(f'{link.get_text(" ", strip=True)}: {link["href"]}' for link in soup.find_all("a", href=True))
        msg.attach(MIMEText(f"{plain}\n\n{links}", "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        msg["Subject"] = subject
        msg["From"] = f"InsightPro <{settings.EMAIL_FROM}>"
        msg["To"] = to_addr
        msg["X-Mailer"] = "InsightPro"
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, [to_addr], msg.as_string())
        logger.info(f"Email sent successfully: {to_addr}")
        return True
    except Exception as e:
        logger.warning(f"Email send failed: {e}")
        return False


def send_subscriber_briefs(subscriber: dict, now: Optional[datetime] = None, skip_sent: bool = False,
                           messages: Optional[list[tuple[str, str]]] = None) -> dict:
    now = now or datetime.now(SHANGHAI_TZ)
    day = now.strftime("%Y-%m-%d")
    messages = messages or _digest_messages(subscriber.get("language", "zh"), day)
    sent_briefs = _sent_briefs(subscriber["id"], day) if skip_sent else set()
    deliveries = 0
    for delivery_type, (subject, html) in zip(("business", "technical"), messages):
        if delivery_type in sent_briefs:
            continue
        sent = send_email(subscriber["email"], subject, html)
        _record_brief_delivery(subscriber, day, delivery_type, sent)
        deliveries += int(sent)
        if sent:
            sent_briefs.add(delivery_type)
    success = {"business", "technical"}.issubset(sent_briefs)
    if success:
        with get_db() as conn:
            conn.cursor().execute("UPDATE email_subscribers SET last_sent_at=CURRENT_TIMESTAMP WHERE id=%s", (subscriber["id"],))
    return {"sent": int(success), "total": 1, "deliveries": deliveries}


def send_daily_digest():
    """Send the insights daily digest to all active subscribers immediately."""
    subscribers = get_subscribers()
    if not subscribers:
        if settings.EMAIL_TO:
            subscribers = [{"email": settings.EMAIL_TO, "name": ""}]
        else:
            logger.info("No email subscribers, skipping send")
            return

    success = 0
    deliveries = 0
    html_by_language = {}
    for sub in subscribers:
        language = sub.get("language", "zh")
        now = datetime.now(SHANGHAI_TZ)
        today = now.strftime("%Y-%m-%d")
        if language not in html_by_language:
            html_by_language[language] = _digest_messages(language, today)
        if sub.get("id") is None:
            results = [send_email(sub["email"], subject, html) for subject, html in html_by_language[language]]
            success += int(all(results))
            deliveries += sum(results)
        else:
            result = send_subscriber_briefs(sub, now, skip_sent=False, messages=html_by_language[language])
            success += result["sent"]
            deliveries += result["deliveries"]
    logger.info(f"Daily email send completed: {success}/{len(subscribers)} subscribers received both briefs")
    return {"sent": success, "total": len(subscribers), "deliveries": deliveries}


def send_scheduled_digests(now: Optional[datetime] = None):
    """Scan every minute, delivering only to subscribers currently due and not yet sent today."""
    now = now or datetime.now(SHANGHAI_TZ)
    due = [subscriber for subscriber in get_subscribers() if subscriber_is_due(subscriber, now)]
    if not due:
        return {"sent": 0, "total": 0}
    if not daily_digest_ready(now):
        logger.info("Intelligence brief delayed: no recent radar events")
        return {"sent": 0, "total": 0}

    success = 0
    deliveries = 0
    html_by_language = {}
    for subscriber in due:
        language = subscriber.get("language", "zh")
        if language not in html_by_language:
            html_by_language[language] = _digest_messages(language, now.strftime("%Y-%m-%d"))
        day = now.date().isoformat()
        result = send_subscriber_briefs(subscriber, now, skip_sent=True, messages=html_by_language[language])
        deliveries += result["deliveries"]
        success += result["sent"]
    logger.info(f"Subscription email send completed: {success}/{len(due)} successful")
    return {"sent": success, "total": len(due), "deliveries": deliveries}
