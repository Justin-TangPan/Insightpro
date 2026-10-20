"""Business evaluation and project summary generation for GitHub Trending."""
import json
import logging
import asyncio

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from db import get_db
from settings import settings

logger = logging.getLogger(__name__)


BUSINESS_EVAL_SYSTEM_PROMPT = """You are an expert in evaluating the solution value of open-source projects. Do not score GitHub popularity or the word AI; judge whether the project can become a valuable, repeatable customer solution. Use four dimensions, each 0-10, total = 0.25*(d1+d2+d3+d4):
[D1 Customer Pain & Urgency] How important and costly is the customer problem, and is there a credible reason to solve it now?
[D2 Scenario Fit & Customer Coverage] Are target customers, use cases, and adoption boundaries clear and broad enough for a solution?
[D3 Business Value & Cloud Consumption] Can the project create measurable business value and a justified cloud-resource or service-consumption path?
[D4 Standardized Delivery & Replication] Can 80% of the solution be fixed, differences parameterized, and delivery verified and reproduced across customers?
Admission constraint: when D1 or D2 < 4, total score is capped at 5.9; when no credible scenario, customer value, or reproducible delivery path exists, total score is capped at 5.9. Pure desktop tools, browser extensions, standalone scripts, and algorithm libraries are generally not recommended.
Rating: 8-10 Strongly Recommended / 6-7.9 Worth Doing / 4-5.9 Marginal / 0-3.9 Not Recommended.
recommendation must give concrete next validation steps; reasoning must address customer pain, scenario fit, business/cloud value, and standardized delivery. Write summary, level, recommendation, and reasoning in Simplified Chinese. Output only a single JSON array. Each element: {"repo_name":"owner/repo","summary":"中文项目价值摘要","d1":number,"d2":number,"d3":number,"d4":number,"total":number,"level":"Strongly Recommended/Worth Doing/Marginal/Not Recommended","recommendation":"中文下一步建议","reasoning":"中文评分依据"}"""


def _parse_eval_json(raw: str) -> list:
    if not raw:
        return []
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        return json.loads(text[start:end+1])
    except Exception as e:
        logger.debug("eval JSON parse failed: %s", e)
        return []


