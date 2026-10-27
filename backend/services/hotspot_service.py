"""Hotspot business logic — evaluation, scoring, and storage.

Extracted from routers/hotspots.py to fix the service→router layer violation
(startup_service was importing from routers.hotspots).
"""
import asyncio
import json
import logging
from datetime import datetime

from db import get_db
from services.intelligence_format import project

logger = logging.getLogger(__name__)


def _empty_eval_summary():
    return {"strong": 0, "worth": 0, "marginal": 0, "not_recommended": 0}


def _canonical_total(item: dict) -> float:
    dimensions = []
    for key in ("d1", "d2", "d3", "d4"):
        try:
            dimensions.append(max(0.0, min(10.0, float(item.get(key)))))
        except (TypeError, ValueError):
            break
    if len(dimensions) == 4:
        return round(round(sum(dimensions) / 4, 2), 1)
    try:
        return max(0.0, min(10.0, float(item.get("total"))))
    except (TypeError, ValueError):
        return 0.0


def _canonical_level(item: dict) -> str:
    total = _canonical_total(item)
    if total >= 8:
        return "Strongly Recommended"
    if total >= 6:
        return "Worth Doing"
    if total >= 4:
        return "Marginal"
    return "Not Recommended"


def _summarize_eval(items: list[dict]) -> dict:
    summary = _empty_eval_summary()
    for it in items:
        lvl = _canonical_level(it)
        if "Strongly Recommended" in lvl or "强烈推荐" in lvl:
            summary["strong"] += 1
        elif "Worth Doing" in lvl or "值得做" in lvl:
            summary["worth"] += 1
        elif "Marginal" in lvl or "勉强" in lvl:
            summary["marginal"] += 1
        elif "Not Recommended" in lvl or "不建议" in lvl:
            summary["not_recommended"] += 1
    return summary


_ZH_LEVELS = {"Strongly Recommended": "强烈推荐", "Worth Doing": "值得做",
              "Marginal": "勉强可做", "Not Recommended": "不建议"}
_HEURISTIC_REASON = "AI 不可用时，按客户痛点、场景适配、业务与云价值、标准化交付进行临时解决方案价值评估。"
_LEGACY_HEURISTIC_REASON = "When AI is unavailable, generate a temporary evaluation based on server-side attributes, independent deployment needs, scenario value, and standardization & reproducibility."


def _localize_evaluations(items: list[dict], locale: str) -> list[dict]:
    localized = []
    for item in items:
        copy = dict(item)
        copy["evaluation_mode"] = "heuristic" if copy.get("reasoning") in {_HEURISTIC_REASON, _LEGACY_HEURISTIC_REASON} else "ai"
        copy["total"] = _canonical_total(copy)
        level = _canonical_level(copy)
        copy["level"] = _ZH_LEVELS.get(level, level) if locale == "zh" else level
        if locale != "zh":
            copy["intelligence"] = project(copy)
            localized.append(copy)
            continue
        if copy.get("reasoning") in {_HEURISTIC_REASON, _LEGACY_HEURISTIC_REASON}:
            copy["summary"] = copy.get("summary_zh") or copy.get("summary") or f"{copy.get('repo_name') or '该项目'}：当前为规则估算，建议先验证客户痛点、适用场景和交付复制性。"
            copy["recommendation"] = "验证客户痛点、目标客户、业务收益、云资源必要性和跨客户复制路径。"
            copy["reasoning"] = _HEURISTIC_REASON
        else:
            copy["summary"] = copy.get("summary_zh") or copy.get("summary") or f"{copy.get('repo_name') or '该项目'}：AI 解决方案价值评估已完成。"
        copy["intelligence"] = project(copy)
        localized.append(copy)
    return localized


def _canonical_evaluations(cursor, rows: list[dict]) -> list[dict]:
    """Resolve every dated sighting of a repository to its first real AI analysis."""
    names = [row["repo_name"] for row in rows]
    if not names:
        return rows
    cursor.execute("""SELECT DISTINCT ON (repo_name) id, repo_name, summary, summary_zh,
                          d1, d2, d3, d4, total, level, recommendation, reasoning, eval_time
                      FROM trending_business_eval
                      WHERE repo_name = ANY(%s) AND reasoning IS NOT NULL
                        AND reasoning <> '' AND reasoning <> ALL(%s)
                      ORDER BY repo_name, scrape_date, id""",
                   (names, [_HEURISTIC_REASON, _LEGACY_HEURISTIC_REASON]))
    analyses = {row["repo_name"]: dict(row) for row in cursor.fetchall()}
    return [{**row, **analyses[row["repo_name"]], "analysis_id": analyses[row["repo_name"]]["id"]}
            if row["repo_name"] in analyses else row for row in rows]


