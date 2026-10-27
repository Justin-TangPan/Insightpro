"""
Email service
Encapsulates email sending, subscription management, and daily digest construction.
"""
import smtplib
import logging
import uuid
import json
from psycopg2.extras import Json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from datetime import datetime
from typing import Optional
from pytz import timezone
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from db import get_db
from settings import settings

logger = logging.getLogger(__name__)
SHANGHAI_TZ = timezone("Asia/Shanghai")


def get_subscribers() -> list:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""SELECT r.*, COALESCE(json_agg(json_build_object(
            'id',s.id,'email_type',s.email_type,'enabled',s.enabled,'weekdays',s.weekdays,
            'send_time',s.send_time,'timezone',s.timezone) ORDER BY s.email_type)
            FILTER (WHERE s.id IS NOT NULL),'[]'::json) AS subscriptions
            FROM email_subscribers r LEFT JOIN email_subscriptions s ON s.recipient_id=r.id
            WHERE r.active=1 GROUP BY r.id ORDER BY r.id""")
        rows = c.fetchall()
        return [dict(r) for r in rows]


def get_subscriber(subscriber_id: int) -> Optional[dict]:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""SELECT r.*, COALESCE(json_agg(json_build_object(
            'id',s.id,'email_type',s.email_type,'enabled',s.enabled,'weekdays',s.weekdays,
            'send_time',s.send_time,'timezone',s.timezone)) FILTER (WHERE s.id IS NOT NULL),'[]'::json) AS subscriptions
            FROM email_subscribers r LEFT JOIN email_subscriptions s ON s.recipient_id=r.id
            WHERE r.id=%s AND r.active=1 GROUP BY r.id""", (subscriber_id,))
        row = c.fetchone()
        return dict(row) if row else None


def add_subscriber(email: str, name: str = "", weekdays: Optional[list[int]] = None, send_time: str = "10:05", language: str = "zh", email_types: tuple[str, ...] = ("business", "technical")) -> bool:
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
            c.execute("SELECT id FROM email_subscribers WHERE email=%s", (email,))
            recipient_id = c.fetchone()["id"]
            for kind in email_types:
                c.execute("""INSERT INTO email_subscriptions (recipient_id,email_type,enabled,weekdays,send_time)
                    VALUES (%s,%s,TRUE,%s,%s) ON CONFLICT (recipient_id,email_type) DO UPDATE SET enabled=TRUE""",
                    (recipient_id, kind, weekdays or list(range(7)), send_time))
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
        if row:
            c.execute("UPDATE email_subscriptions SET weekdays=%s,send_time=%s WHERE recipient_id=%s", (weekdays, send_time, subscriber_id))
        return dict(row) if row else None


def update_subscription(recipient_id: int, email_type: str, enabled: bool, weekdays: list[int], send_time: str, tz_name: str) -> Optional[dict]:
    ZoneInfo(tz_name)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO email_subscriptions (recipient_id,email_type,enabled,weekdays,send_time,timezone)
            SELECT id,%s,%s,%s,%s,%s FROM email_subscribers WHERE id=%s AND active=1
            ON CONFLICT (recipient_id,email_type) DO UPDATE SET enabled=EXCLUDED.enabled,
            weekdays=EXCLUDED.weekdays,send_time=EXCLUDED.send_time,timezone=EXCLUDED.timezone RETURNING *""",
            (email_type, enabled, weekdays, send_time, tz_name, recipient_id))
        row = cursor.fetchone()
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
    """The homepage radar can be mailed once the scheduled delivery window opens."""
    return now.astimezone(SHANGHAI_TZ).strftime("%H:%M") >= "10:05"


def build_daily_digest_html(language: str = "zh") -> str:
    from services.email_dashboard import build_html
    return build_html(language)


def create_email_snapshot(email_type: str, language: str = "zh") -> tuple[str, str]:
    if email_type == "business":
        from services.email_dashboard import build_html, homepage_snapshot
        from services.daily_ai_brief_service import read
        data = homepage_snapshot()
        brief = read()
        if brief.get("date") != datetime.now(SHANGHAI_TZ).date().isoformat() or brief.get("status") != "success" or not (brief.get("headline") or brief.get("quick_reads")):
            raise ValueError("今日每日 AI 洞察简讯尚未成功生成，商业邮件等待发送")
        data["_daily_ai_brief"] = brief
        html = build_html(language, data)
    elif email_type == "technical":
        from services.email_technical_dashboard import build_html, _rows
        data = _rows()
        html = build_html(language, data)
    else:
        raise ValueError("Unknown email type")
    snapshot_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.cursor().execute("""INSERT INTO email_content_snapshots
            (id, language, homepage_data, html, email_type, source_snapshot)
            VALUES (%s,%s,%s,%s,%s,%s)""", (snapshot_id, language, Json(data, dumps=lambda value: json.dumps(value, default=str)), html, email_type, Json(data, dumps=lambda value: json.dumps(value, default=str))))
    return snapshot_id, html


def create_business_snapshot(language: str = "zh") -> tuple[str, str]:
    return create_email_snapshot("business", language)


def get_business_snapshot(snapshot_id: str) -> Optional[dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, language, html, homepage_data, email_type FROM email_content_snapshots WHERE id=%s", (snapshot_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def build_technical_digest_html(language: str = "zh") -> str:
    from services.email_technical_dashboard import build_html
    return build_html(language)


def build_digest_html(template: str, language: str = "zh") -> str:
    return build_technical_digest_html(language) if template == "technical" else build_daily_digest_html(language)


def _subject(email_type: str, language: str, day: str) -> str:
    labels = {"business": ("商业洞察", "Business intelligence"),
              "technical": ("技术项目", "Technical projects")}
    label = labels[email_type][1 if language == "en" else 0]
    return f"小雷达 · {label} ({day})"


def _sent_briefs(subscriber_id: int, day: str) -> set[str]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT delivery_type FROM email_delivery_attempts
                          WHERE subscriber_id=%s AND delivery_date=%s AND status='sent'""",
                       (subscriber_id, day))
        return {row["delivery_type"] for row in cursor.fetchall()}


