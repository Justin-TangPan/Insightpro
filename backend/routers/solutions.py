"""Technical solution catalog routes."""
import asyncio
from fastapi import APIRouter, Depends, HTTPException

from routers.auth import require_auth
from services.aliyun_solution_service import get_solution_catalog, get_solution_detail, refresh_solution_catalogs

router = APIRouter()


@router.get("/solutions/catalog")
@router.get("/solutions/aliyun")  # compatibility with saved clients
async def solution_catalog():
    return await asyncio.to_thread(get_solution_catalog)


@router.get("/solutions/catalog/{solution_id}")
async def solution_detail(solution_id: int):
    item = await asyncio.to_thread(get_solution_detail, solution_id)
    if not item:
        raise HTTPException(status_code=404, detail="Solution not found")
    return item


@router.post("/solutions/catalog/refresh")
@router.post("/solutions/aliyun/refresh")  # compatibility with saved clients
async def refresh_solutions(_=Depends(require_auth)):
    return await asyncio.to_thread(refresh_solution_catalogs)
