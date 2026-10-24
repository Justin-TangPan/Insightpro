"""Compact, source-backed intelligence for each business board."""
from datetime import date, datetime, timedelta
from hashlib import sha256
import json
import logging
import re
import time
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit

from db import get_db
from services import ai_service
from services.prompt_service import published_prompt

logger = logging.getLogger(__name__)
BOARDS = {"github", "apps", "solutions", "competitors", "community"}
SHANGHAI = ZoneInfo("Asia/Shanghai")
FOCUS = {
    "github": "主要技术变化、热门项目方向；判断 Star/Trending 信号对云服务与商业市场的意义。",
    "apps": "新发布或更新的产品、能力变化、集中出现的应用类型和代表厂商。",
    "solutions": "以阿里云解决方案变化为主，华为云作为对照补充；判断变化明显的方案方向。",
    "community": "聚焦 AI 应用、Agent 与框架、模型、AI 开发工具和 AI Infra。识别跨来源共同话题及其讨论信号；发布时间缺失时不得称为今日发布或近期新趋势，也不得把社区观点说成厂商事实。",
    "competitors": "近 7 天内有动作的厂商、产品发布、能力更新、合作或商业动作及代表事件。",
}


def _legacy_rows(board: str, day: str) -> list[dict]:
    since = (date.fromisoformat(day) - timedelta(days=6)).isoformat()
    if board == "community":
        from services.community_insight_service import get_community_insights
        return [{key: row.get(key) for key in ("title", "summary", "url", "source", "topic_category", "relevance", "engagement", "published_at", "observed_at")}
                for row in get_community_insights()["items"] if row.get("title") and row.get("url")]
    sql = {
        "github": "SELECT repo_name AS title, COALESCE(description, '') AS summary, repo_url AS url, stars, today_stars, language, category FROM github_trending WHERE scrape_date BETWEEN %s AND %s AND repo_url IS NOT NULL ORDER BY scrape_date DESC, id DESC",
        "apps": "SELECT name AS title, COALESCE(summary, source_text, '') AS summary, url, vendor, capability, kind, published_at FROM vendor_ai_applications WHERE published_at IS NOT NULL AND LEFT(published_at, 10) BETWEEN %s AND %s AND kind!='product' ORDER BY published_at DESC, id DESC",
        "solutions": "SELECT title, COALESCE(change_summary, source_description, '') AS summary, url, vendor, category, CASE WHEN NOT is_active THEN '下线' WHEN first_seen_date=last_changed_date THEN '新增' ELSE '更新' END AS change_type FROM aliyun_solutions WHERE last_changed_date BETWEEN %s AND %s AND NOT is_baseline ORDER BY CASE vendor WHEN 'Alibaba Cloud' THEN 0 WHEN 'Huawei Cloud' THEN 1 ELSE 2 END, last_changed_date DESC, id DESC",
        "competitors": "SELECT title, COALESCE(summary, '') AS summary, link AS url, vendor, category, published_date, scrape_date AS observed_at, CASE WHEN published_date IS NULL THEN 'observed' ELSE 'published' END AS date_basis FROM competitor_news WHERE scrape_date BETWEEN %s AND %s AND link IS NOT NULL ORDER BY scrape_date DESC, id DESC",
    }[board]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (since, day))
        return [dict(row) for row in cursor.fetchall()]


