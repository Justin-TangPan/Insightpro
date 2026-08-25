"""深度研报路由"""
import os, json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from db import get_db
from services.ai_service import chat_complete, extract_json
from routers.auth import require_auth

router = APIRouter()


class DataSource(BaseModel):
    type: str
    content: Optional[str] = None
    file_url: Optional[str] = None


class TaskRequest(BaseModel):
    title: str
    data_sources: List[DataSource]
    depth: str = "standard"


def _ensure_baseline_report() -> None:
    """Create a completed baseline report when the report center has no data."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) AS cnt FROM insight_tasks WHERE status = %s", ("completed",))
        if c.fetchone()["cnt"] > 0:
            return

        c.execute("""
            SELECT repo_name, language, total, level, recommendation, reasoning
            FROM trending_business_eval
            ORDER BY total DESC NULLS LAST
            LIMIT 5
        """)
        eval_rows = [dict(r) for r in c.fetchall()]
        c.execute("""
            SELECT title, category, summary, last_changed_date
            FROM aliyun_solutions
            WHERE is_active=TRUE
            ORDER BY last_changed_date DESC, id DESC
            LIMIT 8
        """)
        solution_rows = [dict(r) for r in c.fetchall()]

        takeaways = []
        for r in eval_rows[:3]:
            takeaways.append(f"{r.get('repo_name')}：{r.get('level') or '待评估'}，建议：{r.get('recommendation') or '继续跟踪业务适配度'}")
        for r in solution_rows[:3]:
            takeaways.append(f"{r.get('category') or '技术方案'}：{r.get('title')}，{r.get('summary') or '待分析'}")

        result = {
            "summary_metrics": {
                "技术热点数量": len(eval_rows),
                "解决方案样本": len(solution_rows),
                "数据状态": 100 if eval_rows or solution_rows else 60,
            },
            "takeaways": takeaways or ["系统已完成基线巡检，暂无高置信度业务结论。"],
            "detailed_report": "本报告由系统基于 GitHub 技术热点评估和近期解决方案变化自动生成。可通过“新建分析”针对具体技术、方案或友商生成深度研报。",
            "strategies": {
                "短期": "优先跟进高分开源项目的企业部署场景和客户可演示方案。",
                "中期": "将技术热点、方案变化和友商能力统一纳入可复用选型模板。",
            },
        }
        task_id = "baseline_" + datetime.now().strftime("%Y%m%d")
        c.execute("""
            INSERT INTO insight_tasks (id, title, status, data_sources, result)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (
            task_id,
            f"系统基线洞察报告 {datetime.now().strftime('%Y-%m-%d')}",
            "completed",
            json.dumps([{"type": "SYSTEM", "content": "baseline insight from current platform data"}], ensure_ascii=False),
            json.dumps(result, ensure_ascii=False),
        ))


async def run_analysis(task_id: str, title: str, content: str):
    """异步运行AI分析逻辑"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE insight_tasks SET status = %s, updated_at = NOW() WHERE id = %s", ("processing", task_id))

    try:
        system_prompt = """你是一位世界顶级的商业分析师，任职于麦肯锡或高盛研究部。
你的任务是根据用户提供的关键词或数据，撰写一份专业、可执行的技术解决方案洞察报告。

输出要求：
1. 必须包含四个维度：技术问题、方案能力、友商对比、落地风险。
2. 必须包含三个方案指数（0-100）：技术成熟度、集成复杂度、落地适配度。
3. 必须包含详细的执行摘要和实施建议（短期与长期）。
4. 语言风格：专业、客观、直接，使用必要的技术术语，避开空话。
5. 必须基于已有数据进行分析，如需引用外部数据须标注来源和时效性，不得编造未经验证的数据。
6. 输出格式：JSON，包含字段：summary_metrics, takeaways, detailed_report, strategies."""

        safe_title = title[:200].replace("\n", " ").replace("\"", "'")
        safe_content = content[:5000].replace("\n", " ").replace("\"", "'")
        user_prompt = f"""任务标题: {safe_title}
