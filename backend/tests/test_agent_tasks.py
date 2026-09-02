import pytest

from fastapi import HTTPException

from services import agent_task_service
from services import agent_service


def test_business_action_resolves_to_a_server_owned_task():
    key, task = agent_task_service.resolve("cloud_solution", "analyze")
    assert key == "solution_analysis"
    assert task["title"] == "分析解决方案"
    assert "技术架构" in task["prompt"]


def test_unsupported_action_is_rejected_before_context_is_read():
    with pytest.raises(HTTPException) as error:
        agent_task_service.resolve("requirement", "implement")
    assert error.value.status_code == 422


def test_artifact_uses_only_the_callers_session_output(monkeypatch):
    monkeypatch.setattr(agent_service, "get_session", lambda *_: {
        "id": "session-1", "task_key": "solution_analysis", "task_title": "分析解决方案",
        "context_snapshot": {"context_type": "solution", "context_id": "7"},
        "conversation": [{"role": "assistant", "content": "第一版"}, {"role": "assistant", "content": "最终结论"}],
    })
    stored = []
    monkeypatch.setattr(agent_service.artifact_repository, "create", lambda *args: stored.append(args) or {"id": "artifact-1"})
    assert agent_service.create_artifact("user-1", "session-1", "", "Markdown") == {"id": "artifact-1"}
    assert stored[0][0] == "user-1"
    assert stored[0][-1] == "最终结论"


def test_page_chat_keeps_the_opening_page_context(monkeypatch):
    captured = []
    monkeypatch.setattr(agent_service.repository, "create_chat_session", lambda *args: captured.append(args) or {"id": args[0]})
    agent_service.create_chat_session("user-1", "方案详情", "/workbench/solutions/7")
    assert captured[0][2:] == ("方案详情", "/workbench/solutions/7")