def _heuristic_score_project(item: dict) -> dict:
    text = f"{item.get('repo_name', '')} {item.get('description', '')}".lower()
    pain_keywords = ["enterprise", "automation", "workflow", "analytics", "knowledge", "security", "monitoring", "search"]
    scenario_keywords = ["platform", "service", "api", "gateway", "agent", "saas", "team", "business"]
    value_keywords = ["enterprise", "productivity", "cost", "revenue", "automation", "analytics", "workflow", "cloud"]
    delivery_keywords = ["kubernetes", "docker", "helm", "terraform", "cloud", "deploy", "self-host", "api"]
    client_only_keywords = ["desktop", "browser extension", "chrome extension", "command-line", " cli ", "algorithm library"]

    def score(keywords: list[str], base: float) -> float:
        hits = sum(1 for kw in keywords if kw in text)
        return min(9.0, base + hits * 1.1)

    d1 = score(pain_keywords, 4.8)
    d2 = score(scenario_keywords, 4.8)
    d3 = score(value_keywords, 4.6)
    d4 = score(delivery_keywords, 4.2)
    total = round((d1 + d2 + d3 + d4) / 4, 1)
    if any(keyword in text for keyword in client_only_keywords):
        d2, total = min(d2, 3.0), min(total, 3.9)
    elif d1 < 4 or d2 < 4:
        total = min(total, 5.9)
    if total >= 8:
        level = "Strongly Recommended"
    elif total >= 6:
        level = "Worth Doing"
    elif total >= 4:
        level = "Marginal"
    else:
        level = "Not Recommended"
    return {
        "repo_name": item.get("repo_name", ""),
        "repo_url": item.get("repo_url"),
        "language": item.get("language"),
        "stars": item.get("stars"),
        "summary": f"{item.get('repo_name', '该项目')}：围绕{item.get('description') or '开源技术能力'}，可用于验证客户场景、业务价值和方案交付路径。",
        "d1": round(d1, 1),
        "d2": round(d2, 1),
        "d3": round(d3, 1),
        "d4": round(d4, 1),
        "total": total,
        "level": level,
        "recommendation": "验证客户痛点、目标客户、业务收益、云资源必要性和跨客户复制路径。",
        "reasoning": _HEURISTIC_REASON,
        "eval_time": datetime.now().strftime("%H:%M:%S"),
        "evaluation_mode": "heuristic",
    }


def _repository_evidence(repo: dict) -> dict:
    release = repo.get("latest_release") or {}
    evidence = {
        "description": repo.get("description"), "stars": repo.get("stars"), "forks": repo.get("forks"),
        "stars_delta": ((repo.get("scores") or {}).get("hot_score") or {}).get("stars_delta"),
        "today_stars": repo.get("today_stars"), "pushed_at": repo.get("pushed_at"),
        "contributors_count": repo.get("contributors_count"), "license": repo.get("license"),
        "topics": repo.get("topics"), "latest_release_tag": release.get("tag_name"),
        "latest_release_date": release.get("published_at"), "latest_release_major": release.get("major_release"),
        "latest_release_notes": release.get("body"),
    }
    return {key: value for key, value in evidence.items() if value not in (None, "", [])}


def _technical_assessment(value: object, repo: dict) -> dict:
    evidence = _repository_evidence(repo)
    allowed = {
        "engineering_maturity": {"pushed_at", "contributors_count", "latest_release_tag", "latest_release_date", "latest_release_notes", "latest_release_major"},
        "innovation": {"description", "topics", "latest_release_notes"},
        "deployability": {"description", "license", "latest_release_tag", "latest_release_notes"},
    }
    supplied = value if isinstance(value, dict) else {}
    result = {}
    for dimension in ("engineering_maturity", "innovation", "deployability"):
        item = supplied.get(dimension) if isinstance(supplied.get(dimension), dict) else {}
        keys = item.get("evidence_keys") if isinstance(item.get("evidence_keys"), list) else []
        keys = list(dict.fromkeys(key for key in keys if isinstance(key, str) and key in allowed[dimension] and evidence.get(key) is not None))[:8]
        score = item.get("score")
        valid = isinstance(score, (int, float)) and not isinstance(score, bool) and 0 <= score <= 10
        if not keys or not valid:
            score, keys = None, []
        reasoning = item.get("reasoning") if isinstance(item.get("reasoning"), str) else ""
        result[dimension] = {"score": score,
                             "reasoning": reasoning[:500] if score is not None else "可验证证据不足，暂不评分。",
                             "evidence_keys": keys}
    return result


