"""Technical solution catalog routes."""
import asyncio
from fastapi import APIRouter, Depends

from routers.auth import require_auth
from services.aliyun_solution_service import get_solution_catalog, refresh_solution_catalogs

router = APIRouter()


@router.get("/solutions/catalog")
@router.get("/solutions/aliyun")  # compatibility with saved clients
async def solution_catalog():
    return await asyncio.to_thread(get_solution_catalog)


@router.post("/solutions/catalog/refresh")
@router.post("/solutions/aliyun/refresh")  # compatibility with saved clients
async def refresh_solutions(_=Depends(require_auth)):
    return await asyncio.to_thread(refresh_solution_catalogs)