def _event_rows(board: str, day: str) -> list[dict]:
    scope = {"github": "technology_ecosystem", "apps": "ai_applications", "solutions": "solutions",
             "community": "community_insights", "competitors": "competitor_dynamics"}[board]
    since = (date.fromisoformat(day) - timedelta(days=6)).isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT DISTINCT ON (event.id) event.id AS event_id,event.title,
                          COALESCE(event.summary,raw.content->>'summary','') AS summary,raw.canonical_url AS url,
                          source.name AS source,COALESCE(raw.content->>'vendor',entity.metadata->>'vendor','') AS vendor,
                          raw.content->>'category' AS category,raw.content->>'kind' AS kind,
                          raw.content->>'stars' AS stars,raw.content->>'today_stars' AS today_stars,
                          raw.content->>'language' AS language,raw.content->>'change_summary' AS change_summary,
                          CASE WHEN NULLIF(raw.content->>'removed_at','') IS NOT NULL THEN '下线' ELSE '更新' END AS change_type,
                          (SELECT COUNT(DISTINCT evidence2.raw_item_id)::int FROM intelligence_event_evidence evidence2
                           WHERE evidence2.event_id=event.id) AS evidence_count
                          FROM intelligence_events event
                          JOIN intelligence_event_evidence evidence ON evidence.event_id=event.id
                          JOIN intelligence_raw_items raw ON raw.id=evidence.raw_item_id
                          JOIN intelligence_sources source ON source.source_key=raw.source_key
                          LEFT JOIN intelligence_entities entity ON entity.entity_key=event.entity_key
                          WHERE event.status='active' AND %s=ANY(event.business_scopes)
                            AND COALESCE(event.published_at,event.event_at,raw.published_at,raw.observed_at)::date
                                BETWEEN %s::date AND %s::date
                          ORDER BY event.id,source.priority,raw.observed_at DESC,raw.id DESC""",
                       (scope, since, day))
        return [dict(row) for row in cursor.fetchall()]


def _rows(board: str, day: str) -> list[dict]:
    current = _event_rows(board, day)
    legacy = _legacy_rows(board, day)
    event_urls = {_url_key(str(row.get("url") or "")) for row in current}
    return current + [row for row in legacy if _url_key(str(row.get("url") or "")) not in event_urls]


def _short(value, limit: int) -> str:
    value = re.sub(r"<[^>]*>|[#*`_]+", "", str(value or ""))
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit].rstrip("，、； ")


def _source_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except ValueError:
        return False


def _url_key(value: str) -> str:
    parsed = urlsplit(value)
    key = f"{parsed.scheme.casefold()}://{parsed.netloc.casefold()}{parsed.path.rstrip('/')}"
    return f"{key}?{parsed.query}" if parsed.query else key


def _valid_summary(summary: dict) -> bool:
    if not isinstance(summary, dict) or summary.get("analysis_version") != 4 or "focus" not in summary or not _short(summary.get("judgment"), 160):
        return False
    focus = summary.get("focus")
    return focus is None or (isinstance(focus, dict) and all(
        isinstance(focus.get(key), str) and focus[key].strip()
        for key in ("title", "url", "why", "analysis", "impact")))


def _structured(raw: str, rows: list[dict]) -> dict:
    result = ai_service.extract_json(raw)
    if not isinstance(result, dict):
        raise ValueError("AI provider returned invalid JSON")
    judgment = _short(result.get("judgment"), 500).split("。", 1)[0].split("；", 1)[0].rstrip("，、； ")
    if judgment:
        judgment += "。"
    focus_id = result.get("focus_id")
    why = _short(result.get("focus_reason"), 600)
    analysis = _short(result.get("focus_analysis"), 1000)
    impact = _short(result.get("focus_impact"), 800)
    caveat = _short(result.get("focus_caveat"), 600)
    if not judgment or type(focus_id) is not int or not 1 <= focus_id <= len(rows) or any(len(item) < 8 for item in (why, analysis, impact)):
        raise ValueError("AI provider returned incomplete intelligence")
    row = rows[focus_id - 1]
    details = [str(row[key]) for key in ("vendor", "source", "change_type", "today_stars") if row.get(key)]
    return {"analysis_version": 4, "judgment": judgment, "focus": {"title": _short(row["title"], 200), "url": row["url"],
            "event_id": row.get("event_id"), "meta": _short(" · ".join(details), 50), "why": why, "analysis": analysis,
            "impact": impact, "caveat": caveat}}


def _metrics(board: str, rows: list[dict]) -> list[dict]:
    if board == "github":
        return [{"label": "Trending 项目", "value": len(rows)}]
    if board == "apps":
        return [{"label": label, "value": sum(row.get("kind") == kind for row in rows)}
                for kind, label in (("launch", "新发布"), ("update", "产品更新"))]
    if board == "solutions":
        return [{"label": label, "value": sum(row.get("change_type") == kind for row in rows)}
                for kind, label in (("新增", "新增"), ("更新", "更新"), ("下线", "下线"))]
    if board == "community":
        return [{"label": "当前话题", "value": len(rows)}, {"label": "社区来源", "value": len({row.get("source") for row in rows if row.get("source")})}]
    return [{"label": "厂商事件", "value": len(rows)}, {"label": "涉及厂商", "value": len({row.get("vendor") for row in rows if row.get("vendor")})}]


def _community_fallback(rows: list[dict]) -> dict:
    topics = "、".join(dict.fromkeys(row.get("topic_category") or "AI 讨论" for row in rows))
    lead = rows[0]
    return {"analysis_version": 4, "analysis_mode": "source_only", "judgment": f"当前 AI 社区热榜涉及{topics}。",
            "focus": {"title": _short(lead["title"], 90), "url": lead["url"], "event_id": lead.get("event_id"), "meta": _short(lead.get("source"), 50),
                      "why": "当前热榜中可核实的代表讨论。", "analysis": _short(lead.get("summary") or lead["title"], 260),
                      "impact": "可作为需求观察线索，尚不足以确认厂商动作或市场趋势。", "caveat": "话题发布日期未逐条核实。"}}


def _wait_for_source_refreshes() -> None:
    from services.task_service import required_source_tasks
    source_tasks = required_source_tasks()
    deadline = time.monotonic() + 90 * 60
    while True:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""SELECT EXISTS(
                SELECT 1 FROM platform_task_runs
                WHERE task_key = ANY(%s) AND status='running'
                  AND started_at > NOW() - INTERVAL '2 hours'
            ) AS present""", (source_tasks,))
            running = bool(cursor.fetchone()["present"])
        if not running:
            break
        if time.monotonic() >= deadline:
            raise TimeoutError("Source refresh tasks did not finish within 90 minutes")
        time.sleep(5)
    today = datetime.now(SHANGHAI).date().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT task_key,status FROM (
                            SELECT DISTINCT ON (task_key) task_key,status
                            FROM platform_task_runs
                              WHERE task_key=ANY(%s)
                              AND (started_at AT TIME ZONE 'Asia/Shanghai')::date=%s
                            ORDER BY task_key,started_at DESC
                        ) latest""", (list(source_tasks), today))
        states = {row["task_key"]: row["status"] for row in cursor.fetchall()}
    incomplete = [key for key in source_tasks if states.get(key) != "success"]
    if incomplete:
        raise RuntimeError("Source refreshes missing or unsuccessful today: " + ", ".join(incomplete))


def insight(board: str) -> dict:
    if board not in BOARDS:
        raise ValueError("Unknown board")
    day = datetime.now(SHANGHAI).date().isoformat()
    rows = _rows(board, day)
    unique_by_url = {}
    for row in rows:
        if _source_url(str(row.get("url") or "")):
            unique_by_url.setdefault(row["url"], row)
    unique = list(unique_by_url.values())
    fingerprint = sha256(json.dumps(unique, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()
    prompt_name = f"board_{board}"
    active_prompt = published_prompt(prompt_name)
    prompt_version = active_prompt["version"] if active_prompt else None
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT analysis, fingerprint, prompt_name, prompt_version FROM board_daily_insights WHERE board=%s AND insight_date=%s", (board, day))
        previous = cursor.fetchone()
    if previous and previous["fingerprint"] == fingerprint and previous.get("prompt_version") == prompt_version:
        try:
            cached = json.loads(previous["analysis"])
            if _valid_summary(cached):
                return {"date": day, "count": len(unique), "metrics": _metrics(board, unique), "summary": cached, "sources": unique,
                        "prompt_name": previous.get("prompt_name"), "prompt_version": previous.get("prompt_version")}
        except (TypeError, ValueError):
            pass
    if not unique:
        summary = {"analysis_version": 4, "judgment": "近 7 天暂无可核实的新增信息。" if board != "community" else "当前社区热榜暂无可读取的话题。", "focus": None}
    else:
        evidence_rows = unique
        if board == "github":
            def heat(row):
                match = re.search(r"\d[\d,]*", str(row.get("today_stars") or ""))
                return int(match.group().replace(",", "")) if match else 0
            evidence_rows = []
            for row in sorted(unique, key=heat, reverse=True)[:30]:
                stars = str(row.get("today_stars") or "")
                if "month" in stars.casefold():
                    stars = f"月度趋势榜热度：{stars}（非单日新增）"
                elif "week" in stars.casefold():
                    stars = f"周度趋势榜热度：{stars}（非单日新增）"
                evidence_rows.append({**row, "today_stars": stars})
        evidence = "\n".join(f"{n}. {json.dumps({('trending_stars' if board == 'github' and key == 'today_stars' else key): (str(value)[:110] if key == 'summary' else value) for key, value in row.items() if key != 'url'}, ensure_ascii=False, default=str)}" for n, row in enumerate(evidence_rows, 1))
        period = "当前热榜快照" if board == "community" else "近 7 天来源数据"
        fallback_prompt = (f"仅依据提供的{period}，输出一个 JSON 对象，不要 Markdown、代码块或前言。字段："
                  "judgment（一句话概括整体方向，尽量在80字内），focus_id（最值得深入分析的一个来源序号），"
                  "focus_reason（为何它在近期热度、变化幅度和业务价值上值得关注，100字内），"
                  "focus_analysis（只根据选中来源的标题和摘要解释已确认的变化，80到160字，不写未披露的功能、客户或集成），"
                  "focus_impact（对云服务或商业市场可能造成的影响，150字内），focus_caveat（证据边界，100字内）。"
                  "只能选一个焦点。热度须依据输入中的时间、Trending/Stars、讨论信号或更新规模判断，缺指标时不要称其最热；"
                  "总体判断要综合输入来源。事件解读只写来源明示的事实；GitHub热度数字须按字段值中的时间口径描述，不能将‘this month’说成单日；"
                  "不要把标题推断当作事实，不能凭标题声称实际采用、收入或产品成熟度；"
                  "影响是推断时注明可能；不得虚构指标、产品、采用率或事件。"
                  + ("社区话题的发布时间缺失时，只能描述为当前讨论信号，不得声称是今天发布或长期趋势；区分社区观点与厂商事实。" if board == "community" else "")
                  + f"本板块重点：{FOCUS[board]}")
        prompt = active_prompt["system_prompt"] if active_prompt else fallback_prompt
        default_user_prompt = f"板块：{board}；统计范围：{(date.fromisoformat(day) - timedelta(days=6)).isoformat()} 至 {day}（{period}）；总来源{len(unique)}条，提供{len(evidence_rows)}条高热代表样本：\n{evidence}"
        template = active_prompt.get("user_prompt_template") if active_prompt else ""
        user_prompt = template.replace("{{board}}", board).replace("{{date}}", day).replace("{{period}}", period).replace("{{evidence}}", evidence) if template else default_user_prompt
        try:
            raw = ai_service.chat_complete(system_prompt=prompt,
                user_prompt=user_prompt,
                max_tokens=2500, temperature=0.1, timeout=90)
            try:
                summary = _structured(raw, evidence_rows)
            except ValueError:
                compact = "\n".join(f"{n}. {row['title']} {row.get('vendor') or row.get('source') or row.get('category') or ''} {str(row.get('summary') or '')[:55]}" for n, row in enumerate(evidence_rows, 1))
                retry_prompt = ("输出严格 JSON，不要 Markdown。字段 judgment:string, focus_id:number, "
                                "focus_reason:string, focus_analysis:string, focus_impact:string, focus_caveat:string。"
                                "focus_id必须是一个真实来源序号；用一句话总评。focus_analysis只解释选中来源明示事实，不写额外功能；"
                                "focus_impact单独写可能的业务影响，focus_caveat写未知项。"
                                "只根据全部输入判断，不编造事实。"
                                f"业务重点：{FOCUS[board]}")
                raw = ai_service.chat_complete(system_prompt=retry_prompt,
                    user_prompt=f"{board}，{day}，总来源{len(unique)}条，以下{len(evidence_rows)}条高热代表样本：\n{compact}",
                    max_tokens=2500, temperature=0.1, timeout=90)
                summary = _structured(raw, evidence_rows)
        except Exception as exc:
            logger.warning("Daily board insight failed for %s: %s", board, exc)
            summary = _community_fallback(unique) if board == "community" else {"analysis_version": 4, "judgment": "近 7 天信息已收集，深入分析暂不可用。", "focus": None}
            if board == "community":
                try:
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""INSERT INTO board_daily_insights (board, insight_date, fingerprint, analysis,prompt_name,prompt_version)
                                          VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (board, insight_date) DO UPDATE SET
                                          fingerprint=EXCLUDED.fingerprint, analysis=EXCLUDED.analysis,
                                          prompt_name=EXCLUDED.prompt_name,prompt_version=EXCLUDED.prompt_version,generated_at=NOW()""",
                                       (board, day, fingerprint, json.dumps(summary, ensure_ascii=False), prompt_name if active_prompt else None, prompt_version))
                except Exception as cache_exc:
                    logger.warning("Could not cache source-only community insight: %s", cache_exc)
            return {"date": day, "count": len(unique), "metrics": _metrics(board, unique), "summary": summary, "sources": unique,
                    "prompt_name": prompt_name if active_prompt else None, "prompt_version": prompt_version}
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO board_daily_insights (board, insight_date, fingerprint, analysis,prompt_name,prompt_version)
                          VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (board, insight_date) DO UPDATE SET
                          fingerprint=EXCLUDED.fingerprint, analysis=EXCLUDED.analysis, prompt_name=EXCLUDED.prompt_name,
                          prompt_version=EXCLUDED.prompt_version,generated_at=NOW()""",
                       (board, day, fingerprint, json.dumps(summary, ensure_ascii=False), prompt_name if active_prompt else None, prompt_version))
    return {"date": day, "count": len(unique), "metrics": _metrics(board, unique), "summary": summary, "sources": unique,
            "prompt_name": prompt_name if active_prompt else None, "prompt_version": prompt_version}


def refresh_all() -> dict:
    _wait_for_source_refreshes()
    counts = {}
    for board in BOARDS:
        try:
            counts[board] = insight(board)["count"]
        except Exception:
            logger.exception("Daily insight refresh failed for %s", board)
            counts[board] = None
    return counts
