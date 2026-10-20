import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from services import agent_service, context_service
from routers import agent


def test_requirement_context_is_user_scoped(monkeypatch):
    monkeypatch.setattr(context_service.workbench_service, "get_requirement", lambda user_id, _: {
        "title": "可观测性", "description": "统一监控", "status": "draft", "priority": "high",
        "source_type": "manual", "source_id": None, "source_url": None, "solutions": [],
    })
    context = context_service.get_context("user-1", "requirement", "7")
    assert context["context_type"] == "requirement"
    assert context["metadata"]["priority"] == "high"


def test_solution_context_includes_every_background_source_within_limit(monkeypatch):
    requested = []
    monkeypatch.setattr(context_service.workbench_service, "get_solution", lambda user_id, solution_id: requested.append((user_id, solution_id)) or {
        "name": "统一方案实践", "description": "方案背景", "category": "AI", "status": "draft",
        "version": "v0.1.0", "reference_url": "https://example.com/practice",
        "requirements": [
            {"id": 1, "title": "材料一", "description": "甲" * 20_000, "source_type": "github_project", "source_id": "repo-1", "source_url": "https://example.com/one"},
            {"id": 2, "title": "材料二", "description": "乙" * 20_000, "source_type": "cloud_solution", "source_id": "2", "source_url": "https://example.com/two"},
        ],
    })

    context = context_service.get_context("user-1", "solution", "9")

    assert requested == [("user-1", 9)]
    assert len(context["content"]) <= context_service.MAX_CONTENT
    assert "Solution Practice: 统一方案实践" in context["content"]
    assert "Source: https://example.com/practice" in context["content"]
    assert "Background Material: 材料一" in context["content"]
    assert "github_project / repo-1 / https://example.com/one" in context["content"]
    assert "Background Material: 材料二" in context["content"]
    assert "cloud_solution / 2 / https://example.com/two" in context["content"]
    assert context["metadata"]["background_count"] == 2


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


@pytest.mark.parametrize("context_type", ["chat", "solution", "github_project"])
def test_all_agent_chat_runs_in_local_hermes_core(monkeypatch, context_type):
    session_id = "00000000-0000-4000-8000-000000000002"
    user_id = "00000000-0000-4000-8000-000000000001"
    monkeypatch.setattr(agent.agent_service, "get_session", lambda *_: {"id": session_id, "context_type": context_type, "conversation": []})
    monkeypatch.setattr(agent.agent_service, "record_turn", lambda *_: None)
    monkeypatch.setattr(agent.context_repository, "save_runtime_history", lambda *_: None)
    monkeypatch.setattr(agent.ai_usage_service, "record", lambda *_: None)
    called = []

    async def hermes_chat(user_id, session, message, model):
        called.append((user_id, session["id"], message, model))
        yield {"type": "text.delta", "delta": "# Hermes Agent 结果"}
        yield {"type": "message.end", "text": "# Hermes Agent 结果", "hermes_session_id": "hermes-session"}

    async def no_action(*_):
        return None

    monkeypatch.setattr(agent.embedded_agent_service, "stream", hermes_chat)
    monkeypatch.setattr(agent, "_import_runtime_action", no_action)
    user = SimpleNamespace(id=user_id, email="user@example.com", app_metadata={"role": "user"}, user_metadata={"name": "User"})
    response = asyncio.run(agent.chat_stream(agent.ChatRequest(message="分析它", session_id=session_id), user))

    async def body():
        return b"".join([chunk if isinstance(chunk, bytes) else chunk.encode() async for chunk in response.body_iterator])

    assert "Hermes Agent 结果" in asyncio.run(body()).decode()
    assert called == [(user_id, session_id, "分析它", agent.settings.CHAT_MODEL)]


def test_runtime_action_is_validated_before_proposal(monkeypatch):
    action = {"session_id": "session-1", "action": "create_solution_draft", "payload": {"name": "Hermes 方案", "description": "待确认"}}
    proposed = []

    async def read_action(*_):
        return action

    async def clear_action(*args):
        proposed.append(("cleared", *args))

    monkeypatch.setattr(agent.agent_runtime_service, "read_action", read_action)
    monkeypatch.setattr(agent.agent_runtime_service, "clear_action", clear_action)
    monkeypatch.setattr(agent.agent_service, "propose_action", lambda *args: proposed.append(args) or {"id": "action-1", "status": "proposed", "action": args[2], "payload": args[3]})

    result = asyncio.run(agent._import_runtime_action("user-1", "session-1"))

    assert result["status"] == "proposed"
    assert proposed[0][2] == "create_solution_draft"
    assert proposed[0][3]["version"] == "v0.1.0"
    assert proposed[1] == ("cleared", "user-1", "session-1")


def test_runtime_context_bridge_requires_secret_and_keeps_user_scope(monkeypatch):
    monkeypatch.setattr(agent.settings, "HERMES_SSO_SECRET", "runtime-secret")
    requested = []
    monkeypatch.setattr(agent.agent_service, "get_session", lambda *args: requested.append(args) or {"id": args[1]})

    with pytest.raises(HTTPException) as denied:
        asyncio.run(agent.runtime_session_context("session-1", "wrong", "user-1"))
    assert denied.value.status_code == 403

    result = asyncio.run(agent.runtime_session_context("session-1", "runtime-secret", "user-1"))
    assert result == {"id": "session-1"}
    assert requested == [("user-1", "session-1")]
