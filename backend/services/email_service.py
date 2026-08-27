"""
邮件服务
封装邮件发送、订阅管理、每日摘要构建功能。
"""
import smtplib
from html import escape
from email.mime.text import MIMEText
from datetime import datetime
from typing import Optional
from pytz import timezone
from db import get_db
from settings import settings

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


def add_subscriber(email: str, name: str = "", weekdays: Optional[list[int]] = None, send_time: str = "09:05") -> bool:
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO email_subscribers (email, name, weekdays, send_time)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                  name = EXCLUDED.name,
                  weekdays = EXCLUDED.weekdays,
                  send_time = EXCLUDED.send_time,
                  active = 1
                """,
                (email, name, weekdays or list(range(7)), send_time),
            )
        return True
    except Exception:
        return False


def update_subscriber(subscriber_id: int, weekdays: list[int], send_time: str) -> Optional[dict]:
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """
            UPDATE email_subscribers
            SET weekdays = %s, send_time = %s
            WHERE id = %s AND active = 1
            RETURNING *
            """,
            (weekdays, send_time, subscriber_id),
        )
        row = c.fetchone()
        return dict(row) if row else None


def subscriber_is_due(subscriber: dict, now: datetime) -> bool:
    """One small, testable rule used by the minute scheduler."""
    if now.weekday() not in (subscriber.get("weekdays") or []):
        return False
    if (subscriber.get("send_time") or "")[:5] != now.strftime("%H:%M"):
        return False
    last_sent = subscriber.get("last_sent_at")
    if not last_sent:
        return True
    if last_sent.tzinfo is None:
        last_sent = SHANGHAI_TZ.localize(last_sent)
    return last_sent.astimezone(SHANGHAI_TZ).date() < now.date()


def build_daily_digest_html() -> str:
    """构建技术解决方案日报：方案变化 + 技术热点 + 厂商动态。"""
    BASE_URL = settings.BASE_URL
    today = datetime.now().strftime("%Y-%m-%d")
    today_cn = datetime.now().strftime("%Y年%m月%d日")
    weekday = ["周一","周二","周三","周四","周五","周六","周日"][datetime.now().weekday()]

    github_items = []
    eval_items = []
    comp_news = []
    solution_items = []
    solution_total = 0
    solution_new = 0
    solution_updated = 0
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM github_trending WHERE scrape_date = %s AND category = 'daily' ORDER BY id LIMIT 8", (today,))
            github_items = [dict(r) for r in c.fetchall()]
            c.execute("SELECT * FROM trending_business_eval WHERE scrape_date = %s ORDER BY total DESC LIMIT 5", (today,))
            eval_items = [dict(r) for r in c.fetchall()]
            c.execute("SELECT * FROM competitor_news WHERE scrape_date = %s ORDER BY id", (today,))
            comp_news = [dict(r) for r in c.fetchall()]
            c.execute("SELECT COUNT(*)::int AS count FROM aliyun_solutions WHERE is_active=TRUE")
            solution_total = c.fetchone()["count"]
            c.execute(
                """SELECT
                     COUNT(*) FILTER (WHERE first_seen_date=%s)::int AS new_count,
                     COUNT(*) FILTER (WHERE last_changed_date=%s AND first_seen_date<>last_changed_date)::int AS updated_count
                   FROM aliyun_solutions WHERE is_active=TRUE AND NOT is_baseline""",
                (today, today),
            )
            solution_changes = c.fetchone()
            solution_new = solution_changes["new_count"]
            solution_updated = solution_changes["updated_count"]
            c.execute(
                """SELECT title, url, category, summary, first_seen_date, last_changed_date
                   FROM aliyun_solutions
                   WHERE is_active=TRUE AND NOT is_baseline AND last_changed_date=%s
                   ORDER BY CASE WHEN first_seen_date=%s THEN 0 ELSE 1 END, menu_order, id LIMIT 8""",
                (today, today),
            )
            solution_items = [dict(r) for r in c.fetchall()]
    except Exception:
        pass

    if not comp_news:
        from main_legacy import refresh_competitor_news
        comp_news = refresh_competitor_news()

    vendor_order = ["AWS", "Azure", "阿里云", "腾讯云", "火山云"]
    vendor_colors = {"AWS": "#FF6B00", "Azure": "#0078d4", "阿里云": "#F5D300", "腾讯云": "#84CC16", "火山云": "#3b82f6"}
    comp_by_vendor = {}
    for item in comp_news:
        v = item.get("vendor", "")
        if v not in comp_by_vendor:
            comp_by_vendor[v] = []
        comp_by_vendor[v].append(item)

    INK = "#183028"
    PAPER = "#F3F7F4"
    GRID = "#DCE8E0"
    MUTED = "#6B7F74"
    SECONDARY = "#385146"
    PRIMARY = "#3F8062"
    SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

    # ── 阿里云官方解决方案变化 ──
    solution_cards = ""
    for item in solution_items:
        is_new = item.get("first_seen_date") == today
        badge = "新增" if is_new else "更新"
        primary, _, secondary = (item.get("category") or "未分类").partition(" / ")
        category = f"{primary} · {secondary}" if secondary else primary
        solution_cards += f"""\
          <tr>
            <td style="padding:13px 16px;border-bottom:1px solid {GRID};">
              <span style="display:inline-block;padding:3px 8px;border-radius:999px;font-size:9px;font-weight:700;background:{'#DFF3E7' if is_new else PAPER};color:{PRIMARY};margin-right:7px;">{badge}</span>
              <span style="font-size:10px;color:{MUTED};">{escape(category)}</span>
              <a href="{escape(str(item.get('url') or '#'), quote=True)}" style="display:block;margin-top:7px;color:{INK};text-decoration:none;font-size:13px;font-weight:700;">{escape(str(item.get('title') or ''))}</a>
              <p style="margin:5px 0 0;font-size:11px;color:{SECONDARY};line-height:1.55;">{escape(str(item.get('summary') or '暂无摘要'))}</p>
            </td>
          </tr>"""
    solution_empty = f'<tr><td style="padding:24px;text-align:center;color:{MUTED};font-size:12px;">今日官方目录暂无新增或更新</td></tr>' if not solution_cards else ""

    # ── 友商动态卡片 ──
    comp_cards = ""
    for vendor in vendor_order:
        items = comp_by_vendor.get(vendor, [])
        if not items:
            continue
        color = vendor_colors.get(vendor, MUTED)
        news_rows = ""
        for item in items:
            badge_text_color = INK if color in ("#F5D300", "#84CC16") else "#FFFFFF"
            cat_badge = f'<span style="display:inline-block;padding:3px 8px;border-radius:999px;font-size:9px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;background:{color};color:{badge_text_color};margin-right:8px;">{item.get("category","")}</span>' if item.get("category") else ""
            news_rows += f"""\
              <tr>
                <td style="padding:12px 18px;border-bottom:1px solid {GRID};">
                  {cat_badge}
                  <a href="{item.get('link','#')}" style="color:{INK};text-decoration:none;font-size:13px;font-weight:600;">{item.get('title','')}</a>
                  <p style="margin:5px 0 0;font-size:12px;color:{MUTED};line-height:1.55;">{item.get('summary','')}</p>
                </td>
              </tr>"""
        comp_cards += f"""\
          <tr>
            <td style="padding:0 0 14px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {GRID};border-radius:14px;overflow:hidden;">
                <tr>
                  <td style="padding:11px 18px;border-bottom:1px solid {GRID};border-left:3px solid {color};">
                    <span style="font-size:13px;font-weight:700;color:{INK};letter-spacing:-0.01em;">{vendor}</span>
                  </td>
                </tr>
                {news_rows}
              </table>
            </td>
          </tr>"""

    # ── GitHub 趋势榜 ──
    github_cards = ""
    eval_by_repo = {item.get("repo_name"): item for item in eval_items}
    for i, item in enumerate(github_items[:8]):
        bg = INK if i < 3 else MUTED
        summary = (eval_by_repo.get(item.get("repo_name")) or {}).get("summary")
        summary_html = f'<p style="margin:8px 0 0;padding:8px 10px;border-left:2px solid {PRIMARY};background:{PAPER};font-size:11px;color:{SECONDARY};line-height:1.55;"><strong style="color:{PRIMARY};">AI 项目速读：</strong>{escape(str(summary))}</p>' if summary else ""
        lang_badge = f'<span style="display:inline-block;padding:3px 8px;border-radius:999px;font-size:9px;font-weight:600;letter-spacing:0.06em;background:{PAPER};color:{SECONDARY};border:1px solid {GRID};">{item.get("language","")}</span>' if item.get("language") and item.get("language") != "N/A" else ""
        today_stars = f'<span style="display:inline-block;padding:3px 8px;border-radius:999px;font-size:9px;font-weight:700;background:#DFF3E7;color:{PRIMARY};">{item.get("today_stars","")}</span>' if item.get("today_stars") else ""
        github_cards += f"""\
          <tr>
            <td style="padding:12px 14px;border-bottom:1px solid {GRID};vertical-align:top;width:34px;">
              <span style="display:inline-block;width:24px;height:24px;line-height:24px;border-radius:8px;text-align:center;font-size:11px;font-weight:700;color:#FFFFFF;background:{bg};">{i+1}</span>
            </td>
            <td style="padding:12px 14px;border-bottom:1px solid {GRID};">
              <a href="{item.get('repo_url','#')}" style="color:{INK};text-decoration:none;font-size:13px;font-weight:600;">{item.get('repo_name','')}</a>
              <p style="margin:4px 0 0;font-size:11px;color:{MUTED};line-height:1.45;">{item.get('description','')[:90]}</p>
              {summary_html}
              <div style="margin-top:5px;">{lang_badge} {today_stars}</div>
            </td>
            <td style="padding:12px 14px;border-bottom:1px solid {GRID};text-align:right;vertical-align:top;width:64px;">
              <span style="font-size:13px;font-weight:700;color:{INK};">{item.get('stars','')}</span>
              <p style="margin:2px 0 0;font-size:9px;color:{MUTED};letter-spacing:0.08em;text-transform:uppercase;">stars</p>
            </td>
          </tr>"""

    eval_cards = ""
    level_colors = {"强烈推荐": "#2F7D5A", "值得做": "#B7791F", "勉强可做": "#C56A30", "不建议": "#B94A48"}
    for item in eval_items:
        level = item.get("level", "")
        color = next((value for key, value in level_colors.items() if key in level), MUTED)
        eval_cards += f"""\
          <tr>
            <td style="padding:0 0 10px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border:1px solid {GRID};border-radius:14px;overflow:hidden;">
                <tr>
                  <td style="padding:14px 16px;">
                    <a href="{item.get('repo_url') or '#'}" style="color:{INK};text-decoration:none;font-size:13px;font-weight:700;">{item.get('repo_name','')}</a>
                    <span style="float:right;padding:3px 9px;border-radius:999px;background:{PAPER};border:1px solid {GRID};color:{color};font-size:10px;font-weight:700;">{item.get('total',0)} · {level}</span>
                    <p style="margin:8px 0 0;font-size:11px;color:{SECONDARY};line-height:1.55;">建议：{item.get('recommendation') or '暂无'}</p>
                    <p style="margin:4px 0 0;font-size:11px;color:{MUTED};line-height:1.55;">{item.get('reasoning') or ''}</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>"""

    github_empty = f'<tr><td colspan="3" style="padding:24px;text-align:center;color:{MUTED};font-size:12px;">今日数据抓取中</td></tr>' if not github_cards else ""
    eval_empty = f'<tr><td style="padding:24px;text-align:center;color:{MUTED};font-size:12px;">今日 AI 评估生成中</td></tr>' if not eval_cards else ""
    comp_empty = f'<tr><td style="padding:24px;text-align:center;color:{MUTED};font-size:12px;">暂无友商动态</td></tr>' if not comp_cards else ""

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style type="text/css">
  body{{margin:0;padding:0;background:{PAPER};font-family:{SANS};color:{INK};-webkit-font-smoothing:antialiased;-ms-text-size-adjust:100%;-webkit-text-size-adjust:100%;}}
  table{{border-collapse:collapse;mso-table-lspace:0;mso-table-rspace:0;}}
  td,a{{word-break:break-word;}}
  img{{border:0;outline:none;}}
  @media only screen and (max-width:480px){{
    .email-wrap{{width:100% !important;}}
    .email-pad{{padding-left:16px !important;padding-right:16px !important;}}
    .stat-cell{{display:block !important;width:100% !important;padding:8px 12px !important;}}
    .stat-gap{{display:none !important;}}
  }}
</style>
</head>
<body>
<!--[if mso]><center><table cellpadding="0" cellspacing="0" width="600"><tr><td><![endif]-->
<table class="email-wrap" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPER};padding:28px 0;">
  <tr>
    <td align="center">

      <!-- 主容器 -->
      <table class="email-wrap" width="600" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border:1px solid {GRID};border-radius:22px;overflow:hidden;box-shadow:0 12px 36px rgba(24,48,40,0.08);">

        <!-- ════ Header ════ -->
        <tr>
          <td style="background:{INK};padding:36px 40px;" class="email-pad">
            <p style="margin:0 0 8px;font-size:10px;font-weight:600;color:#A9E5C4;letter-spacing:0.22em;text-transform:uppercase;">Technology Solution Intelligence</p>
            <h1 style="margin:0 0 6px;font-size:24px;font-weight:800;color:#FFFFFF;letter-spacing:-0.02em;">InsightPro · 技术解决方案日报</h1>
            <p style="margin:0;font-size:12px;color:#A0B5AA;">{today_cn} {weekday}</p>
          </td>
        </tr>

        <!-- ════ 统计概览 ════ -->
        <tr>
          <td style="padding:20px 40px 0;" class="email-pad">
            <table width="100%" cellpadding="0" cellspacing="0" style="border-radius:14px;overflow:hidden;">
              <tr>
                <td class="stat-cell" style="background:{PAPER};border:1px solid {GRID};padding:14px 16px;text-align:center;">
                  <span style="font-size:9px;color:{MUTED};letter-spacing:0.16em;text-transform:uppercase;">官方方案库</span>
                  <span style="display:block;font-size:18px;font-weight:700;color:{INK};margin-top:3px;">{solution_total} 项</span>
                </td>
                <td class="stat-gap" width="6" style="font-size:1px;line-height:1px;">&nbsp;</td>
                <td class="stat-cell" style="background:{PAPER};border:1px solid {GRID};padding:14px 16px;text-align:center;">
                  <span style="font-size:9px;color:{MUTED};letter-spacing:0.16em;text-transform:uppercase;">今日新增</span>
                  <span style="display:block;font-size:18px;font-weight:700;color:{PRIMARY};margin-top:3px;">{solution_new} 项</span>
                </td>
                <td class="stat-gap" width="6" style="font-size:1px;line-height:1px;">&nbsp;</td>
                <td class="stat-cell" style="background:{PAPER};border:1px solid {GRID};padding:14px 16px;text-align:center;">
                  <span style="font-size:9px;color:{MUTED};letter-spacing:0.16em;text-transform:uppercase;">今日更新</span>
                  <span style="display:block;font-size:18px;font-weight:700;color:{INK};margin-top:3px;">{solution_updated} 项</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- ════ 解决方案变化 ════ -->
        <tr>
          <td style="padding:28px 40px 0;" class="email-pad">
            <span style="font-size:11px;font-weight:600;color:{MUTED};letter-spacing:0.18em;text-transform:uppercase;">Solution Updates</span>
            <span style="display:block;font-size:18px;font-weight:700;color:{INK};margin-top:3px;">阿里云官方解决方案变化</span>
            <span style="display:block;font-size:11px;color:{MUTED};margin-top:5px;">每日对比官方目录，仅标记当天真实新增与更新</span>
          </td>
        </tr>
        <tr>
          <td style="padding:12px 40px 0;" class="email-pad">
            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {GRID};border-radius:14px;overflow:hidden;">
              {solution_cards}
              {solution_empty}
            </table>
          </td>
        </tr>

        <!-- ════ GitHub 趋势 ════ -->
        <tr>
          <td style="padding:28px 40px 0;" class="email-pad">
            <span style="font-size:11px;font-weight:600;color:{MUTED};letter-spacing:0.18em;text-transform:uppercase;">GitHub Trending</span>
            <span style="display:block;font-size:18px;font-weight:700;color:{INK};margin-top:3px;">今日技术洞察</span>
          </td>
        </tr>
        <tr>
          <td style="padding:12px 40px 0;" class="email-pad">
            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {GRID};border-radius:14px;overflow:hidden;">
              {github_cards}
              {github_empty}
            </table>
          </td>
        </tr>

        <!-- ════ AI 价值评估 ════ -->
        <tr>
          <td style="padding:28px 40px 0;" class="email-pad">
            <span style="font-size:11px;font-weight:600;color:{MUTED};letter-spacing:0.18em;text-transform:uppercase;">AI Value Assessment</span>
            <span style="display:block;font-size:18px;font-weight:700;color:{INK};margin-top:3px;">技术价值评估</span>
            <span style="display:block;font-size:11px;color:{MUTED};margin-top:5px;">服务端 · 营销 · 场景 · 云上部署四维分析</span>
          </td>
        </tr>
        <tr>
          <td style="padding:12px 40px 0;" class="email-pad">
            <table width="100%" cellpadding="0" cellspacing="0">
              {eval_cards}
              {eval_empty}
            </table>
          </td>
        </tr>

        <!-- ════ 友商动态 ════ -->
        <tr>
          <td style="padding:28px 40px 0;" class="email-pad">
            <span style="font-size:11px;font-weight:600;color:{MUTED};letter-spacing:0.18em;text-transform:uppercase;">Competitor News</span>
            <span style="display:block;font-size:18px;font-weight:700;color:{INK};margin-top:3px;">云厂商最新动态</span>
          </td>
        </tr>
        <tr>
          <td style="padding:12px 40px 0;" class="email-pad">
            <table width="100%" cellpadding="0" cellspacing="0">
              {comp_cards}
              {comp_empty}
            </table>
          </td>
        </tr>

        <!-- ════ CTA ════ -->
        <tr>
          <td style="padding:32px 40px;text-align:center;" class="email-pad">
            <a href="{BASE_URL}/insights/solutions" style="display:inline-block;padding:13px 40px;border-radius:999px;background:{PRIMARY};color:#FFFFFF;font-size:13px;font-weight:600;letter-spacing:0.04em;text-decoration:none;">查看完整解决方案洞察 →</a>
            <p style="margin:12px 0 0;font-size:10px;color:{MUTED};">技术热点 · 解决方案洞察 · 云厂商动态</p>
          </td>
        </tr>

        <!-- ════ Footer ════ -->
        <tr>
          <td style="padding:16px 40px;background:{PAPER};border-top:1px solid {GRID};" class="email-pad">
            <p style="margin:0;font-size:10px;color:{MUTED};">InsightPro 自动发送 · 投递时间由订阅计划设定</p>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>
<!--[if mso]></td></tr></table></center><![endif]-->
</body>
</html>"""
    return html


