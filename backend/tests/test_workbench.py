import pytest
from fastapi import HTTPException

from services import workbench_service


def test_requirement_and_solution_flow(monkeypatch):
    calls = []
    monkeypatch.setattr(
        workbench_service.repository,
        "create_requirement",
        lambda user_id, data: {"id": 7, "user_id": user_id, **data},
    )
    monkeypatch.setattr(
        workbench_service.repository,
        "create_solution",
        lambda user_id, data, requirement_id: calls.append((user_id, requirement_id)) or {"id": 9, **data},
    )
    requirement = workbench_service.create_requirement("user-1", {"title": "  可观测性建设  "})
    solution = workbench_service.create_solution("user-1", {"name": "  统一监控方案  "}, requirement["id"])

    assert requirement["title"] == "可观测性建设"
    assert solution["name"] == "统一监控方案"
    assert calls == [("user-1", 7)]


def test_workbench_rejects_blank_names():
    with pytest.raises(HTTPException) as error:
        workbench_service.create_requirement("user-1", {"title": "  "})
    assert error.value.status_code == 422
