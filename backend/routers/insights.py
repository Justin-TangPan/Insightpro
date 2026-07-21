"""洞察路由 — 每日洞察、市场总览、行业分析"""
from fastapi import APIRouter, Query
from datetime import datetime, timedelta
from db import get_db
from services.ai_service import chat_complete, extract_json
from services.bidding_service import get_bidding_opportunities
from settings import settings

router = APIRouter()


@router.get("/daily-insight")
async def get_daily_insight():
    """获取今日商业市场洞察（从数据库实时聚合）"""
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    with get_db() as conn:
        c = conn.cursor()
        industry = []
        try:
            c.execute("SELECT title, source, url, category FROM industry_news WHERE crawl_date >= %s ORDER BY id DESC LIMIT 3", (week_ago,))
            for r in c.fetchall():
                industry.append({"name": r["source"], "summary": r["title"], "link": r["url"] or "#"})
        except Exception:
            pass

        hotspots = []
        try:
            c.execute("SELECT repo_name, description, repo_url, language FROM github_trending WHERE scrape_date = %s AND category = 'daily' ORDER BY id LIMIT 3", (today,))
            for r in c.fetchall():
                hotspots.append({"platform": r["language"] or "GitHub", "title": r["repo_name"], "link": r["repo_url"]})
        except Exception:
            pass

        news = []
        try:
            c.execute("SELECT title, url, source FROM industry_news ORDER BY id DESC LIMIT 3")
            for r in c.fetchall():
                news.append({"title": r["title"], "link": r["url"] or "#", "source": r["source"]})
        except Exception:
            pass

        opportunities = []
        try:
            c.execute("SELECT title, industry, budget, summary FROM bidding_opportunities WHERE bid_date >= %s ORDER BY relevance_score DESC LIMIT 3", (week_ago,))
            rows = c.fetchall()
            if not rows:
                c.execute("SELECT title, industry, budget, summary FROM bidding_opportunities ORDER BY relevance_score DESC NULLS LAST, id DESC LIMIT 3")
                rows = c.fetchall()
            for r in rows:
                opportunities.append({"target": r["industry"], "advice": r["summary"][:80] if r["summary"] else "", "opportunity": r["title"]})
        except Exception:
            pass

        policies = []
        try:
            c.execute("SELECT title, source, url FROM policy_updates WHERE crawl_date >= %s ORDER BY id DESC LIMIT 3", (week_ago,))
            for r in c.fetchall():
                policies.append({"title": r["title"], "source": r["source"], "link": r["url"] or "#"})
        except Exception:
            pass

    return {
        "date": today,
        "industry": industry,
        "hotspots": hotspots,
        "news": news,
        "opportunities": opportunities,
        "policies": policies,
    }


