import asyncio
from types import SimpleNamespace

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


def test_agent_chat_runs_in_native_runtime(monkeypatch):
    monkeypatch.setattr(agent.agent_service, "get_session", lambda *_: {"id": "session-1", "conversation": []})
    monkeypatch.setattr(agent.agent_service, "record_turn", lambda *_: None)
    called = []

    async def native_stream(session, message):
        called.append((session["id"], message))
        yield "# Insight-Agent 结果"

    monkeypatch.setattr(agent.insight_agent_runtime, "stream_reply", native_stream)
    user = SimpleNamespace(id="user-1", email="user@example.com", app_metadata={"role": "user"}, user_metadata={"name": "User"})
    response = asyncio.run(agent.chat_stream(agent.ChatRequest(message="分析它", session_id="session-1"), user))

    async def body():
        return b"".join([chunk if isinstance(chunk, bytes) else chunk.encode() async for chunk in response.body_iterator])

    assert "Insight-Agent 结果" in asyncio.run(body()).decode()
    assert called == [("session-1", "分析它")]