def translate_project_summaries(limit: int = 25) -> dict:
    """Generate missing Chinese briefs outside the page read path."""
    from services.ai_service import chat_complete
    from services.hotspot_service import _HEURISTIC_REASON

    date_str = datetime.now().strftime("%Y-%m-%d")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT e.repo_name, e.summary,
                      COALESCE(NULLIF(e.summary, ''), g.description) AS source
               FROM trending_business_eval e
               LEFT JOIN github_trending g ON g.scrape_date = e.scrape_date
                    AND g.repo_name = e.repo_name AND g.category = 'daily'
               WHERE e.scrape_date = %s AND e.reasoning <> %s
                 AND CHAR_LENGTH(COALESCE(NULLIF(e.summary, ''), g.description, '')) >= 20
                 AND COALESCE(e.summary_zh, '') = ''
               ORDER BY e.id LIMIT %s""",
            (date_str, _HEURISTIC_REASON, limit),
        )
        rows = cursor.fetchall()

    def translate(row):
        try:
            translated = chat_complete(
                system_prompt="Translate this GitHub project brief into natural Simplified Chinese. Preserve names and technical facts. Return plain text only.",
                user_prompt=row["source"], temperature=0.1, max_tokens=512, timeout=60,
            ).strip()
            if not any("\u4e00" <= char <= "\u9fff" for char in translated):
                raise ValueError("translation contains no Chinese")
            return row["repo_name"], row["summary"], translated
        except Exception as exc:
            logger.warning("Chinese brief failed for %s: %s", row["repo_name"], exc)
            return None

    count = 0
    with ThreadPoolExecutor(max_workers=2) as executor:
        for future in as_completed(executor.submit(translate, row) for row in rows):
            result = future.result()
            if result:
                with get_db() as conn:
                    conn.cursor().execute(
                        "UPDATE trending_business_eval SET summary_zh = %s WHERE scrape_date = %s AND repo_name = %s AND summary IS NOT DISTINCT FROM %s",
                        (result[2], date_str, result[0], result[1]),
                    )
                count += 1
    return {"status": "success" if count == len(rows) else "partial_success", "count": count, "requested": len(rows)}


def evaluate_trending_business(limit: int = 25) -> dict:
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M:%S")
    from services.hotspot_service import _HEURISTIC_REASON, _LEGACY_HEURISTIC_REASON, _heuristic_score_project
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""SELECT g.repo_name, g.repo_url, g.description, g.language, g.stars
                     FROM github_trending g LEFT JOIN trending_business_eval e
                       ON e.scrape_date = g.scrape_date AND e.repo_name = g.repo_name
                     WHERE g.scrape_date = %s AND g.category = 'daily'
                     ORDER BY g.id LIMIT %s""", (date_str, limit))
        rows = c.fetchall()
    if not rows:
        return {"status": "success", "count": 0, "date": date_str}
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""SELECT DISTINCT ON (repo_name) repo_name, summary, summary_zh, d1, d2, d3, d4, total, level, recommendation, reasoning, eval_time
                     FROM trending_business_eval WHERE repo_name = ANY(%s)
                       AND reasoning IS NOT NULL AND reasoning <> '' AND reasoning <> ALL(%s)
                     ORDER BY repo_name, scrape_date ASC, id ASC""",
                  ([row["repo_name"] for row in rows], [_HEURISTIC_REASON, _LEGACY_HEURISTIC_REASON]))
        existing = {row["repo_name"]: dict(row) for row in c.fetchall() if row.get("reasoning")}
    # Keep scheduled/manual evaluation on the same Insight-Agent runtime as the page refresh path.
    from services.hotspot_service import _evaluate_live_items
    missing = [dict(row) for row in rows if row["repo_name"] not in existing]
    fresh = asyncio.run(_evaluate_live_items(missing, limit)) if missing and settings.CHAT_API_KEY else [_heuristic_score_project(row) for row in missing]
    results = [{**dict(row), **existing[row["repo_name"]], "evaluation_mode": "ai"} for row in rows if row["repo_name"] in existing] + fresh
    if not results:
        return {"status": "error", "count": 0}
    with get_db() as conn:
        c = conn.cursor()
        for item in results:
            rn = item.get("repo_name", "")
            if not rn:
                continue
            match = next((r for r in rows if r["repo_name"] == rn), None)
            c.execute("INSERT INTO trending_business_eval (scrape_date, repo_name, repo_url, language, stars, summary, summary_zh, d1, d2, d3, d4, total, level, recommendation, reasoning, eval_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (scrape_date, repo_name) DO UPDATE SET summary=EXCLUDED.summary, summary_zh=EXCLUDED.summary_zh, d1=EXCLUDED.d1, d2=EXCLUDED.d2, d3=EXCLUDED.d3, d4=EXCLUDED.d4, total=EXCLUDED.total, level=EXCLUDED.level, recommendation=EXCLUDED.recommendation, reasoning=EXCLUDED.reasoning, eval_time=EXCLUDED.eval_time WHERE trending_business_eval.reasoning IS NULL OR trending_business_eval.reasoning = ANY(%s)",
                (date_str, rn, match["repo_url"] if match else None, match["language"] if match else None, match["stars"] if match else None,
                 item.get("summary"), item.get("summary_zh"), item.get("d1"), item.get("d2"), item.get("d3"), item.get("d4"), item.get("total"), item.get("level"), item.get("recommendation"), item.get("reasoning"), time_str, [_HEURISTIC_REASON, _LEGACY_HEURISTIC_REASON]))
        c.execute("""WITH canonical AS (
                       SELECT DISTINCT ON (repo_name) repo_name, id
                       FROM trending_business_eval
                       WHERE repo_name=ANY(%s) AND reasoning IS NOT NULL
                         AND reasoning <> '' AND reasoning <> ALL(%s)
                       ORDER BY repo_name, scrape_date, id
                     )
                     UPDATE trending_business_eval e SET analysis_id=canonical.id
                     FROM canonical WHERE e.repo_name=canonical.repo_name
                       AND e.analysis_id IS DISTINCT FROM canonical.id""",
                  ([row["repo_name"] for row in rows], [_HEURISTIC_REASON, _LEGACY_HEURISTIC_REASON]))
    logger.info("business eval done, %d items", len(results))
    complete = len(results) == len(rows) and all(item.get("evaluation_mode") != "heuristic" for item in results)
    return {"status": "success" if complete else "partial_success", "count": len(results), "date": date_str}


def backfill_project_analyses(limit: int = 25) -> dict:
    """Analyze historical projects that have never had a real AI evaluation."""
    if not settings.CHAT_API_KEY:
        return {"status": "skipped", "count": 0}
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT DISTINCT ON (e.repo_name) e.scrape_date, e.repo_name, e.repo_url,
                              e.language, e.stars, g.description
                          FROM trending_business_eval e
                          LEFT JOIN LATERAL (
                            SELECT description FROM github_trending g
                            WHERE g.repo_name=e.repo_name ORDER BY g.scrape_date DESC LIMIT 1
                          ) g ON TRUE
                          WHERE e.analysis_id IS NULL
                          ORDER BY e.repo_name, e.scrape_date LIMIT %s""", (limit,))
        rows = [dict(row) for row in cursor.fetchall()]
    if not rows:
        return {"status": "success", "count": 0}
    from services.hotspot_service import _evaluate_live_items, _HEURISTIC_REASON, _LEGACY_HEURISTIC_REASON
    results = asyncio.run(_evaluate_live_items(rows, limit))
    dates = {row["repo_name"]: row["scrape_date"] for row in rows}
    completed = [item for item in results if item.get("evaluation_mode") == "ai"]
    with get_db() as conn:
        cursor = conn.cursor()
        for item in completed:
            cursor.execute("""UPDATE trending_business_eval SET summary=%s, summary_zh=NULL,
                              d1=%s, d2=%s, d3=%s, d4=%s, total=%s, level=%s,
                              recommendation=%s, reasoning=%s, eval_time=%s
                              WHERE repo_name=%s AND scrape_date=%s
                                AND (reasoning IS NULL OR reasoning='' OR reasoning=ANY(%s))""",
                           (item["summary"], item["d1"], item["d2"], item["d3"], item["d4"],
                            item["total"], item["level"], item["recommendation"], item["reasoning"],
                            item["eval_time"], item["repo_name"], dates[item["repo_name"]],
                            [_HEURISTIC_REASON, _LEGACY_HEURISTIC_REASON]))
        cursor.execute("""WITH canonical AS (
                           SELECT DISTINCT ON (repo_name) repo_name, id
                           FROM trending_business_eval
                           WHERE repo_name=ANY(%s) AND reasoning IS NOT NULL
                             AND reasoning <> '' AND reasoning <> ALL(%s)
                           ORDER BY repo_name, scrape_date, id
                         )
                         UPDATE trending_business_eval e SET analysis_id=canonical.id
                         FROM canonical WHERE e.repo_name=canonical.repo_name
                           AND e.analysis_id IS DISTINCT FROM canonical.id""",
                       ([item["repo_name"] for item in completed], [_HEURISTIC_REASON, _LEGACY_HEURISTIC_REASON]))
    return {"status": "success" if len(completed) == len(rows) else "partial_success",
            "count": len(completed), "requested": len(rows)}