分析背景数据: {safe_content}

请开始你的深度分析。"""

        result = chat_complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7, max_tokens=4096,
        )

        parsed = extract_json(result)
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE insight_tasks SET status = %s, result = %s, updated_at = NOW() WHERE id = %s",
                ("completed", json.dumps(parsed or {"raw": result}, ensure_ascii=False), task_id)
            )
        print(f"任务 {task_id} 深度分析完成")

    except Exception as e:
        error_msg = str(e)[:500]
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE insight_tasks SET status = %s, error = %s, updated_at = NOW() WHERE id = %s",
                ("failed", error_msg, task_id)
            )
        print(f"任务 {task_id} 分析失败: {error_msg}")


@router.post("/tasks/analyze")
async def analyze_task(request: TaskRequest, background_tasks: BackgroundTasks, _=Depends(require_auth)):
    from settings import settings
    if not settings.CHAT_API_KEY:
        raise HTTPException(status_code=500, detail="AI 服务未配置（CHAT_API_KEY 缺失）")

    task_id = "task_" + os.urandom(4).hex()
    combined_content = ""
    for source in request.data_sources:
        if source.type == "KEYWORD" and source.content:
            combined_content += source.content + "\n"
        elif source.type == "FILE" and source.file_url:
            combined_content += f"[文件引用: {source.file_url}]\n"

    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO insight_tasks (id, title, status, data_sources) VALUES (%s, %s, %s, %s)",
            (task_id, request.title, "pending",
             json.dumps([s.dict() for s in request.data_sources], ensure_ascii=False))
        )

    background_tasks.add_task(run_analysis, task_id, request.title, combined_content)
    return {"status": "processing", "task_id": task_id, "title": request.title, "message": "分析任务已启动"}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, _=Depends(require_auth)):
    """查询任务状态和结果"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, title, status, error, result, created_at, updated_at FROM insight_tasks WHERE id = %s", (task_id,))
        row = c.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="任务不存在")
    task = dict(row)
    if task.get("result"):
        try:
            task["result"] = json.loads(task["result"]) if isinstance(task["result"], str) else task["result"]
        except Exception:
            pass
    return task


@router.get("/reports")
async def list_reports(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    _=Depends(require_auth),
):
    """获取报告列表"""
    _ensure_baseline_report()
    with get_db() as conn:
        c = conn.cursor()
        where = "WHERE status = 'completed'" if not status else f"WHERE status = %s"
        params = [status] if status else []
        c.execute(f"SELECT COUNT(*) AS cnt FROM insight_tasks {where}", params)
        total = c.fetchone()["cnt"]
        c.execute(
            f"SELECT id, title, status, created_at, updated_at FROM insight_tasks {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params + [page_size, (page - 1) * page_size]
        )
        rows = c.fetchall()
    return {"items": [dict(r) for r in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/reports/{report_id}")
async def get_report(report_id: str, _=Depends(require_auth)):
    """获取报告详情"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, title, status, result, error, data_sources, created_at, updated_at FROM insight_tasks WHERE id = %s", (report_id,))
        row = c.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="报告不存在")
    report = dict(row)
    if report.get("result"):
        try:
            report["result"] = json.loads(report["result"]) if isinstance(report["result"], str) else report["result"]
        except Exception:
            pass
    if report.get("data_sources"):
        try:
            report["data_sources"] = json.loads(report["data_sources"]) if isinstance(report["data_sources"], str) else report["data_sources"]
        except Exception:
            pass
    return report


@router.delete("/reports/{report_id}")
async def delete_report(report_id: str, _=Depends(require_auth)):
    """删除报告"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM insight_tasks WHERE id = %s", (report_id,))
        if c.rowcount == 0:
            raise HTTPException(status_code=404, detail="报告不存在")
    return {"status": "success", "message": "报告已删除"}
