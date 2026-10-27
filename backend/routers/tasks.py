"""Administrator task-center routes."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from routers.auth import require_admin
from services.task_service import TASK_BY_KEY, list_tasks, recent_runs, run_task, set_daily_brief_schedule_enabled
from services.system_health_service import get_collection_report
from services.pipeline_service import start_pipeline, execute_pipeline, recent_pipelines
from services.admin_overview_service import overview

router = APIRouter()


class BriefScheduleRequest(BaseModel):
    enabled: bool


@router.get("/admin/overview")
async def admin_overview(_=Depends(require_admin)):
    from asyncio import to_thread
    return await to_thread(overview)


@router.get("/admin/collection")
async def collection_status(_=Depends(require_admin)):
    from asyncio import to_thread
    return await to_thread(get_collection_report)


@router.get("/admin/tasks")
async def tasks(limit: int = Query(50, ge=1, le=200), _=Depends(require_admin)):
    return {"tasks": list_tasks(), "runs": recent_runs(limit)}


@router.post("/admin/tasks/{task_key}/run", status_code=202)
async def trigger_task(task_key: str, background_tasks: BackgroundTasks, _=Depends(require_admin)):
    if task_key not in TASK_BY_KEY:
        raise HTTPException(status_code=404, detail="Task not found")
    background_tasks.add_task(run_task, task_key, "manual")
    return {"status": "accepted", "task_key": task_key}


@router.patch("/admin/tasks/daily_ai_brief/schedule")
async def configure_daily_brief_schedule(body: BriefScheduleRequest, request: Request, _=Depends(require_admin)):
    set_daily_brief_schedule_enabled(body.enabled)
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler and scheduler.get_job("daily_ai_brief"):
        (scheduler.resume_job if body.enabled else scheduler.pause_job)("daily_ai_brief")
    return {"enabled": body.enabled}


@router.get("/admin/daily-ai-brief/versions")
async def daily_brief_versions(limit: int = Query(60, ge=1, le=200), _=Depends(require_admin)):
    from services.daily_ai_brief_service import versions
    return {"items": versions(limit)}


@router.post("/admin/daily-ai-brief/retry-email", status_code=202)
async def retry_daily_brief_email(background_tasks: BackgroundTasks, _=Depends(require_admin)):
    from services.email_service import retry_business_emails
    background_tasks.add_task(run_task, "scheduled_email", "manual", retry_business_emails)
    return {"status": "accepted", "task_key": "scheduled_email"}


@router.get("/admin/pipelines")
async def pipelines(_=Depends(require_admin)):
    return {"items": recent_pipelines()}


@router.post("/admin/pipelines/{domain}/run", status_code=202)
async def trigger_pipeline(domain: str, background_tasks: BackgroundTasks,
                           resume_from: Optional[int] = Query(None, ge=1), _=Depends(require_admin)):
    try:
        run = start_pipeline(domain, resume_from)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    background_tasks.add_task(execute_pipeline, run["run_id"], domain, run["steps"])
    return {"status": "accepted", **run}