@router.get("/daily-insight/enhanced")
async def daily_insight_enhanced():
    """增强版每日洞察：RAG 检索 + AI 生成"""
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        from deep_searcher_integration import retrieve_context, context_to_str
        ctx = retrieve_context("今日数字化市场热点和行业动态", top_k=6)
        ctx_str = context_to_str(ctx)

        prompt = f"""你是一位资深商业分析师。基于以下信息，生成今日市场洞察摘要。

向量数据库信息:
{ctx_str[:2000]}

请输出 JSON:
{{
  "date": "{today}",
  "headline": "今日核心洞察标题",
  "hot_industries": ["行业1", "行业2", "行业3"],
  "key_insights": ["洞察1（含数据）", "洞察2", "洞察3"],
  "opportunity_alert": "今日最值得关注的商机",
  "risk_warning": "需要关注的风险因素",
  "action_items": ["建议行动1", "建议行动2"]
}}"""

        if settings.CHAT_API_KEY:
            insight_raw = chat_complete(
                messages=[
                    {"role": "system", "content": "你是资深分析师，输出结构化市场洞察 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5, max_tokens=800,
            )
            insight = extract_json(insight_raw)
            return insight or {"date": today}
        else:
            return {"date": today, "headline": "AI 洞察暂不可用"}
    except Exception as e:
        return {"error": str(e), "date": today}


@router.get("/market/overview")
async def market_overview():
    """市场总览：整合各维度数据生成全景洞察"""
    try:
        from deep_searcher_integration import retrieve_context, context_to_str
        ctx = retrieve_context("数字化市场全景洞察各行业发展趋势", top_k=10)
        ctx_str = context_to_str(ctx)

        industries_count = 8
        signals_count = 0
        tenders_count = 0
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT COUNT(DISTINCT industry) AS cnt FROM demand_signals WHERE signal_date >= (CURRENT_DATE - INTERVAL '30 days')")
                row = c.fetchone()
                if row and row["cnt"]:
                    industries_count = row["cnt"]
                c.execute("SELECT COUNT(*) AS cnt FROM demand_signals WHERE signal_date >= (CURRENT_DATE - INTERVAL '30 days')")
                signals_count = c.fetchone()["cnt"] or 0
                c.execute("SELECT COUNT(*) AS cnt FROM bidding_opportunities WHERE bid_date >= (CURRENT_DATE - INTERVAL '30 days')")
                tenders_count = c.fetchone()["cnt"] or 0
                if not tenders_count:
                    c.execute("SELECT COUNT(*) AS cnt FROM bidding_opportunities")
                    tenders_count = c.fetchone()["cnt"] or 0
        except Exception:
            pass

        if settings.CHAT_API_KEY:
            prompt = f"""基于以下数据，生成一份简洁的数字化市场全景洞察摘要：

覆盖行业: {industries_count} 个
需求信号: {signals_count} 条
招标信息: {tenders_count} 条

向量库检索到的相关信息:
{ctx_str[:2000]}

请生成结构化的市场总览 JSON：
{{
  "summary": "一句话总结",
  "market_status": "扩张/稳定/收缩",
  "top_industries": [{{"name": "行业名", "driver": "驱动因素", "growth": "增长判断"}}],
  "hot_tags": ["标签1", "标签2", "标签3"],
  "outlook": "趋势判断"
}}"""
            overview_raw = chat_complete(
                messages=[
                    {"role": "system", "content": "你是资深市场分析师，输出结构化 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5, max_tokens=800,
            )
            overview = extract_json(overview_raw)
        else:
            overview = {
                "summary": f"当前覆盖 {industries_count} 个行业",
                "market_status": "扩张",
                "top_industries": [],
                "hot_tags": ["AI赋能", "数字化转型", "信创替代"],
                "outlook": "数字化市场保持高速增长",
            }

        return {
            "overview": overview or {},
            "stats": {"industries": industries_count, "signals": signals_count, "tenders": tenders_count},
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    except Exception as e:
        return {"error": str(e), "stats": {"industries": 0, "signals": 0, "tenders": 0}}


@router.get("/market/heatmap")
async def market_heatmap():
    """市场热度热力图数据"""
    cutoff_30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    cutoff_7 = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    industry_stats = {}
    with get_db() as conn:
        c = conn.cursor()
        try:
            c.execute("SELECT industry, COUNT(*) AS cnt FROM demand_signals WHERE signal_date >= %s GROUP BY industry", (cutoff_30,))
            for r in c.fetchall():
                ind = r["industry"] or "通用"
                industry_stats.setdefault(ind, {})["demand_signals"] = r["cnt"]
        except Exception:
            pass
        try:
            c.execute("SELECT industry, COUNT(*) AS cnt FROM bidding_opportunities WHERE bid_date >= %s GROUP BY industry", (cutoff_30,))
            for r in c.fetchall():
                ind = r["industry"] or "通用"
                industry_stats.setdefault(ind, {})["bidding"] = r["cnt"]
        except Exception:
            pass
        try:
            c.execute("SELECT COUNT(*) AS cnt FROM policy_updates WHERE crawl_date >= %s", (cutoff_30,))
            policy_count = c.fetchone()["cnt"]
        except Exception:
            policy_count = 0
        try:
            c.execute("SELECT COUNT(*) AS cnt FROM industry_news WHERE crawl_date >= %s", (cutoff_7,))
            news_count = c.fetchone()["cnt"]
        except Exception:
            news_count = 0

    max_demand = max((v.get("demand_signals", 0) + v.get("bidding", 0)) for v in industry_stats.values()) or 1
    industries_heat = []
    all_industries = list(set(list(industry_stats.keys()) + ["政务", "医疗", "制造", "金融", "教育", "交通", "能源", "零售", "农业"]))
    for ind in all_industries:
        stats = industry_stats.get(ind, {})
        demand_count = stats.get("demand_signals", 0)
        bidding_count = stats.get("bidding", 0)
        total_signals = demand_count + bidding_count
        demand_score = min(90, 40 + int(total_signals / max(max_demand, 1) * 50))
        competition_score = min(90, 30 + min(news_count, 60))
        policy_score = min(95, 50 + min(policy_count * 2, 45))
        trend = f"+{min(total_signals * 3, 50)}%" if total_signals > 0 else "—"
        growth = "高速增长" if total_signals > 10 else "稳健增长" if total_signals > 3 else "增长中"
        industries_heat.append({
            "industry": ind, "demand": demand_score, "competition": competition_score,
            "policy": policy_score, "growth": growth, "trend": trend,
        })

    industries_heat.sort(key=lambda x: x["demand"], reverse=True)
    return {"items": industries_heat, "total": len(industries_heat), "source": "database"}


@router.get("/market/industry-analysis")
async def industry_analysis(industry: str = Query("制造", description="行业名称")):
    """指定行业的深度分析（含 RAG 检索）"""
    try:
        from deep_searcher_integration import retrieve_context, context_to_str
        query = f"{industry}行业数字化市场分析、需求趋势、竞争格局、机会点"
        ctx = retrieve_context(query, top_k=8)
        ctx_str = context_to_str(ctx)

        bids, _ = get_bidding_opportunities(industry=industry, days=60)
        bid_context = ""
        if bids:
            for b in bids[:5]:
                bid_context += f"- {b['title']}（预算: {b.get('budget','')}，截止: {b.get('deadline','')}）\n"

        prompt = f"""你是一位资深行业分析师。请分析{industry}行业的数字化市场。

向量数据库检索到的相关信息:
{ctx_str[:2500]}

近期相关招标:
{bid_context or '暂无'}

请输出以下格式（JSON）:
{{
  "industry": "{industry}",
  "market_size": "市场规模描述",
  "key_trends": ["趋势1", "趋势2", "趋势3"],
  "pain_points": ["痛点1", "痛点2"],
  "opportunities": [{{"title": "机会描述", "priority": "高/中", "action": "建议行动"}}],
  "competition": "竞争格局概述",
  "huawei_advantage": "华为云优势分析",
  "recommendation": "综合建议"
}}"""

        if settings.CHAT_API_KEY:
            analysis_raw = chat_complete(
                messages=[
                    {"role": "system", "content": "你是资深行业分析师，输出结构化 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5, max_tokens=1200,
            )
            analysis = extract_json(analysis_raw) or {}
        else:
            analysis = {"industry": industry}

        return {"analysis": analysis, "bids_count": len(bids[:5])}
    except Exception as e:
        return {"error": str(e)}