async def _evaluate_live_items(items: list[dict], limit: int = 25) -> list[dict]:
    from services.ai_service import chat_complete
    from services.evaluation_service import BUSINESS_EVAL_SYSTEM_PROMPT, _parse_eval_json
    from services.prompt_service import published_prompt

    selected = items[:limit]
    if not selected:
        return []

    parsed = []
    try:
        active_prompt = await asyncio.to_thread(published_prompt, "repository_business_eval")
    except Exception as error:
        logger.warning("Repository evaluation prompt unavailable; using built-in compatibility prompt: %s", error)
        active_prompt = None
    system_prompt = active_prompt["system_prompt"] if active_prompt else BUSINESS_EVAL_SYSTEM_PROMPT
    async def evaluate_batch(batch: list[dict]) -> list[dict]:
        project_lines = [json.dumps({"repo_name": repo["repo_name"], "evidence": _repository_evidence(repo)},
                                    ensure_ascii=False) for repo in batch]
        user_prompt = (active_prompt.get("user_prompt_template") or "") if active_prompt else ""
        user_prompt = user_prompt.replace("{projects}", "\n".join(project_lines)) if "{projects}" in user_prompt else (
            "仅依据以下 JSON 证据，评估项目业务价值与技术成熟度。技术维度必须返回 engineering_maturity、innovation、deployability，每项含 score、reasoning、evidence_keys；证据不足时 score=null。只输出 JSON 数组，文字使用简体中文。\n\n" + "\n".join(project_lines))
        try:
            raw = await asyncio.to_thread(
                chat_complete,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=16384,
                timeout=180,
            )
            batch_result = _parse_eval_json(raw)
            return batch_result if isinstance(batch_result, list) else []
        except Exception as error:
            logger.warning("Insight-Agent evaluation failed for %s: %s", [repo["repo_name"] for repo in batch], error)
            return []

    for offset in range(0, len(selected), 5):
        parsed.extend(await evaluate_batch(selected[offset:offset + 5]))

    parsed_names = {item.get("repo_name") for item in parsed if isinstance(item, dict)}
    for repo in selected:
        if repo["repo_name"] not in parsed_names:
            retry = await evaluate_batch([repo])
            parsed.extend(retry)
            parsed_names.update(item.get("repo_name") for item in retry if isinstance(item, dict))

    if not parsed:
        return [_heuristic_score_project(item) for item in selected]

    enriched = []
    seen = set()
    for item in parsed:
        if not isinstance(item, dict):
            continue
        repo_name = item.get("repo_name", "")
        match = next((r for r in selected if r.get("repo_name") == repo_name), None)
        if not match or repo_name in seen:
            continue
        seen.add(repo_name)
        enriched.append({
           "repo_name": repo_name,
            "repo_url": match.get("repo_url") if match else None,
            "language": match.get("language") if match else None,
            "stars": match.get("stars") if match else None,
            "summary": item.get("summary") or "",
            "d1": item.get("d1"),
            "d2": item.get("d2"),
            "d3": item.get("d3"),
            "d4": item.get("d4"),
            "total": _canonical_total(item),
            "level": _canonical_level(item),
            "recommendation": item.get("recommendation") or "",
            "reasoning": item.get("reasoning") or "",
            "technical_assessment": _technical_assessment(item.get("technical_assessment"), match),
            "eval_time": datetime.now().strftime("%H:%M:%S"),
            "evaluation_mode": "ai",
            "prompt_name": active_prompt["prompt_name"] if active_prompt else None,
            "prompt_version": active_prompt["version"] if active_prompt else None,
        })
    enriched.extend(_heuristic_score_project(item) for item in selected if item.get("repo_name") not in seen)
    return enriched


def _store_live_evaluations(date_str: str, items: list[dict]) -> None:
    if not items:
        return
    with get_db() as conn:
        c = conn.cursor()
        for item in items:
            c.execute(
                """
                INSERT INTO trending_business_eval
                (scrape_date, repo_name, repo_url, language, stars, summary, d1, d2, d3, d4,
                 total, level, recommendation, reasoning, eval_time)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (scrape_date, repo_name) DO UPDATE SET
                  repo_url = EXCLUDED.repo_url,
                  language = EXCLUDED.language,
                  stars = EXCLUDED.stars,
                  summary = EXCLUDED.summary,
                  d1 = EXCLUDED.d1,
                  d2 = EXCLUDED.d2,
                  d3 = EXCLUDED.d3,
                  d4 = EXCLUDED.d4,
                  total = EXCLUDED.total,
                  level = EXCLUDED.level,
                  recommendation = EXCLUDED.recommendation,
                  reasoning = EXCLUDED.reasoning,
                  eval_time = EXCLUDED.eval_time
                WHERE trending_business_eval.reasoning IS NULL
                   OR trending_business_eval.reasoning = ANY(%s)
                """,
                (
                    date_str, item.get("repo_name"), item.get("repo_url"), item.get("language"),
                    item.get("stars"), item.get("summary"),
                    *(value.get("score") if isinstance(value, dict) else value
                      for value in (item.get("d1"), item.get("d2"), item.get("d3"), item.get("d4"))),
                    item.get("total"), item.get("level"),
                    item.get("recommendation"), item.get("reasoning"), item.get("eval_time"),
                    [_HEURISTIC_REASON, _LEGACY_HEURISTIC_REASON],
                ),
            )
