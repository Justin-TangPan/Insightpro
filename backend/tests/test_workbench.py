import pytest
from fastapi import HTTPException

from services import workbench_service
from repositories import workbench_repository


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


def test_legacy_requirements_are_absorbed_once(monkeypatch):
    state = {
        "requirements": [{
            "id": 7, "user_id": "user-1", "title": "可观测性", "description": "统一监控",
            "status": "planned", "source_type": "github_project", "source_url": "https://example.com/repo",
            "absorbed_at": None,
        }],
        "links": {},
        "solutions": [],
    }

    class Cursor:
        one = None
        many = []

        def execute(self, sql, params=()):
            normalized = " ".join(sql.split())
            if normalized.startswith("SELECT * FROM requirements"):
                self.many = [row.copy() for row in state["requirements"] if row["absorbed_at"] is None]
            elif normalized.startswith("SELECT s.id FROM solutions"):
                solution_id = state["links"].get(params[0])
                self.one = {"id": solution_id} if solution_id else None
            elif normalized.startswith("INSERT INTO solutions"):
                self.one = {"id": 20 + len(state["solutions"])}
                state["solutions"].append(params)
            elif normalized.startswith("INSERT INTO requirement_solutions"):
                state["links"][params[0]] = params[1]
            elif normalized.startswith("UPDATE requirements SET absorbed_at"):
                next(row for row in state["requirements"] if row["id"] == params[0])["absorbed_at"] = "now"

        def fetchall(self):
            return self.many

        def fetchone(self):
            return self.one

    class Connection:
        def cursor(self):
            return Cursor()

    class Database:
        def __enter__(self):
            return Connection()

        def __exit__(self, *_):
            pass

    monkeypatch.setattr(workbench_repository, "get_db", Database)

    assert workbench_repository.absorb_requirements_into_solutions() == 1
    assert workbench_repository.absorb_requirements_into_solutions() == 0
    assert len(state["solutions"]) == 1
    assert state["solutions"][0][4] == "active"
    assert state["links"] == {7: 20}
