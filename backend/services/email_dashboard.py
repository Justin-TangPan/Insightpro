"""Render the current homepage projection as a durable email document."""
from __future__ import annotations
from datetime import datetime
from html import escape
import os
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
import requests
from settings import settings


def homepage_snapshot() -> dict:
    response = requests.get(os.getenv('INSIGHT_FRONTEND_URL', 'http://frontend:3000').rstrip('/') + '/api/home-email-snapshot', timeout=40)
    response.raise_for_status()
    return response.json()


def _url(event: dict) -> str:
    source = next((item.get('url', '') for item in event.get('sources', []) if item.get('url', '').startswith(('https://', 'http://'))), '')
    if source and urlsplit(source).netloc:
        return source
    identifier = str(event.get('id', ''))
    return f"{settings.BASE_URL.rstrip('/')}/events/{identifier[6:]}" if identifier.startswith('event:') and identifier[6:].isdigit() else settings.BASE_URL.rstrip('/')


def _link(event: dict) -> str:
    return f'<a href="{escape(_url(event), quote=True)}" style="color:#17345b;text-decoration:none;font-weight:700">{escape(str(event.get("display_title") or event.get("title") or ""))}</a>'


def _section(title: str, body: str) -> str:
    return f'<tr><td style="padding:22px 28px;border-bottom:1px solid #e5ebf2"><h2 style="margin:0 0 12px;font-size:18px;color:#10233c">{title}</h2>{body}</td></tr>'


def _daily_brief_section(language: str = "zh", brief: dict | None = None) -> str:
    """Render the shared daily AI brief as the leading email section (same data as the homepage)."""
    from services.daily_ai_brief_service import read

    def esc(value) -> str:
        return escape(str(value or ""))

    if brief is None:
        try:
            brief = read()
        except Exception:
            return ""
    en = language == "en"
    if brief.get("status") == "failed" or not (brief.get("headline") or brief.get("quick_reads") or brief.get("recent_judgments")):
        note = brief.get("note") or ("No high-value AI events today." if en else "今日暂无可核实的高价值 AI 情报。")
        return _section("Daily AI brief" if en else "每日 AI 洞察简讯", f'<p style="margin:0;color:#526277">{esc(note)}</p>')
    parts: list[str] = []
    judgments = brief.get("recent_judgments") or []
    if judgments:
        parts.append('<h3 style="margin:0 0 8px;font-size:14px;color:#10233c">' + ("Recent judgments" if en else "近日判断") + '</h3>' + ''.join(
            f'<p style="margin:8px 0;line-height:1.55"><b>{esc(item["title"])}</b><br><span style="color:#526277">{esc(item["detail"])}</span></p>'
            for item in judgments))
    headline = brief.get("headline")
    if headline:
        headline_body = f'<p style="font-size:16px;line-height:1.4;margin:0 0 6px"><a href="{esc(headline.get("source_url"))}" style="color:#17345b;text-decoration:none;font-weight:700">{esc(headline.get("title"))}</a></p>'
        headline_body += f'<p style="margin:0 0 8px;color:#526277;font-size:12px">{esc(headline.get("category"))} · {esc(headline.get("source_name"))} · {esc(str(headline.get("published_at") or "")[:10])}</p>'
        headline_body += f'<p style="margin:0;line-height:1.6"><b>摘要</b> {esc(headline.get("summary"))}</p><p style="margin:8px 0 0;line-height:1.6"><b>点评</b> {esc(headline.get("commentary"))}</p><p><a href="{escape(str(headline.get("source_url") or ""), quote=True)}">查看原文 →</a></p>'
        parts.append('<h3 style="margin:14px 0 8px;font-size:14px;color:#10233c">' + ("Today's headline" if en else "今日头条") + '</h3>' + headline_body)
    quick_reads = brief.get("quick_reads") or []
    if quick_reads:
        quick_body = ''.join(
            f'<p style="margin:10px 0;line-height:1.55"><b style="color:#67809d">{esc(item.get("title"))}</b><br>'
            f'<span style="color:#526277">【摘要】{esc(item.get("summary"))}<br>【点评】{esc(item.get("commentary"))}</span><br>'
            f'<a href="{escape(str(item.get("source_url") or ""), quote=True)}" style="color:#17345b;text-decoration:none;font-size:12px">查看原文 →</a></p>'
            for item in quick_reads)
        parts.append('<h3 style="margin:14px 0 8px;font-size:14px;color:#10233c">' + ("Quick reads" if en else "今日快读") + '</h3>' + quick_body)
    return _section("Daily AI brief" if en else "每日 AI 洞察简讯", ''.join(parts))


