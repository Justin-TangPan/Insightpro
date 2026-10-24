"""Five-board email dashboard, assembled from finished analyses and source records."""
from __future__ import annotations

import json
from datetime import date, datetime
from html import escape
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from db import get_db
from settings import settings

BOARDS = {
    "github": ("GitHub 技术", "GitHub technology", "/insights/hotspots"),
    "apps": ("AI 应用", "AI applications", "/insights/app-launches"),
    "solutions": ("解决方案", "Solutions", "/insights/solutions"),
    "community": ("社区洞察", "Community", "/insights/community"),
    "competitors": ("厂商动态", "Vendor updates", "/insights/competitors"),
}


def current_analyses(today: date) -> dict:
    """Read cached analyses only; generating an email must never start AI work."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT board, analysis FROM board_daily_insights WHERE insight_date=%s", (today.isoformat(),))
        analyses = {row["board"]: json.loads(row["analysis"]) for row in cursor.fetchall()}
        return {board: summary for board, summary in analyses.items() if summary.get("analysis_version") == 4}


def safe_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme in ("http", "https") and parsed.netloc else ""
    except ValueError:
        return ""


def _build_event_brief(analyses: dict, base: str, now: datetime, language: str) -> str | None:
    from services.event_service import list_events

    events = list_events(100)["items"]
    if not events:
        return None
    en = language == "en"
    scope_names = {
        "technology_ecosystem": "Technology" if en else "技术生态",
        "ai_applications": "AI applications" if en else "AI 应用",
        "solutions": "Solutions" if en else "解决方案",
        "community_insights": "Community" if en else "社区洞察",
        "competitor_dynamics": "Competitors" if en else "友商动态",
    }
    counts = {scope: 0 for scope in scope_names}
    for event in events:
        for scope in event.get("business_scopes") or []:
            if scope in counts:
                counts[scope] += 1
    def score(event: dict) -> float:
        scores = event.get("scores") or {}
        if isinstance(scores, str):
            try:
                scores = json.loads(scores)
            except ValueError:
                scores = {}
        return float((scores.get("hot_score") or {}).get("value") or 0)
    events.sort(key=lambda item: (score(item), str(item.get("last_seen_at") or "")), reverse=True)
    analysis_by_event = {
        (summary.get("focus") or {}).get("event_id"): summary
        for summary in analyses.values() if isinstance(summary, dict)
    }
    rows = []
    for event in events[:3]:
        event_id = event["id"]
        summary = analysis_by_event.get(event_id) or {}
        focus = summary.get("focus") or {}
        event_url = f"{base}/events/{event_id}"
        title = escape(str(event.get("title") or ""))
        event_summary = escape(str(event.get("summary") or "")[:180])
        score_value = score(event)
        meta = [f"{event.get('source_count') or 0} {'sources' if en else '个来源'}",
                f"{event.get('evidence_count') or 0} {'evidence items' if en else '条证据'}"]
        if score_value:
            meta.insert(0, f"Hot score {score_value:g}" if en else f"热度评分 {score_value:g}")
        impact = focus.get("impact") or focus.get("why")
        impact_html = (f'<p style="margin:6px 0 0;color:#475569;font-size:13px">{escape(str(impact)[:180])}</p>'
                       if impact else "")
        rows.append(f'<tr><td style="padding:13px 0;border-bottom:1px solid #e5e7eb"><a href="{escape(event_url, quote=True)}" style="color:#27313d;font-size:15px;font-weight:700">{title}</a><div style="margin-top:4px;color:#66717d;font-size:12px">{escape(" · ".join(meta))}</div><div style="margin-top:6px;color:#475569;font-size:13px;line-height:1.55">{event_summary}</div>{impact_html}</td></tr>')
    business_changes = " · ".join(f"{scope_names[key]} <b>{count}</b>" for key, count in counts.items() if count)
    business_changes = business_changes or ("No active events" if en else "暂无有效事件")
    title = "Today's AI market brief" if en else "今日 AI 市场简报"
    return f'''<!doctype html><html lang="{'en' if en else 'zh-CN'}"><head><meta charset="utf-8"></head><body style="margin:0;background:#fff;color:#27313d;font-family:Arial,'PingFang SC','Microsoft YaHei',sans-serif"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px"><table role="presentation" width="100%" style="max-width:600px;border-top:2px solid #334155" cellpadding="0" cellspacing="0"><tr><td style="padding:22px 0 14px;border-bottom:1px solid #e5e7eb"><div style="color:#66717d;font-size:12px">INSIGHTPRO · {now:%Y-%m-%d} UTC+8</div><h1 style="margin:8px 0;font-size:24px">{title}</h1><div style="color:#475569;font-size:13px">{len(events)} {'recent events reviewed (max 100)' if en else '条近期事件（最多检查 100 条）'}</div></td></tr><tr><td style="padding:14px 0;border-bottom:1px solid #e5e7eb"><div style="color:#66717d;font-size:12px;font-weight:700">{'RECENT EVENTS BY BUSINESS' if en else '五大业务近期事件'}</div><div style="margin-top:7px;font-size:14px">{business_changes}</div></td></tr><tr><td><h2 style="margin:20px 0 4px;font-size:17px">{'Top intelligence' if en else '今日重点情报'}</h2><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{''.join(rows)}</table><p style="color:#66717d;font-size:12px;line-height:1.6">{'Counts, evidence and scores are observed system data. Business impact appears only when a cached analysis is linked to the same Event.' if en else '数量、证据与评分来自系统观测；商业影响仅在缓存分析关联到同一 Event 时展示。'}</p></td></tr></table></td></tr></table></body></html>'''


def build_html(language: str = "zh") -> str:
    en = language == "en"
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    analyses = current_analyses(now.date())
    base = settings.BASE_URL.rstrip("/")
    event_brief = _build_event_brief(analyses, base, now, language)
    if event_brief:
        return event_brief
    has_cached_source = any(safe_url((summary.get("focus") or {}).get("url", ""))
                            for summary in analyses.values() if isinstance(summary, dict))
    intro = (("Recent board analyses with cached source links." if has_cached_source else "Recent board analyses; no cached focus sources are available.") if en else
             ("五个业务板块的近期分析与缓存来源。" if has_cached_source else "五个业务板块的近期分析；当前没有缓存重点来源。"))
    cards = []
    for key, (zh_name, en_name, path) in BOARDS.items():
        analysis = analyses.get(key) or {}
        focus = analysis.get("focus") or {}
        source_url = safe_url(focus.get("url", ""))
        event_id = focus.get("event_id")
        url = f"{base}/events/{event_id}" if type(event_id) is int and event_id > 0 else source_url
        item_title = focus.get("title") or ""
        judgment = analysis.get("judgment") or (("Recent source available; in-depth analysis is pending." if item_title else "No verified recent update.") if en else ("近期来源已收录，深入分析待更新。" if item_title else "近 7 天暂无可核实的新信息。"))
        status = ("Current community snapshot" if en else "当前社区热榜") if key == "community" else ("Last 7 days" if en else "近 7 天")
        if key not in analyses or "focus" not in analysis:
            status += " · " + ("Analysis pending" if en else "分析待更新")
        title_html = f'<a href="{escape(url, quote=True)}" style="color:#27313d;font-weight:700;text-decoration:underline">{escape(item_title)}</a>' if url else escape(item_title)
        meta = focus.get("meta") or ""
        detail = "".join(f'<p style="margin:10px 0 0;color:#475569;font-size:14px;line-height:1.65"><strong style="color:#27313d">{label}：</strong>{escape(focus[field])}</p>'
                         for field, label in (("why", "Why it matters" if en else "为何值得关注"),
                                              ("analysis", "What changed" if en else "事件解读"),
                                              ("impact", "Business impact" if en else "业务影响"),
                                              ("caveat", "Evidence boundary" if en else "证据边界")) if focus.get(field))
        source_link = f'<a href="{escape(source_url, quote=True)}" style="color:#475569;font-size:12px">{"Original source" if en else "原始来源"}</a>' if source_url else ""
        cards.append(f'''<tr><td style="padding:23px 0 25px;border-bottom:1px solid #e5e7eb">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td><h2 style="margin:0;color:#27313d;font-size:18px;line-height:1.4">{escape(en_name if en else zh_name)}</h2></td><td align="right" style="color:#66717d;font-size:12px;white-space:nowrap">{status}</td></tr></table>
          <p style="margin:12px 0 0;color:#27313d;font-size:15px;line-height:1.65;font-weight:600"><span style="display:block;color:#66717d;font-size:12px;font-weight:700">{"Overall assessment" if en else "总体判断"}</span>{escape(judgment)}</p>
          <p style="margin:16px 0 0;color:#66717d;font-size:12px;font-weight:700">{"Focus to examine" if en else "本期重点分析"}</p>
          <p style="margin:5px 0 0;color:#27313d;font-size:15px;line-height:1.6">{title_html or ("No representative item" if en else "暂无代表条目")}<span style="display:block;color:#66717d;font-size:12px;line-height:1.5;margin-top:4px">{escape(meta)}</span><span style="display:block;margin-top:5px">{source_link}</span></p>
          {detail}
          <p style="margin:13px 0 0"><a href="{escape(base + path, quote=True)}" style="color:#334155;font-size:13px;font-weight:700;text-decoration:underline">{"View board" if en else "查看板块详情"} →</a></p>
        </td></tr>''')
    complete = set(analyses) >= set(BOARDS)
    note = ("All five boards have today's cached analysis · Community is a current ranking snapshot; boards without a focus item omit source fallback." if en else "五个板块均有当日分析缓存 · 社区为当前热榜观察；无焦点板块不补入其他来源。") if complete else ("Some board analyses or focus items are pending; uncached sources are omitted." if en else "部分板块分析或重点条目待更新；未缓存来源不作补入。")
    title = "Five-board intelligence brief" if en else "五大业务情报简报"
    community_note = "Community items are a current ranking snapshot; publication dates are not verified." if en else "社区内容为当前热榜观察，未逐条核实发布日期。"
    return f'''<!doctype html><html lang="{"en" if en else "zh-CN"}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;background:#ffffff;color:#27313d;font-family:Arial,'PingFang SC','Microsoft YaHei',sans-serif"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff"><tr><td align="center" style="padding:20px 12px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff"><tr><td style="padding:28px 25px 23px;border-top:2px solid #334155;border-bottom:1px solid #e5e7eb"><p style="margin:0 0 12px;color:#66717d;font-size:12px;font-weight:700;letter-spacing:1px">INSIGHTPRO &nbsp;/&nbsp; {now:%Y-%m-%d} UTC+8</p><h1 style="margin:0;color:#27313d;font-size:25px;line-height:1.3">{title}</h1><p style="margin:10px 0 0;color:#475569;font-size:14px;line-height:1.6">{intro}</p></td></tr><tr><td style="padding:0 25px 27px"><p style="margin:19px 0 2px;color:#66717d;font-size:12px;line-height:1.6">{note}</p><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{''.join(cards)}</table><p style="margin:22px 0 0;color:#66717d;font-size:12px;line-height:1.6">{community_note}</p><p style="margin:8px 0 0;color:#66717d;font-size:12px;line-height:1.6">{"Automated analysis is a reading aid. Verify the original source before acting." if en else "AI 分析仅辅助阅读，采取行动前请核实原始来源。"}</p></td></tr></table></td></tr></table></body></html>'''
