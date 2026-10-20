import pytest
import asyncio
import json
from types import SimpleNamespace

from fastapi import HTTPException

from routers import agent
from repositories import context_repository
from services import agent_task_service
from services import agent_service
from services import insight_agent_runtime
from services import ai_usage_service


def test_business_action_resolves_to_a_server_owned_task():
    key, task = agent_task_service.resolve("cloud_solution", "analyze")
    assert key == "solution_analysis"
    assert task["title"] == "Analyze Solution"
    assert "open-source projects" in task["prompt"]
    assert "cloud service resource" in task["prompt"]
    assert "not confirmed" in task["prompt"]


def test_fake_stream_chunker_is_removed():
    assert not hasattr(agent, "_text_chunks")


def test_native_stream_forwards_chunks_through_heartbeat_wrapper():
    async def source():
        yield "a"
        yield "b"

    async def collect():
        return [item async for item in agent._heartbeat_chunks(source())]

    assert asyncio.run(collect()) == ["a", "b"]


def test_solution_practice_action_uses_the_enabled_sac_workflow():
    key, task = agent_task_service.resolve("solution", "architecture")
    assert key == "solution_practice"
    assert task["title"] == "Create Solution Practice"
    assert "sac-project" in task["prompt"]
    assert "Architecture Contract" in task["prompt"]
    assert "background information" in task["prompt"]


def test_solution_home_requires_value_story_and_two_rfs_deliverables():
    messages = insight_agent_runtime.messages_for({
        "context_type": "chat",
        "context_snapshot": {"page_path": "/workbench/ai"},
        "conversation": [],
    }, "建设企业知识库")
    system = messages[0]["content"]
    assert all(item in system for item in ("application scenarios", "solution advantages", "applicable customers", "cloud-stack.tf", "deploy-guide.md", "do not invoke deployments"))


def test_model_selection_is_limited_to_configured_models(monkeypatch):
    monkeypatch.setattr(insight_agent_runtime.settings, "CHAT_MODEL", "fast")
    assert insight_agent_runtime.resolve_model(None) == "fast"
    assert insight_agent_runtime.available_models() == ("fast",)
    with pytest.raises(ValueError):
        insight_agent_runtime.resolve_model("careful")


def test_usage_accepts_openai_and_provider_token_names():
    assert ai_usage_service._token_counts({"prompt_tokens": 12, "completion_tokens": 8}) == (12, 8)
    assert ai_usage_service._token_counts({"input_tokens": 5, "output_tokens": 3}) == (5, 3)


def test_unsupported_action_is_rejected_before_context_is_read():
    with pytest.raises(HTTPException) as error:
        agent_task_service.resolve("requirement", "implement")
    assert error.value.status_code == 422


def test_artifact_uses_only_the_callers_session_output(monkeypatch):
    monkeypatch.setattr(agent_service, "get_session", lambda *_: {
        "id": "session-1", "task_key": "solution_analysis", "task_title": "Analyze Solution",
        "context_snapshot": {"context_type": "solution", "context_id": "7"},
        "conversation": [{"role": "assistant", "content": "First version"}, {"role": "assistant", "content": "Final conclusion"}],
    })
    stored = []
    monkeypatch.setattr(agent_service.artifact_repository, "create", lambda *args: stored.append(args) or {"id": "artifact-1"})
    assert agent_service.create_artifact("user-1", "session-1", "", "Markdown") == {"id": "artifact-1"}
    assert stored[0][0] == "user-1"
    assert stored[0][5] == "Final conclusion"
    assert stored[0][6] == "Analyze Solution.md"
    assert stored[0][7] == "text/markdown"


def test_page_chat_keeps_the_opening_page_context(monkeypatch):
    captured = []
    monkeypatch.setattr(agent_service.repository, "create_chat_session", lambda *args: captured.append(args) or {"id": args[0]})
    monkeypatch.setattr(agent_service.context_service, "get_context", lambda *_: {"title": "实践七", "content": "完整背景"})
    agent_service.create_chat_session("user-1", "方案详情", "/workbench/solutions/7", " 页面可见正文\0 ")
    assert captured[0][2:] == ("方案详情", "/workbench/solutions/7", "页面可见正文", {"title": "实践七", "content": "完整背景"})


def test_page_chat_never_fetches_external_or_unowned_context(monkeypatch):
    monkeypatch.setattr(agent_service.context_service, "get_context", lambda *_: (_ for _ in ()).throw(pytest.fail("must not fetch context")))
    captured = []
    monkeypatch.setattr(agent_service.repository, "create_chat_session", lambda *args: captured.append(args) or {"id": args[0]})
    agent_service.create_chat_session("user-1", "外部页面", "/insights/solutions?url=https", "公开正文")
    assert captured[0][-1] is None


def test_empty_session_delete_is_user_scoped(monkeypatch):
    deleted = []
    cleaned = []
    monkeypatch.setattr(agent_service.artifact_repository, "delete_knowledge_for_session", lambda user_id, session_id: cleaned.append((user_id, session_id)))
    monkeypatch.setattr(agent_service.repository, "delete_agent_session", lambda user_id, session_id: deleted.append((user_id, session_id)) or True)
    agent_service.delete_session("user-1", "empty-session")
    assert deleted == [("user-1", "empty-session")]
    assert cleaned == [("user-1", "empty-session")]


def test_missing_or_unowned_session_cannot_be_deleted(monkeypatch):
    monkeypatch.setattr(agent_service.artifact_repository, "delete_knowledge_for_session", lambda *_: None)
    monkeypatch.setattr(agent_service.repository, "delete_agent_session", lambda *_: False)
    with pytest.raises(HTTPException) as error:
        agent_service.delete_session("user-2", "empty-session")
    assert error.value.status_code == 404


