from types import SimpleNamespace

from services import agent_service, context_service


def test_requirement_context_is_user_scoped(monkeypatch):
    monkeypatch.setattr(context_service.workbench_service, "get_requirement", lambda user_id, _: {
        "title": "可观测性", "description": "统一监控", "status": "draft", "priority": "high",
        "source_type": "manual", "source_id": None, "source_url": None, "solutions": [],
    })
    context = context_service.get_context("user-1", "requirement", "7")
    assert context["context_type"] == "requirement"
    assert context["metadata"]["priority"] == "high"


def test_confirm_requirement_action_creates_draft_from_snapshot(monkeypatch):
    proposal = {"status": "proposed", "session_id": "session-1", "action": "create_requirement_draft", "payload": {"title": "AI 草稿", "description": "背景", "priority": "medium"}}
    monkeypatch.setattr(agent_service.repository, "get_agent_action", lambda *_: proposal)
    monkeypatch.setattr(agent_service, "get_session", lambda *_: {"context_snapshot": {"context_type": "github_project", "context_id": "dify", "source_url": "https://github.com/langgenius/dify"}})
    created = []
    monkeypatch.setattr(agent_service.workbench_service, "create_requirement", lambda user_id, data: created.append((user_id, data)) or {"id": 8, **data})
    monkeypatch.setattr(agent_service.repository, "confirm_agent_action", lambda action_id, result: None)

    result = agent_service.confirm_action("user-1", "action-1")

    assert result["status"] == "draft"
    assert created[0][1]["source_type"] == "github_project"
    assert created[0][1]["source_id"] == "dify"