def build_html(language: str = 'zh', snapshot: dict | None = None) -> str:
    snapshot = snapshot if snapshot is not None else homepage_snapshot()
    en = language == 'en'
    base = settings.BASE_URL.rstrip('/')
    now = datetime.fromisoformat(snapshot['as_of']).astimezone(ZoneInfo('Asia/Shanghai'))
    focus_item = snapshot.get('focus') or {}
    focus = focus_item.get('event') or {}
    focus_body = f'<p style="font-size:20px;line-height:1.45;margin:0 0 12px">{_link(focus) if focus else ("No verified focus" if en else "近期暂无可核实的焦点")}</p>'
    if focus:
        focus_body += f'<p style="margin:0 0 8px;color:#526277">{escape(str(focus.get("vendor") or "行业动态"))} · {escape(str(focus_item.get("type") or ""))}</p>'
        focus_body += f'<p style="line-height:1.6;margin:0">{escape(str(focus.get("summary") or ""))}</p><p style="line-height:1.6;margin:8px 0 0">{escape(str(focus.get("why") or ""))}</p>'
    judgments = snapshot.get('insights') or []
    judgment_body = ''.join(f'<p style="margin:8px 0;line-height:1.55"><b>{escape(item["label"])}</b> · {escape(str((item.get("event") or {}).get("why") or "暂无可核实的新变化"))}</p>' for item in judgments)
    board_body = ''.join(f'<tr><td style="padding:11px 0;border-bottom:1px solid #edf1f5;width:105px;font-weight:700">{escape(board["name"])}</td><td style="padding:11px 0;border-bottom:1px solid #edf1f5">{_link(board["events"][0]) if board["events"] else "近 30 天暂无新增"}<div style="margin-top:4px;color:#526277;line-height:1.5">{escape(str(board["events"][0].get("summary") or board["events"][0].get("why") or "")) if board["events"] else ""}</div></td></tr>' for board in snapshot.get('boards', []))
    priorities = [focus_item, *(snapshot.get('keypoints') or [])][:5]
    priority_body = ''.join(f'<p style="margin:10px 0;line-height:1.55"><b style="color:#67809d">{index:02d}</b> &nbsp;{_link(item["event"])}<br><span style="color:#526277">{escape(str(item["event"].get("summary") or item["event"].get("why") or ""))}</span></p>' for index, item in enumerate(priorities, 1) if item.get('event')) or '暂无重点动态'
    vendor_body = ''.join(f'<p style="margin:8px 0;line-height:1.55">{escape(str(item.get("vendor") or "厂商"))} · {_link(item)}<br><span style="color:#526277">{escape(str(item.get("summary") or item.get("why") or ""))}</span></p>' for item in snapshot.get('vendors', [])) or '近期暂无友商动态'
    latest_body = '<table role="presentation" width="100%" cellspacing="0" cellpadding="0">' + ''.join(f'<tr><td style="padding:9px 4px;border-bottom:1px solid #edf1f5;color:#60738b;white-space:nowrap">{escape(str(item.get("happened_at") or "")[:10])}</td><td style="padding:9px 4px;border-bottom:1px solid #edf1f5">{_link(item)}</td></tr>' for item in snapshot.get('latest', [])) + '</table>'
    title = 'Xiao Leida business intelligence brief' if en else '小雷达首页商业情报简报'
    observed = [item.get('last_seen_at') or item.get('observed_at') or item.get('happened_at') for item in snapshot.get('latest', [])]
    latest_time = max((datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(ZoneInfo('Asia/Shanghai')) for value in observed if value), default=now)
    sections = [_daily_brief_section(language, snapshot.get("_daily_ai_brief")), _section('Recent focus' if en else '近期焦点', focus_body), _section('Core judgments' if en else '本期核心判断', judgment_body), _section('Five business areas' if en else '五大业务摘要', f'<table role="presentation" width="100%" cellspacing="0">{board_body}</table>'), _section('Top updates' if en else '重点动态', priority_body), _section('Vendor watch' if en else '厂商关注 / 友商动态摘要', vendor_body), _section('Latest updates' if en else '最新动态', latest_body)]
    sections = [s for s in sections if s]
    return f'''<!doctype html><html lang="{'en' if en else 'zh-CN'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0;background:#edf2f8;font-family:Arial,'PingFang SC',sans-serif;color:#26384d"><table role="presentation" width="100%" cellspacing="0"><tr><td align="center" style="padding:24px 12px"><table role="presentation" width="100%" cellspacing="0" style="max-width:640px;background:white;border-radius:12px;overflow:hidden"><tr><td style="padding:26px 28px;background:#102b50;color:white"><div style="font-size:13px;letter-spacing:2px;font-weight:700">小雷达</div><h1 style="margin:12px 0 8px;font-size:26px">{title}</h1><div style="font-size:13px;color:#c7d6e7">{'Latest data: ' if en else '最新数据时间：'}{latest_time:%Y-%m-%d %H:%M} CST</div></td></tr>{''.join(sections)}<tr><td align="center" style="padding:28px"><a href="{escape(base, quote=True)}" style="display:inline-block;background:#173b70;color:white;padding:13px 24px;border-radius:7px;text-decoration:none;font-weight:700">{'View full homepage' if en else '查看完整首页'} →</a></td></tr></table></td></tr></table></body></html>'''
