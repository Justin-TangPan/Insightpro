"""Technical solution catalog routes."""
import asyncio
from fastapi import APIRouter, Depends

from routers.auth import require_auth
from services.aliyun_solution_service import get_aliyun_solutions, refresh_aliyun_solutions

router = APIRouter()


@router.get("/solutions/aliyun")
async def aliyun_solutions():
    return await asyncio.to_thread(get_aliyun_solutions)


@router.post("/solutions/aliyun/refresh")
async def refresh_solutions(_=Depends(require_auth)):
    return await asyncio.to_thread(refresh_aliyun_solutions)
