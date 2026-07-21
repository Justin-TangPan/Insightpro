"""需求信号路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from routers.auth import require_auth
from typing import Optional
from services.demand_service import (
    collect_demand_signals, get_demand_signals, get_demand_trends,
)
from deep_searcher_integration import deep_research
from settings import settings
from datetime import datetime, timedelta
from db import get_db

router = APIRouter()


def _build_demand_fallback_report(industry: Optional[str] = None) -> str:
    from services.demand_service import get_demand_signals
    signals = get_demand_signals(industry=industry, days=30)
    selected = signals[:12]
    lines = [
        f"# {industry or '综合'}行业需求洞察报告",
        "",
        "## 摘要",
        f"近 30 天共识别 {len(signals)} 条需求信号，覆盖政策、招标、产业新闻等来源。当前报告为系统基于结构化数据生成的兜底摘要。",
        "",
        "## 重点信号",
    ]
    if selected:
        for s in selected:
            lines.append(f"- [{s.get('industry') or '综合'}][{s.get('source_type') or '未知来源'}] {s.get('title')}")
    else:
        lines.append("- 暂无匹配信号，建议先执行需求信号刷新。")
    lines.extend([
        "",
        "## 行动建议",
        "- 优先筛选高相关度行业信号，形成行业场景包。",
        "- 将招标、政策和技术热点联动，识别可落地的云服务机会。",
        "- 对高频需求标签建立周度复盘机制。",
    ])
    return "\n".join(lines)


@router.post("/demand/refresh")
async def refresh_demand(_=Depends(require_auth)):
    count = collect_demand_signals()
    return {"status": "success", "message": f"已采集 {count} 条需求信号", "count": count}


@router.get("/demand/signals")
async def demand_signals(
    industry: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=90),
):
    signals = get_demand_signals(industry=industry, source_type=source_type, days=days)
    return {"signals": signals, "count": len(signals)}


@router.get("/demand/trends")
async def demand_trends():
    return get_demand_trends()


@router.get("/demand/report")
async def demand_report(industry: Optional[str] = Query(None), _=Depends(require_auth)):
    """AI 生成行业需求洞察报告"""
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        query_text = f"分析{industry or '各行业'}数字化需求趋势和市场机会，按行业分类输出洞察报告"
        if industry:
            query_text = f"分析{industry}行业的数字化需求趋势、政策驱动因素和市场机会"
        result = await deep_research(query_text, max_iter=2)

        if result["answer"] and "错误" not in result["answer"][:20]:
            report_content = result["answer"]
        else:
            from services.demand_service import get_demand_signals
            signals = get_demand_signals(industry=industry, days=30)
            context = "以下是近期行业需求信号数据：\n\n"
            for s in signals[:20]:
                context += f"[{s['source_type']}] [{s['industry']}] {s['title']}\n{s['summary']}\n需求标签: {s.get('demand_tags','')}\n\n"
            prompt = f"""基于以下行业需求信号数据，生成一份专业的行业数字化需求洞察报告。

要求：
1. 按行业分类分析需求趋势
2. 识别高增长需求领域和市场机会
3. 分析政策驱动 vs 市场驱动的需求
4. 给出华为云在各行业的切入点建议
5. 输出格式：Markdown，包含标题、摘要、各行业分析、机会点、行动建议

{context}"""
            from services.ai_service import chat_complete
            report_content = chat_complete(
                messages=[
                    {"role": "system", "content": "你是资深行业分析师，擅长从数据中提炼商业洞察。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7, max_tokens=2000,
            )

        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO demand_reports (report_date, industry, title, content)
                VALUES (%s, %s, %s, %s)
            """, (today, industry or "综合", f"行业需求洞察报告 {today}", report_content))
        return {"report": report_content, "date": today}
    except Exception as e:
        report_content = _build_demand_fallback_report(industry)
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO demand_reports (report_date, industry, title, content)
                    VALUES (%s, %s, %s, %s)
                """, (today, industry or "综合", f"行业需求洞察报告 {today}", report_content))
        except Exception as insert_error:
            print(f"需求报告兜底写入失败: {insert_error}")
        return {"error": str(e), "report": report_content, "date": today, "source": "fallback"}


@router.get("/demand/report/history")
async def demand_report_history(days: int = Query(30, ge=1, le=90)):
    with get_db() as conn:
        c = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        c.execute("SELECT * FROM demand_reports WHERE report_date >= %s ORDER BY report_date DESC", (cutoff,))
        rows = c.fetchall()
        if not rows:
            today = datetime.now().strftime("%Y-%m-%d")
            report_content = _build_demand_fallback_report()
            c.execute("""
                INSERT INTO demand_reports (report_date, industry, title, content)
                VALUES (%s, %s, %s, %s)
            """, (today, "综合", f"行业需求洞察报告 {today}", report_content))
            c.execute("SELECT * FROM demand_reports WHERE report_date >= %s ORDER BY report_date DESC", (cutoff,))
            rows = c.fetchall()
    return {"reports": [dict(r) for r in rows]}