def test_page_text_and_internal_context_are_persisted_in_snapshot(monkeypatch):
    class Cursor:
        params = ()

        def execute(self, _query, params):
            self.params = params

        def fetchone(self):
            return {"context_snapshot": json.loads(self.params[4])}

    cursor = Cursor()

    class Database:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return cursor

    monkeypatch.setattr(context_repository, "get_db", Database)
    result = context_repository.create_chat_session("session-1", "user-1", "方案详情", "/workbench/solutions/7", "页面正文", {"title": "实践七", "content": "完整背景"})
    assert result["context_snapshot"] == {
        "page_title": "方案详情", "page_path": "/workbench/solutions/7", "page_text": "页面正文",
        "business_context": {"title": "实践七", "content": "完整背景"},
    }


def test_generated_text_files_are_parsed_and_validated(monkeypatch):
    reply = "交付如下。\n```file:部署指南.md\n# 部署\n```\n```file:../secret.md\nno\n```\n```file:run.exe\nno\n```"
    files = insight_agent_runtime.generated_files(reply)
    monkeypatch.setattr(agent_service, "get_session", lambda *_: {
        "id": "session-1", "task_key": "materials", "context_snapshot": {"context_type": "solution", "context_id": "7"},
    })
    stored = []

    def create(*args):
        stored.append(args)
        return {"id": "artifact-1", "session_id": "session-1", "title": args[3], "type": args[4], "filename": args[6], "mime_type": args[7], "size_bytes": len(args[5].encode())}

    monkeypatch.setattr(agent_service.artifact_repository, "create", create)
    artifacts = agent_service.create_generated_artifacts("user-1", "session-1", files)
    assert [item["filename"] for item in artifacts] == ["部署指南.md"]
    assert stored[0][5] == "# 部署\n"
    cleaned = insight_agent_runtime.reply_without_files(reply, {"部署指南.md"})
    assert cleaned.startswith("交付如下。")
    assert "部署指南.md" not in cleaned
    assert "../secret.md" in cleaned


def test_file_only_reply_keeps_a_short_history_message():
    assert insight_agent_runtime.reply_without_files("```file:data.csv\na,b\n1,2\n```", {"data.csv"}) == "Files generated."


def test_generated_file_rejects_more_than_100kb(monkeypatch):
    monkeypatch.setattr(agent_service, "get_session", lambda *_: {"id": "session-1", "context_snapshot": {}})
    monkeypatch.setattr(agent_service.artifact_repository, "create", lambda *_: pytest.fail("oversized file must not be stored"))
    assert agent_service.create_generated_artifacts("user-1", "session-1", [{"filename": "large.txt", "content": "界" * 40000}]) == []


def test_history_file_references_are_not_sent_to_model():
    session = {
        "conversation": [{"role": "assistant", "content": "完成", "artifacts": [{"id": "file-1"}]}],
        "context_snapshot": {},
    }
    assert insight_agent_runtime.messages_for(session, "继续")[-2] == {"role": "assistant", "content": "完成"}


def test_download_uses_owned_artifacts_real_metadata(monkeypatch):
    requested = []
    monkeypatch.setattr(agent.agent_service, "get_artifact", lambda user_id, artifact_id: requested.append((user_id, artifact_id)) or {
        "content": '{"ok": true}', "title": "结果", "filename": "结果.json", "mime_type": "application/json",
    })
    response = asyncio.run(agent.download_artifact("artifact-1", SimpleNamespace(id="user-1")))
    assert requested == [("user-1", "artifact-1")]
    assert response.body == b'{"ok": true}'
    assert response.headers["content-type"] == "application/json; charset=utf-8"
    assert response.headers["content-disposition"].endswith("%E7%BB%93%E6%9E%9C.json")
    assert response.headers["x-content-type-options"] == "nosniff"


def test_stream_returns_file_metadata_and_history_reference(monkeypatch):
    monkeypatch.setattr(agent.agent_service, "get_session", lambda *_: {"id": "session-1", "context_type": "chat", "conversation": []})

    async def model_stream(*_):
        yield {"type": "text.delta", "delta": "已完成。"}
        yield {"type": "message.end", "text": "已完成。\n```file:result.csv\na,b\n1,2\n```"}

    artifact = {"id": "artifact-1", "session_id": "session-1", "title": "result.csv", "filename": "result.csv", "mime_type": "text/csv", "size_bytes": 8, "type": "CSV", "knowledge_status": "private", "created_at": "2026-09-02T00:00:00Z"}
    monkeypatch.setattr(agent.embedded_agent_service, "stream", model_stream)
    monkeypatch.setattr(agent.context_repository, "save_runtime_history", lambda *_: None)
    monkeypatch.setattr(agent.ai_usage_service, "record", lambda *_: None)
    monkeypatch.setattr(agent.agent_service, "create_generated_artifacts", lambda *_: [artifact])
    recorded = []
    monkeypatch.setattr(agent.agent_service, "record_turn", lambda *args: recorded.append(args))
    response = asyncio.run(agent.chat_stream(agent.ChatRequest(message="生成 CSV", session_id="session-1"), SimpleNamespace(id="user-1")))

    async def body():
        return b"".join([chunk if isinstance(chunk, bytes) else chunk.encode() async for chunk in response.body_iterator]).decode()

    output = asyncio.run(body())
    assert '"artifacts": [{"id": "artifact-1"' in output
    assert recorded[0][3] == "已完成。"
    assert recorded[0][4][0]["filename"] == "result.csv"
