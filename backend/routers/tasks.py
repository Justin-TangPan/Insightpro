"""Administrator task-center routes."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from routers.auth import require_admin
from services.task_service import TASK_BY_KEY, list_tasks, recent_runs, run_task

router = APIRouter()


@router.get("/admin/tasks")
async def tasks(limit: int = Query(50, ge=1, le=200), _=Depends(require_admin)):
    return {"tasks": list_tasks(), "runs": recent_runs(limit)}


@router.post("/admin/tasks/{task_key}/run", status_code=202)
async def trigger_task(task_key: str, background_tasks: BackgroundTasks, _=Depends(require_admin)):
    if task_key not in TASK_BY_KEY:
        raise HTTPException(status_code=404, detail="Task not found")
    background_tasks.add_task(run_task, task_key, "manual")
    return {"status": "accepted", "task_key": task_key}