def _record_brief_delivery(subscriber: dict, day: str, delivery_type: str, sent: bool,
                           snapshot_id: str, subscription_id: int) -> None:
    with get_db() as conn:
        conn.cursor().execute("""INSERT INTO email_delivery_attempts
            (subscriber_id,recipient_email,delivery_date,delivery_type,status,attempts,last_error,sent_at,updated_at,snapshot_id,subscription_id)
            VALUES (%s,%s,%s,%s,%s,1,%s,CASE WHEN %s THEN NOW() END,NOW(),%s,%s)
            ON CONFLICT (subscriber_id,delivery_date,delivery_type) DO UPDATE SET
              recipient_email=EXCLUDED.recipient_email,status=EXCLUDED.status,
              attempts=email_delivery_attempts.attempts+1,last_error=EXCLUDED.last_error,
              snapshot_id=EXCLUDED.snapshot_id,subscription_id=EXCLUDED.subscription_id,
              sent_at=CASE WHEN EXCLUDED.status='sent' THEN NOW() ELSE email_delivery_attempts.sent_at END,
              updated_at=NOW()""",
            (subscriber["id"], subscriber["email"], day, delivery_type,
             "sent" if sent else "failed", None if sent else "SMTP delivery failed", sent, snapshot_id, subscription_id))


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
        msg["From"] = formataddr((str(Header("小雷达", "utf-8")), settings.EMAIL_FROM))
        msg["To"] = to_addr
        msg["X-Mailer"] = "小雷达"
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, [to_addr], msg.as_string())
        logger.info(f"Email sent successfully: {to_addr}")
        return True
    except Exception as e:
        logger.warning(f"Email send failed: {e}")
        return False


def _subscription_due(subscription: dict, now: datetime) -> bool:
    if not subscription["enabled"]:
        return False
    local = now.astimezone(ZoneInfo(subscription["timezone"]))
    return local.weekday() in subscription["weekdays"] and local.strftime("%H:%M") >= subscription["send_time"]


