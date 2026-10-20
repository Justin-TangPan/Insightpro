"""
Email service
Encapsulates email sending, subscription management, and daily digest construction.
"""
import smtplib
import logging
from html import escape
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


def add_subscriber(email: str, name: str = "", weekdays: Optional[list[int]] = None, send_time: str = "09:05", language: str = "zh") -> bool:
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
    """Send after today's Radar has at least one collected signal."""
    from services.radar_service import build_radar_snapshot
    return build_radar_snapshot(now.astimezone(SHANGHAI_TZ).date())["today_count"] > 0


def build_daily_digest_html(language: str = "zh") -> str:
    """Compact, email-safe Radar Snapshot shared with the homepage."""
    from services.radar_service import build_radar_snapshot

    en = language == "en"
    snapshot = build_radar_snapshot()
    base_url = settings.BASE_URL.rstrip("/")
    categories = snapshot["categories"]
    max_count = max((item["current"] for item in categories), default=0) or 1
    rising = [item["name"] for item in categories if item["direction"] == "↑"]
    radar_rows = "".join(
        f'<tr><td style="padding:7px 8px 7px 0;color:#50606a;font-size:12px;width:105px">{escape(item["name"])}</td>'
        f'<td style="padding:7px 4px;width:220px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td style="background:#e7ecea;height:9px"><div style="background:#78958c;width:{round(item["current"] / max_count * 100)}%;height:9px"></div></td></tr></table></td>'
        f'<td style="padding:7px 0 7px 8px;color:#283a38;font-size:12px;white-space:nowrap;text-align:right">{item["current"]} &nbsp;{item["direction"]}</td></tr>'
        for item in categories
    )
    signals = "".join(
        f'<tr><td style="padding:13px 0;border-top:1px solid #e2e7e8"><span style="color:#4f6c62;font-size:11px">{escape(item["category"])} · {escape(str(item["source"]))}</span>'
        f'<p style="margin:5px 0;font-size:15px;font-weight:bold;color:#1c2529">{escape(item["title"])}</p>'
        f'<p style="margin:0;font-size:12px;line-height:1.6;color:#50606a">{escape(item["summary"][:85] + ("…" if len(item["summary"]) > 85 else "") or ("Brief pending" if en else "一句话解读待补充"))}</p>'
        f'<a href="{escape(item["url"] or base_url, quote=True)}" style="display:inline-block;margin-top:6px;color:#607a72;font-size:12px">{"Read source" if en else "查看来源"}</a></td></tr>'
        for item in snapshot["top_signals"][:3]
    ) or f'<tr><td style="padding:12px 0;color:#70808a;font-size:12px">{"No vendor launch signal matched this sample" if en else "本期暂无符合筛选条件的厂商发布线索"}</td></tr>'
    apps = "".join(
        f'<tr><td style="padding:13px 0;border-top:1px solid #e2e7e8"><a href="{escape(app["url"], quote=True)}" style="font-size:15px;font-weight:bold;color:#607a72;text-decoration:none">{escape(app["title"])}</a>'
        f'<span style="margin-left:8px;font-size:11px;color:#78858b">Product Hunt · {escape(app["day"])}</span>'
        f'<p style="margin:5px 0;color:#1c2529;font-size:12px;line-height:1.6">{escape(app["tagline"] if en else app["summary"])}</p>'
        f'<p style="margin:0;color:#70808a;font-size:11px;line-height:1.5">{escape(app["tagline"] if not en else app["why"])}</p></td></tr>'
        for app in snapshot["apps"][:2]
    ) or f'<tr><td style="padding:12px 0;color:#70808a;font-size:12px">{"No recent AI app matched the discovery criteria" if en else "本期暂无符合条件的新 AI 应用线索"}</td></tr>'
    focus = snapshot["apps"][0] if snapshot["apps"] else None
    next_step = (f'{"Check" if en else "建议验证"} {escape(focus["title"])}: {escape(focus["why"])}' if focus
                 else ("Review the source evidence before taking action." if en else "建议先核实来源，再决定是否跟进。"))
    title = "AI Radar · Daily Brief" if en else "AI Radar · 今日简报"
    return f'''<!doctype html><html lang="{"en" if en else "zh-CN"}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;background:#f5f6f7;color:#1c2529;font-family:Arial,'Microsoft YaHei',sans-serif"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f6f7"><tr><td align="center" style="padding:20px 10px"><table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background:#ffffff;border:1px solid #e2e7e8"><tr><td style="padding:27px 28px 22px;border-bottom:3px solid #78958c"><p style="margin:0 0 7px;color:#4f6c62;font-size:11px;font-weight:bold;letter-spacing:1px">INSIGHTPRO / {snapshot["as_of"]}</p><h1 style="margin:0;font-size:24px;line-height:1.3;color:#1c2529">{title}</h1></td></tr><tr><td style="padding:22px 28px"><p style="margin:0 0 16px;color:#596771;font-size:12px">{"Collected today" if en else "今日采集"} <b style="color:#1c2529">{snapshot["today_count"]}</b> &nbsp;·&nbsp; {"New AI apps" if en else "本周新应用"} <b style="color:#1c2529">{len(snapshot["apps"])}</b> &nbsp;·&nbsp; {"Rising directions" if en else "升温方向"} <b style="color:#1c2529">{len(rising)}</b></p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f2f4f5;border:1px solid #e2e7e8"><tr><td style="padding:15px"><p style="margin:0 0 7px;font-size:14px;font-weight:bold;color:#283a38">{"Small AI Radar" if en else "AI 热点小雷达"}</p><p style="margin:0 0 10px;font-size:11px;color:#70808a">{"Source signal volume · last 7 days versus prior 7 days" if en else "已采集信号量 · 近 7 天对比前 7 天"}</p><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{radar_rows}</table></td></tr></table>
<p style="margin:18px 0 4px;font-size:12px;color:#50606a">{"Rising:" if en else "本周升温："} {escape('、'.join(rising) if rising else ('None clearly detected' if en else '暂无明显升温方向'))}</p><h2 style="margin:24px 0 8px;font-size:17px;color:#1c2529">{"New AI app discovery" if en else "新 AI 应用发现"}</h2><p style="margin:0 0 6px;font-size:11px;color:#78858b">Product Hunt · {"External launch feed" if en else "独立发布线索"}</p><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{apps}</table><h2 style="margin:24px 0 8px;font-size:17px;color:#1c2529">{"Vendor launch signals" if en else "厂商产品发布信号"}</h2><p style="margin:0 0 6px;font-size:11px;color:#78858b">{"Existing competitor feed" if en else "现有友商动态采集"}</p><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{signals}</table><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:22px;background:#e7eeeb"><tr><td style="padding:15px;color:#283a38;font-size:12px;line-height:1.6"><b>{"Suggested next step" if en else "建议下一步"}</b><br>{next_step}</td></tr></table><p style="margin:20px 0 4px"><a href="{escape(base_url, quote=True)}" style="display:inline-block;padding:12px 18px;background:#607a72;color:#ffffff;font-size:13px;text-decoration:none">{"Open the full AI Radar" if en else "进入 InsightPro 查看完整 AI Radar"}</a></p><p style="margin:14px 0 0;font-size:11px;line-height:1.5;color:#78858b">{"Product Hunt launch is discovery evidence, not user growth proof. Source signals are not yet clustered events." if en else "产品发布是发现线索，不代表用户增长；来源信号尚未完成跨来源事件聚类。"}</p></td></tr></table></td></tr></table></body></html>'''