def send_email(to_addr: str, subject: str, html_content: str) -> bool:
    """通过 SMTP 发送邮件"""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD or settings.SMTP_PASSWORD == "your-qq-auth-code-here":
        print("邮件未配置：请在 .env 中设置 SMTP_PASSWORD（QQ 邮箱授权码）")
        return False
    try:
        msg = MIMEText(html_content, "html", "utf-8")
        msg["Subject"] = subject
        msg["From"] = f"InsightPro <{settings.EMAIL_FROM}>"
        msg["To"] = to_addr
        msg["X-Mailer"] = "InsightPro"
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, [to_addr], msg.as_string())
        print(f"邮件发送成功: {to_addr}")
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False


def send_daily_digest():
    """立即向全部有效订阅者发送洞察日报。"""
    subscribers = get_subscribers()
    if not subscribers:
        if settings.EMAIL_TO:
            subscribers = [{"email": settings.EMAIL_TO, "name": ""}]
        else:
            print("没有邮件订阅者，跳过发送")
            return

    html = build_daily_digest_html()
    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"InsightPro · 技术解决方案日报 ({today})"
    success = 0
    for sub in subscribers:
        if send_email(sub["email"], subject, html):
            success += 1
    print(f"每日邮件发送完成: {success}/{len(subscribers)} 成功")
    return {"sent": success, "total": len(subscribers)}


def send_scheduled_digests(now: Optional[datetime] = None):
    """每分钟扫描一次，仅向当前到期且今日未发送的订阅者投递。"""
    now = now or datetime.now(SHANGHAI_TZ)
    due = [subscriber for subscriber in get_subscribers() if subscriber_is_due(subscriber, now)]
    if not due:
        return {"sent": 0, "total": 0}

    html = build_daily_digest_html()
    subject = f"InsightPro · 技术解决方案日报 ({now:%Y-%m-%d})"
    success = 0
    for subscriber in due:
        if not send_email(subscriber["email"], subject, html):
            continue
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE email_subscribers SET last_sent_at = CURRENT_TIMESTAMP WHERE id = %s",
                (subscriber["id"],),
            )
        success += 1
    print(f"订阅邮件发送完成: {success}/{len(due)} 成功")
    return {"sent": success, "total": len(due)}