def send_subscriber_briefs(subscriber: dict, now: Optional[datetime] = None, skip_sent: bool = False,
                           snapshot_id: Optional[str] = None, email_type: Optional[str] = None) -> dict:
    now = now or datetime.now(SHANGHAI_TZ)
    day = now.astimezone(SHANGHAI_TZ).date().isoformat()
    subscriptions = [sub for sub in subscriber.get("subscriptions", [])
                     if sub["enabled"] and (email_type is None or sub["email_type"] == email_type)]
    if email_type and not subscriptions:
        raise ValueError("Recipient has no enabled subscription for this email type")
    selected = get_business_snapshot(snapshot_id) if snapshot_id else None
    if snapshot_id and (not selected or selected["language"] != subscriber.get("language", "zh")
                        or (email_type and selected["email_type"] != email_type)):
        raise ValueError("Preview snapshot is unavailable or does not match the subscription")
    if snapshot_id and not email_type:
        subscriptions = [sub for sub in subscriptions if sub["email_type"] == selected["email_type"]]
    if snapshot_id and not subscriptions:
        raise ValueError("Recipient is not subscribed to this preview type")
    sent_briefs = _sent_briefs(subscriber["id"], day) if skip_sent else set()
    deliveries = 0
    blocked = 0
    for sub in subscriptions:
        kind = sub["email_type"]
        if kind in sent_briefs:
            continue
        current_brief = None
        if kind == "business":
            from services.daily_ai_brief_service import read
            current_brief = read(day)
            if current_brief.get("date") != day or current_brief.get("status") != "success" or not (current_brief.get("headline") or current_brief.get("quick_reads")):
                blocked += 1
                logger.warning("Business email blocked: today's daily AI brief is unavailable for %s", day)
                continue
        if selected:
            if kind == "business" and (selected.get("homepage_data") or {}).get("_daily_ai_brief", {}).get("version") != current_brief["version"]:
                raise ValueError("Preview uses an outdated daily AI brief version")
            chosen_id, html = snapshot_id, selected["html"]
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""SELECT snapshot_id FROM email_delivery_attempts
                    WHERE subscriber_id=%s AND delivery_date=%s AND delivery_type=%s AND status='failed'""",
                    (subscriber["id"], day, kind))
                previous = cursor.fetchone()
            stored = get_business_snapshot(previous["snapshot_id"]) if previous and previous.get("snapshot_id") else None
            if stored and (kind != "business" or (stored.get("homepage_data") or {}).get("_daily_ai_brief", {}).get("version") == current_brief["version"]):
                chosen_id, html = stored["id"], stored["html"]
            else:
                chosen_id, html = create_email_snapshot(kind, subscriber.get("language", "zh"))
        if kind == "business":
            from services.daily_ai_brief_service import mark_email_status
            mark_email_status(day, current_brief["version"], "发送中")
        sent = send_email(subscriber["email"], _subject(kind, subscriber.get("language", "zh"), day), html)
        _record_brief_delivery(subscriber, day, kind, sent, chosen_id, sub["id"])
        if kind == "business":
            try:
                mark_email_status(day, current_brief["version"], "发送成功" if sent else "发送失败", None if sent else "SMTP delivery failed")
            except Exception as exc:  # email status is auxiliary; never break delivery.
                logger.warning("Could not record daily brief email status: %s", exc)
        deliveries += int(sent)
        if sent:
            sent_briefs.add(kind)
    return {"sent": int(bool(subscriptions) and all(sub["email_type"] in sent_briefs for sub in subscriptions)),
            "total": 1, "deliveries": deliveries, **({"blocked": blocked} if blocked else {})}


def send_daily_digest():
    subscribers = get_subscribers()
    results = [send_subscriber_briefs(subscriber) for subscriber in subscribers]
    return {"sent": sum(row["sent"] for row in results), "total": len(results),
            "deliveries": sum(row["deliveries"] for row in results)}


def retry_business_emails() -> dict:
    day = datetime.now(SHANGHAI_TZ).date().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT subscriber_id FROM email_delivery_attempts WHERE delivery_date=%s AND delivery_type='business' AND status='failed'",
            (day,),
        )
        failed_ids = {row["subscriber_id"] for row in cursor.fetchall()}
    results = [send_subscriber_briefs(subscriber, skip_sent=True, email_type="business")
               for subscriber in get_subscribers()
               if subscriber["id"] in failed_ids and any(sub["email_type"] == "business" and sub["enabled"] for sub in subscriber.get("subscriptions", []))]
    blocked = sum(row.get("blocked", 0) for row in results)
    return {"sent": sum(row["sent"] for row in results), "total": len(results),
            "deliveries": sum(row["deliveries"] for row in results),
            **({"status": "blocked", "blocked": blocked, "error": "今日每日 AI 洞察简讯尚未生成，商业邮件等待发送"} if blocked else {})}


def send_scheduled_digests(now: Optional[datetime] = None):
    now = now or datetime.now(SHANGHAI_TZ)
    sent = total = deliveries = blocked = 0
    for subscriber in get_subscribers():
        for sub in subscriber.get("subscriptions", []):
            if not _subscription_due(sub, now):
                continue
            total += 1
            result = send_subscriber_briefs(subscriber, now, skip_sent=True, email_type=sub["email_type"])
            sent += result["sent"]
            deliveries += result["deliveries"]
            blocked += result.get("blocked", 0)
    return {"sent": sent, "total": total, "deliveries": deliveries, **({"status": "blocked", "blocked": blocked, "error": "今日每日 AI 洞察简讯尚未生成，商业邮件等待发送"} if blocked else {})}