def send_email(to_addr: str, subject: str, html_content: str) -> bool:
    """Send email via SMTP"""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD or settings.SMTP_PASSWORD == "your-qq-auth-code-here":
        logger.warning("Email not configured: please set SMTP_PASSWORD in .env (QQ mail authorization code)")
        return False
    try:
        msg = MIMEMultipart("alternative")
        plain = BeautifulSoup(html_content, "html.parser").get_text(" ", strip=True)
        msg.attach(MIMEText(f"{plain}\n\n{settings.BASE_URL.rstrip('/')}", "plain", "utf-8"))
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
    for sub in subscribers:
        language = sub.get("language", "zh")
        today = datetime.now().strftime("%Y-%m-%d")
        html = build_daily_digest_html(language)
        subject = f"InsightPro · AI Radar {'Daily Snapshot' if language == 'en' else '每日快照'} ({today})"
        if send_email(sub["email"], subject, html):
            success += 1
    logger.info(f"Daily email send completed: {success}/{len(subscribers)} successful")
    return {"sent": success, "total": len(subscribers)}


def send_scheduled_digests(now: Optional[datetime] = None):
    """Scan every minute, delivering only to subscribers currently due and not yet sent today."""
    now = now or datetime.now(SHANGHAI_TZ)
    due = [subscriber for subscriber in get_subscribers() if subscriber_is_due(subscriber, now)]
    if not due:
        return {"sent": 0, "total": 0}
    if not daily_digest_ready(now):
        logger.info("Daily Radar Snapshot delayed: no signals collected today")
        return {"sent": 0, "total": 0}

    success = 0
    for subscriber in due:
        language = subscriber.get("language", "zh")
        html = build_daily_digest_html(language)
        subject = f"InsightPro · AI Radar {'Daily Snapshot' if language == 'en' else '每日快照'} ({now:%Y-%m-%d})"
        if not send_email(subscriber["email"], subject, html):
            continue
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE email_subscribers SET last_sent_at = CURRENT_TIMESTAMP WHERE id = %s",
                (subscriber["id"],),
            )
        success += 1
    logger.info(f"Subscription email send completed: {success}/{len(due)} successful")
    return {"sent": success, "total": len(due)}
