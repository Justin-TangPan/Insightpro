"""Compact technical-project email built from stored GitHub observations."""
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from db import get_db


def _rows() -> list[dict]:
    from services.repository_service import list_trending_repositories

    snapshot = list_trending_repositories("daily")
    if snapshot["source"] == "event_store":
        items = []
        for row in snapshot["items"]:
            scores = row.get("scores") or {}
            evaluation = scores.get("business_evaluation") or {}
            hot_score = scores.get("hot_score") or {}
            items.append({**row, "total": evaluation.get("total"),
                          "engineering_score": evaluation.get("d4"),
                          "technical_assessment": evaluation.get("technical_assessment"),
                          "stars_delta": hot_score.get("stars_delta"),
                          "recommendation": evaluation.get("recommendation"),
                          "reasoning": evaluation.get("reasoning") or evaluation.get("summary")})
        return items
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""WITH latest AS (SELECT MAX(scrape_date) AS day FROM github_trending WHERE category='daily')
            SELECT g.repo_name,g.repo_url,g.description,g.language,g.stars,g.forks,g.today_stars,
                   e.total,e.d4,e.recommendation,e.reasoning
            FROM github_trending g CROSS JOIN latest
            LEFT JOIN LATERAL (
                SELECT total,recommendation,reasoning FROM trending_business_eval
                WHERE repo_name=g.repo_name AND scrape_date=g.scrape_date
                ORDER BY id DESC LIMIT 1
            ) e ON TRUE
            WHERE g.category='daily' AND g.scrape_date=latest.day
            ORDER BY COALESCE((regexp_match(g.today_stars, '[0-9,]+'))[1]::numeric,0) DESC,g.repo_name
            LIMIT 8""")
        return [{**dict(row), "engineering_score": row.get("d4"), "stars_delta": None, "pushed_at": None, "topics": [],
                 "contributors_count": None, "latest_release": None}
                for row in cursor.fetchall()]


def build_html(language: str = "zh") -> str:
    en = language == "en"
    rows = _rows()
    leads = ("Technical project brief", "Developer trend", "Trending repositories", "No verified release records.") if en else (
        "技术项目洞察", "开发者趋势", "Trending Repo", "当前没有可核实的重大版本发布记录。")
    title, trend_title, repos_title, empty = leads
    languages: dict[str, int] = {}
    directions = {"Agent": ("agent", "智能体"), "MCP": ("mcp", "MCP"), "AI Infra": ("infra", "推理|向量|runtime|infrastructure|gpu"), "Model": ("model", "模型|llm|多模态"), "Developer Tool": ("developer", "developer|cli|ide|framework|sdk|开发工具|框架")}
    import re
    for row in rows:
        lang = (row.get("language") or "").strip()
        if lang and lang.casefold() not in ("n/a", "unknown"):
            languages[lang] = languages.get(lang, 0) + 1
    trends = []
    for label, (_, pattern) in directions.items():
        count = sum(bool(re.search(pattern, f"{row.get('repo_name','')} {row.get('description','')}", re.I)) for row in rows)
        if count:
            trends.append((label if en else {"Agent": "Agent", "MCP": "MCP", "AI Infra": "AI Infra", "Model": "模型", "Developer Tool": "开发工具"}[label], count))
    trend_items = sorted(trends, key=lambda item: item[1], reverse=True)[:4]
    language_items = [(f"{label} ({count})" if en else f"{label} ({count})") for label, count in sorted(languages.items(), key=lambda item: item[1], reverse=True)[:4]]
    cards = []
    for row in rows:
        url = str(row.get("repo_url") or "")
        if not url.startswith("https://github.com/"):
            continue
        title_text = escape(str(row.get("repo_name") or ""))
        description = escape(str(row.get("description") or "")[:180])
        metrics = [
            ("Stars", row.get("stars") or "—"),
            (("24h Δ" if en else "24 小时增长"), row.get("stars_delta") if row.get("stars_delta") is not None else row.get("today_stars") or "—"),
            ("Forks", row.get("forks") or "—"),
            (("Business score" if en else "业务评估"), row.get("total") if row.get("total") is not None else "—"),
            (("Engineering / delivery" if en else "工程交付评估（AI）"), row.get("engineering_score") if row.get("engineering_score") is not None else "—"),
        ]
        metric_html = " · ".join(f"<b>{escape(str(label))}</b> {escape(str(value))}" for label, value in metrics)
        activity = escape(str(row.get("pushed_at") or ("not collected" if en else "未采集")))
        topics = ", ".join(escape(str(topic)) for topic in (row.get("topics") or [])[:4]) or ("—")
        contributors = row.get("contributors_count")
        release = row.get("latest_release") or {}
        release_name = release.get("name") or release.get("tag_name")
        release_value = " — ".join(str(value) for value in (release_name, release.get("published_at")) if value)
        if not release_value:
            if row.get("repository_metadata_available"):
                release_value = "none published" if en else "未发布 Release"
            else:
                release_value = "not collected" if en else "未采集"
        contributors_value = contributors if contributors is not None else ("not collected" if en else "未采集")
        analysis = escape(str(row.get("reasoning") or row.get("recommendation") or "")[:240])
        technical = row.get("technical_assessment") or {}
        technical_labels = {
            "engineering_maturity": "Engineering maturity" if en else "工程成熟度",
            "innovation": "Innovation" if en else "创新性",
            "deployability": "Deployability" if en else "可部署性",
        }
        evidence_labels = {
            "description": "Description" if en else "项目描述", "stars_delta": "Stars growth" if en else "Stars 增长",
            "pushed_at": "Last push" if en else "最近代码更新", "contributors_count": "Contributors" if en else "贡献者",
            "license": "License" if en else "许可证", "topics": "Topics" if en else "技术方向",
            "latest_release_tag": "Release tag" if en else "Release 版本", "latest_release_date": "Release date" if en else "Release 日期",
            "latest_release_major": "Major version change" if en else "主版本变化", "latest_release_notes": "Release notes" if en else "Release 说明",
            "stars": "Stars", "forks": "Forks", "today_stars": "Daily Stars" if en else "今日 Stars",
        }
        technical_parts = []
        for key, label in technical_labels.items():
            dimension = technical.get(key) or {}
            if not dimension:
                continue
            score = dimension.get("score")
            score_text = f"{score}/10" if score is not None else ("Insufficient evidence" if en else "证据不足")
            refs = ", ".join(evidence_labels.get(ref, ref) for ref in dimension.get("evidence_keys", []))
            detail = f"{escape(label)} <b>{escape(score_text)}</b>"
            if refs:
                detail += f" <span style=\"color:#64748b\">({escape(refs)})</span>"
            if dimension.get("reasoning"):
                detail += f"<div style=\"color:#64748b;margin-top:2px\">{escape(str(dimension['reasoning'])[:120])}</div>"
            technical_parts.append(f"<div style=\"padding:6px 8px;background:#f8fafc;border-radius:6px\">{detail}</div>")
        technical_html = (f"<div style=\"display:grid;gap:5px;margin-top:8px;font-size:12px\">{''.join(technical_parts)}</div>" if technical_parts else "")
        activity_label = "Last pushed" if en else "最近代码更新"
        topic_label = "Topics" if en else "技术方向"
        contributors_label = "Contributors" if en else "贡献者"
        is_major_release = bool(release.get("major_release"))
        release_label = ("Major release" if is_major_release else "Latest release") if en else ("重大版本" if is_major_release else "最近 Release")
        cards.append(f'<tr><td style="padding:16px 0;border-bottom:1px solid #e5e7eb"><a href="{escape(url, quote=True)}" style="font-weight:700;color:#172554">{title_text}</a><div style="margin-top:5px;color:#475569">{description}</div><div style="margin-top:8px;color:#334155;font-size:12px">{metric_html}</div><div style="margin-top:5px;color:#64748b;font-size:12px">{activity_label}: {activity} · {topic_label}: {topics}</div><div style="margin-top:4px;color:#64748b;font-size:12px">{contributors_label}: {escape(str(contributors_value))} · {release_label}: {escape(str(release_value))}</div><div style="margin-top:6px;color:#64748b;font-size:13px">{analysis}</div>{technical_html}</td></tr>')
    trend_html = " · ".join([*(f"{escape(label)} <b>{count}</b>" for label, count in trend_items), *(escape(label) for label in language_items)])
    if not trend_html:
        trend_html = empty if en else "暂无足够的项目样本形成趋势判断。"
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    data_note = ("Repository metadata is refreshed from GitHub at most daily for the top eight daily repositories." if en else "仓库元数据每天最多更新一次，仅覆盖当日 Trending 前 8 个项目。")
    return f'''<!doctype html><html><body style="margin:0;background:#f4f6f8;font-family:Arial,'Noto Sans SC',sans-serif;color:#172033"><table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:28px 12px"><table role="presentation" width="640" cellspacing="0" cellpadding="0" style="max-width:640px;background:#fff;border:1px solid #e5e7eb;border-radius:16px;padding:26px"><tr><td><div style="font-size:11px;letter-spacing:1.5px;color:#64748b">INSIGHTPRO · {now:%Y-%m-%d}</div><h1 style="font-size:24px;margin:10px 0 6px">{title}</h1><p style="margin:0;color:#64748b">{len(rows)} {('repositories' if en else '个趋势项目')} · {now:%H:%M}</p><h2 style="font-size:16px;margin:24px 0 8px">{trend_title}</h2><p style="font-size:14px;line-height:1.8;color:#334155">{trend_html}</p><h2 style="font-size:16px;margin:24px 0 8px">{repos_title}</h2><table role="presentation" width="100%" cellspacing="0" cellpadding="0">{''.join(cards) if cards else '<tr><td style="padding:20px 0;color:#64748b">'+escape(empty)+'</td></tr>'}</table><p style="margin-top:22px;color:#64748b;font-size:12px">{data_note}</p></td></tr></table></td></tr></table></body></html>'''
