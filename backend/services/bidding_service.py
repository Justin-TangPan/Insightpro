"""
招标业务逻辑
封装招标信息的采集、查询、统计、分析功能。
"""
import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional
from db import get_db
from settings import settings
from services.ai_service import chat_complete


def parse_budget_yuan(text) -> Optional[int]:
    """把预算文本归一化成整数元，无法解析返回 None。
    支持: 1.5亿元 / 500万元 / 1.5亿 / 500万 / 1,500,000元 / 100-200万元（取较大值）
    """
    if not text:
        return None
    s = str(text).strip().replace(",", "").replace(" ", "").replace("￥", "").replace("¥", "")
    if not s:
        return None
    matches = re.findall(r'(\d+(?:\.\d+)?)(亿|万)?元', s)
    if not matches:
        matches = re.findall(r'(\d+(?:\.\d+)?)(亿|万)', s)
    if not matches:
        m = re.search(r'(\d+(?:\.\d+)?)', s)
        matches = [(m.group(1), "")] if m else []
    if not matches:
        return None
    best = None
    for num_str, unit in matches:
        try:
            val = float(num_str)
        except ValueError:
            continue
        if unit == "亿":
            val *= 100_000_000
        elif unit == "万":
            val *= 10_000
        if best is None or val > best:
            best = val
    return int(round(best)) if best is not None else None


def backfill_budget_amount():
    """幂等回填：把有 budget 文本但 budget_amount 为空的老数据补上归一化金额。"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, budget FROM bidding_opportunities WHERE budget_amount IS NULL AND budget IS NOT NULL AND budget != ''")
        rows = c.fetchall()
        if not rows:
            return
        for row in rows:
            amt = parse_budget_yuan(row["budget"])
            if amt is not None:
                c.execute("UPDATE bidding_opportunities SET budget_amount = %s WHERE id = %s", (amt, row["id"]))
        print(f"[backfill] 补全 {len(rows)} 条招标预算金额")


def collect_bidding_data():
    """采集招标信息 — 使用 crawl_bidding() 爬虫，增量 upsert"""
    today = datetime.now().strftime("%Y-%m-%d")
    from crawlers import crawl_bidding
    items = crawl_bidding()
    if not items:
        print(f"[{today}] 招标爬虫未返回数据")
        return 0

    with get_db() as conn:
        c = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        c.execute("DELETE FROM bidding_opportunities WHERE bid_date < %s", (cutoff,))

        for item in items:
            budget_text = item.get("budget", "")
            c.execute("""
                INSERT INTO bidding_opportunities
                (bid_date, industry, title, procuring_entity, budget, budget_amount, deadline, summary,
                 requirements, qualification, contact, url, source, status, relevance_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (bid_date, title) DO UPDATE SET
                    industry = EXCLUDED.industry,
                    budget = EXCLUDED.budget,
                    budget_amount = EXCLUDED.budget_amount,
                    url = EXCLUDED.url,
                    source = EXCLUDED.source,
                    status = EXCLUDED.status,
                    relevance_score = EXCLUDED.relevance_score
            """, (item.get("bid_date") or today, item.get("industry", "政务"), item["title"],
                  item.get("procuring_entity", ""), budget_text, parse_budget_yuan(budget_text),
                  item.get("deadline", ""), item.get("summary", ""),
                  "", "", "", item.get("url", ""), item.get("source", ""), "open",
                  item.get("relevance_score", 0.5)))
    print(f"[{today}] 招标爬虫获取 {len(items)} 条")
    return len(items)


def get_bidding_opportunities(industry=None, status=None, days=30, page=None, page_size=None):
    with get_db() as conn:
        c = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        base_where = "WHERE bid_date >= %s"
        params = [cutoff]
        if industry:
            base_where += " AND industry = %s"
            params.append(industry)
        if status:
            base_where += " AND status = %s"
            params.append(status)

        count_query = f"SELECT COUNT(*) AS cnt FROM bidding_opportunities {base_where}"
        c.execute(count_query, params)
        total = c.fetchone()["cnt"]

        order_clause = " ORDER BY (budget_amount IS NULL), budget_amount DESC, relevance_score DESC"
        query = f"SELECT * FROM bidding_opportunities {base_where}{order_clause}"
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            query += " LIMIT %s OFFSET %s"
            params.extend([page_size, offset])
        c.execute(query, params)
        rows = c.fetchall()
        return [dict(r) for r in rows], total


def get_bidding_stats():
    """招标统计"""
    with get_db() as conn:
        c = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        c.execute("""
            SELECT industry, COUNT(*) as count, SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) as open_count,
                   ROUND(AVG(relevance_score)::numeric, 2) as avg_score
            FROM bidding_opportunities WHERE bid_date >= %s
            GROUP BY industry ORDER BY count DESC
        """, (cutoff,))
        by_industry = [dict(r) for r in c.fetchall()]

        c.execute("SELECT COUNT(*) AS total FROM bidding_opportunities WHERE bid_date >= %s", (cutoff,))
        total = c.fetchone()["total"]
        c.execute("SELECT COUNT(*) AS cnt FROM bidding_opportunities WHERE bid_date >= %s AND status='open'", (cutoff,))
        open_count = c.fetchone()["cnt"]

        c.execute(
            "SELECT COALESCE(SUM(budget_amount), 0) AS total_yuan, COUNT(budget_amount) AS with_budget "
            "FROM bidding_opportunities WHERE bid_date >= %s AND budget_amount IS NOT NULL",
            (cutoff,),
        )
        budget_row = c.fetchone()
        total_yuan = budget_row["total_yuan"] if budget_row else 0
        with_budget = budget_row["with_budget"] if budget_row else 0
        if total_yuan > 0:
            yi = total_yuan / 100_000_000
            if yi >= 1:
                total_budget = f"约 {yi:.2f} 亿元（{with_budget} 条含预算）"
            else:
                total_budget = f"约 {total_yuan / 10_000:.0f} 万元（{with_budget} 条含预算）"
        else:
            total_budget = "暂无预算数据"

        return {
            "total": total,
            "open_count": open_count,
            "by_industry": by_industry,
            "total_budget": total_budget,
        }


def analyze_bidding():
    """AI 分析招标机会"""
    items, total_count = get_bidding_opportunities(days=30)
    if not items:
        return {"analysis": "暂无招标数据，请先刷新", "total": 0}

    context = "以下是近期招标信息汇总：\n\n"
    for item in items[:15]:
        context += f"[{item['industry']}] {item['title']}\n  招标方: {item.get('procuring_entity','')} | 预算: {item.get('budget','')} | 截止: {item.get('deadline','')}\n  摘要: {item.get('summary','')[:100]}\n\n"

    prompt = f"""基于以下招标信息，生成一份专业的招标市场分析报告。

要求：
1. 按行业分类分析招标需求热点和趋势
2. 识别高价值标段（预算大、紧迫度高）
3. 分析各行业的数字化建设重点方向
4. 给出华为云在标的中的竞争优劣势和切入点建议
5. 输出格式：Markdown，包含标题、摘要、各行业分析、重点推荐标段、行动建议

{context}"""

    try:
        if not settings.CHAT_API_KEY:
            return {"analysis": "AI 未配置", "total": len(items)}
        analysis_text = chat_complete(
            messages=[
                {"role": "system", "content": "你是资深招标分析师，擅长从招标信息中挖掘商机。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=2500,
        )
        return {"analysis": analysis_text, "total": len(items)}
    except Exception as e:
        return {"error": str(e), "analysis": None, "total": len(items)}
