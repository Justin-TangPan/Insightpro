"""Authenticated Requirements and Solutions workbench API."""
from __future__ import annotations

import asyncio
from typing import Literal, Optional, Set

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field, HttpUrl

from routers.auth import require_auth
from services import workbench_service as service

router = APIRouter(prefix="/workbench")
RequirementStatus = Literal["draft", "active", "planned", "completed", "archived"]
Priority = Literal["low", "medium", "high", "critical"]
SolutionStatus = Literal["draft", "active", "deprecated", "archived"]


class RequirementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    status: RequirementStatus = "draft"
    priority: Priority = "medium"
    source_type: str = Field(default="manual", max_length=50)
    source_id: Optional[str] = Field(default=None, max_length=200)
    source_url: Optional[HttpUrl] = None


class RequirementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[RequirementStatus] = None
    priority: Optional[Priority] = None
    source_type: Optional[str] = Field(default=None, max_length=50)
    source_id: Optional[str] = Field(default=None, max_length=200)
    source_url: Optional[HttpUrl] = None


class SolutionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    category: str = Field(default="未分类", max_length=100)
    status: SolutionStatus = "draft"
    version: str = Field(default="v0.1.0", max_length=50)
    reference_url: Optional[HttpUrl] = None
    requirement_id: Optional[int] = Field(default=None, gt=0)


class SolutionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    category: Optional[str] = Field(default=None, max_length=100)
    status: Optional[SolutionStatus] = None
    version: Optional[str] = Field(default=None, max_length=50)
    reference_url: Optional[HttpUrl] = None


def _data(model, *, exclude: Optional[Set[str]] = None, unset: bool = False) -> dict:
    data = model.model_dump(exclude=exclude or set(), exclude_unset=unset)
    return {key: str(value) if isinstance(value, HttpUrl) else value for key, value in data.items()}


@router.get("/summary")
async def summary(user=Depends(require_auth)):
    return await asyncio.to_thread(service.get_summary, str(user.id))


@router.get("/requirements")
async def requirements(status: Optional[RequirementStatus] = None, user=Depends(require_auth)):
    return await asyncio.to_thread(service.list_requirements, str(user.id), status)


@router.post("/requirements", status_code=status.HTTP_201_CREATED)
async def create_requirement(payload: RequirementCreate, user=Depends(require_auth)):
    return await asyncio.to_thread(service.create_requirement, str(user.id), _data(payload))


@router.get("/requirements/{requirement_id}")
async def requirement(requirement_id: int, user=Depends(require_auth)):
    return await asyncio.to_thread(service.get_requirement, str(user.id), requirement_id)


@router.put("/requirements/{requirement_id}")
async def update_requirement(requirement_id: int, payload: RequirementUpdate, user=Depends(require_auth)):
    return await asyncio.to_thread(service.update_requirement, str(user.id), requirement_id, _data(payload, unset=True))


@router.delete("/requirements/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement(requirement_id: int, user=Depends(require_auth)):
    await asyncio.to_thread(service.delete_requirement, str(user.id), requirement_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/requirements/{requirement_id}/solutions/{solution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def link_solution(requirement_id: int, solution_id: int, user=Depends(require_auth)):
    await asyncio.to_thread(service.link_solution, str(user.id), requirement_id, solution_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/requirements/{requirement_id}/solutions/{solution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_solution(requirement_id: int, solution_id: int, user=Depends(require_auth)):
    await asyncio.to_thread(service.unlink_solution, str(user.id), requirement_id, solution_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/solutions")
async def solutions(user=Depends(require_auth)):
    return await asyncio.to_thread(service.list_solutions, str(user.id))


@router.post("/solutions", status_code=status.HTTP_201_CREATED)
async def create_solution(payload: SolutionCreate, user=Depends(require_auth)):
    data = _data(payload, exclude={"requirement_id"})
    return await asyncio.to_thread(service.create_solution, str(user.id), data, payload.requirement_id)


@router.get("/solutions/{solution_id}")
async def solution(solution_id: int, user=Depends(require_auth)):
    return await asyncio.to_thread(service.get_solution, str(user.id), solution_id)


@router.put("/solutions/{solution_id}")
async def update_solution(solution_id: int, payload: SolutionUpdate, user=Depends(require_auth)):
    return await asyncio.to_thread(service.update_solution, str(user.id), solution_id, _data(payload, unset=True))


@router.delete("/solutions/{solution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_solution(solution_id: int, user=Depends(require_auth)):
    await asyncio.to_thread(service.delete_solution, str(user.id), solution_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
