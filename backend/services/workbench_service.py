"""Business rules for the Insight → Requirement → Solution workbench."""
from __future__ import annotations

from fastapi import HTTPException

from repositories import workbench_repository as repository


def _required(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise HTTPException(status_code=422, detail=f"{label}不能为空")
    return value


def list_requirements(user_id: str, status: str | None = None):
    return repository.list_requirements(user_id, status)


def get_requirement(user_id: str, requirement_id: int):
    item = repository.get_requirement(user_id, requirement_id)
    if not item:
        raise HTTPException(status_code=404, detail="Requirement 不存在")
    return item


def create_requirement(user_id: str, data: dict):
    data["title"] = _required(data["title"], "标题")
    return repository.create_requirement(user_id, data)


def update_requirement(user_id: str, requirement_id: int, data: dict):
    if "title" in data:
        data["title"] = _required(data["title"], "标题")
    item = repository.update_requirement(user_id, requirement_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Requirement 不存在")
    return item


def delete_requirement(user_id: str, requirement_id: int):
    if not repository.delete_requirement(user_id, requirement_id):
        raise HTTPException(status_code=404, detail="Requirement 不存在")


def list_solutions(user_id: str):
    return repository.list_solutions(user_id)


def get_solution(user_id: str, solution_id: int):
    item = repository.get_solution(user_id, solution_id)
    if not item:
        raise HTTPException(status_code=404, detail="Solution 不存在")
    return item


def create_solution(user_id: str, data: dict, requirement_id: int | None = None):
    data["name"] = _required(data["name"], "名称")
    item = repository.create_solution(user_id, data, requirement_id)
    if not item:
        raise HTTPException(status_code=404, detail="关联的 Requirement 不存在")
    return item


def update_solution(user_id: str, solution_id: int, data: dict):
    if "name" in data:
        data["name"] = _required(data["name"], "名称")
    item = repository.update_solution(user_id, solution_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Solution 不存在")
    return item


def delete_solution(user_id: str, solution_id: int):
    if not repository.delete_solution(user_id, solution_id):
        raise HTTPException(status_code=404, detail="Solution 不存在")


def link_solution(user_id: str, requirement_id: int, solution_id: int):
    if not repository.link_solution(user_id, requirement_id, solution_id):
        raise HTTPException(status_code=404, detail="Requirement 或 Solution 不存在")


def unlink_solution(user_id: str, requirement_id: int, solution_id: int):
    if not repository.unlink_solution(user_id, requirement_id, solution_id):
        raise HTTPException(status_code=404, detail="关联关系不存在")


def get_summary(user_id: str):
    return repository.get_summary(user_id)
