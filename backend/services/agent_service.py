"""Session snapshots and human-confirmed Insight-Agent business actions."""
from __future__ import annotations

import re
from uuid import uuid4
from fastapi import HTTPException

from repositories import artifact_repository, context_repository as repository
from services import agent_task_service, context_service, workbench_service

MAX_ARTIFACT_BYTES = 100 * 1024
MIME_TYPES = {
    ".md": "text/markdown", ".txt": "text/plain", ".csv": "text/csv",
    ".json": "application/json", ".yaml": "application/yaml", ".yml": "application/yaml",
    ".tf": "text/plain", ".py": "text/x-python", ".js": "text/javascript",
    ".jsx": "text/javascript", ".ts": "text/typescript", ".tsx": "text/typescript",
    ".sh": "text/x-shellscript", ".sql": "application/sql", ".html": "text/html",
    ".css": "text/css", ".xml": "application/xml", ".toml": "application/toml",
    ".ini": "text/plain", ".go": "text/plain", ".java": "text/plain",
    ".c": "text/plain", ".h": "text/plain", ".cpp": "text/plain", ".rs": "text/plain",
}


def create_session(user_id: str, context_type: str, context_id: str) -> dict:
    context = context_service.get_context(user_id, context_type, context_id)
    return repository.create_agent_session(str(uuid4()), user_id, context)


def route_session(user_id: str, context_type: str, context_id: str, action_key: str) -> dict:
    task_key, task = agent_task_service.resolve(context_type, action_key)
    context = context_service.get_context(user_id, context_type, context_id)
    return repository.create_agent_session(str(uuid4()), user_id, context, task_key, task["title"], task["status"], task["prompt"])


def create_chat_session(user_id: str, page_title: str = "", page_path: str = "", page_text: str = "") -> dict:
    business_context = None
    match = re.fullmatch(r"/workbench/solutions/(\d+)", page_path)
    if match:
        try:
            business_context = context_service.get_context(user_id, "solution", match.group(1))
        except HTTPException:
            pass
    return repository.create_chat_session(str(uuid4()), user_id, page_title, page_path, page_text.replace("\0", "").strip()[:12000], business_context)


def list_sessions(user_id: str) -> list[dict]:
    return repository.list_agent_sessions(user_id)


def delete_session(user_id: str, session_id: str) -> None:
    if not repository.delete_agent_session(user_id, session_id):
        raise HTTPException(status_code=404, detail="Agent Session 不存在")


def record_turn(user_id: str, session_id: str, message: str, reply: str, artifacts: list[dict] | None = None) -> None:
    repository.append_conversation(user_id, session_id, message, reply, artifacts or [])


def get_session(user_id: str, session_id: str) -> dict:
    session = repository.get_agent_session(user_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Agent Session 不存在")
    return session


def refresh_context(user_id: str, session_id: str) -> dict:
    session = get_session(user_id, session_id)
    if session["context_type"] == "chat":
        raise HTTPException(status_code=422, detail="自由讨论没有可刷新的业务 Context")
    fresh = context_service.get_context(user_id, session["context_type"], session["context_id"])
    for key in ("supplement", "excluded_sections"):
        if session["context_snapshot"].get(key): fresh[key] = session["context_snapshot"][key]
    return repository.update_context_snapshot(user_id, session_id, fresh) or (_ for _ in ()).throw(HTTPException(status_code=404, detail="Agent Session 不存在"))


def patch_context(user_id: str, session_id: str, supplement: str, excluded_sections: list[str]) -> dict:
    session = get_session(user_id, session_id)
    snapshot = dict(session["context_snapshot"])
    snapshot["supplement"] = supplement.strip()
    snapshot["excluded_sections"] = [item for item in excluded_sections if item in {"summary", "content", "metadata", "related_entities"}]
    return repository.update_context_snapshot(user_id, session_id, snapshot) or (_ for _ in ()).throw(HTTPException(status_code=404, detail="Agent Session 不存在"))


def _file_details(filename: str, content: str) -> tuple[str, str]:
    filename = filename.strip()
    if not filename or len(filename.encode("utf-8")) > 255 or filename in {".", ".."} or any(char in filename for char in "/\\\r\n\0"):
        raise HTTPException(status_code=422, detail="文件名无效")
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in MIME_TYPES:
        raise HTTPException(status_code=422, detail="仅支持安全白名单内的文本文件")
    size = len(content.encode("utf-8"))
    if not size or size > MAX_ARTIFACT_BYTES or "\0" in content:
        raise HTTPException(status_code=422, detail="文件必须为 1B–100KB 的 UTF-8 文本")
    return filename, MIME_TYPES[suffix]


def create_artifact(user_id: str, session_id: str, title: str, artifact_type: str, content: str = "", filename: str = "") -> dict:
    session = get_session(user_id, session_id)
    if not content:
        replies = [item["content"] for item in session.get("conversation", []) if item.get("role") == "assistant" and item.get("content")]
        content = replies[-1] if replies else ""
    if not content.strip():
        raise HTTPException(status_code=422, detail="当前 Session 没有可保存的 Agent 输出")
    title = title.strip() or session.get("task_title") or "Agent 成果"
    safe_title = "".join("-" if char in "/\\\r\n\0" else char for char in title).strip(". ")[:80] or "agent-output"
    filename, mime_type = _file_details(filename or (safe_title if safe_title.lower().endswith(".md") else f"{safe_title}.md"), content)
    return artifact_repository.create(user_id, session, str(uuid4()), title, artifact_type, content, filename, mime_type)


def create_generated_artifacts(user_id: str, session_id: str, files: list[dict]) -> list[dict]:
    session = get_session(user_id, session_id)
    created = []
    for item in files:
        try:
            filename, mime_type = _file_details(item.get("filename", ""), item.get("content", ""))
        except HTTPException:
            continue
        suffix = filename.rsplit(".", 1)[-1].upper()
        created.append(artifact_repository.create(user_id, session, str(uuid4()), filename, suffix, item["content"], filename, mime_type))
    return created


def list_artifacts(user_id: str) -> list[dict]:
    return artifact_repository.list_for_user(user_id)


def get_artifact(user_id: str, artifact_id: str) -> dict:
    item = artifact_repository.get_for_user(user_id, artifact_id)
    if not item: raise HTTPException(status_code=404, detail="Artifact 不存在")
    return item


def request_knowledge(user_id: str, artifact_id: str) -> dict:
    item = artifact_repository.request_knowledge(user_id, artifact_id)
    if not item: raise HTTPException(status_code=409, detail="Artifact 不存在或已提交")
    return item


def propose_action(user_id: str, session_id: str, action: str, payload: dict) -> dict:
    get_session(user_id, session_id)
    return repository.create_agent_action(str(uuid4()), session_id, user_id, action, payload)


def confirm_action(user_id: str, action_id: str) -> dict:
    proposal = repository.get_agent_action(user_id, action_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Agent Action 不存在")
    if proposal["status"] != "proposed":
        raise HTTPException(status_code=409, detail="该 Action 已处理")
    session = get_session(user_id, str(proposal["session_id"]))
    snapshot = session["context_snapshot"]
    payload = proposal["payload"]
    if proposal["action"] == "create_requirement_draft":
        result = workbench_service.create_requirement(user_id, {
            "title": payload["title"], "description": payload.get("description", ""), "status": "draft",
            "priority": payload.get("priority", "medium"), "source_type": snapshot["context_type"],
            "source_id": snapshot["context_id"], "source_url": snapshot.get("source_url") or None,
        })
    elif proposal["action"] == "create_solution_draft":
        result = workbench_service.create_solution(user_id, {
            "name": payload["name"], "description": payload.get("description", ""), "category": payload.get("category", "未分类"),
            "status": "draft", "version": payload.get("version", "v0.1.0"), "reference_url": snapshot.get("source_url") or None,
        }, payload.get("requirement_id"))
    elif proposal["action"] == "append_note":
        if payload["entity_type"] == "requirement":
            item = workbench_service.get_requirement(user_id, payload["entity_id"])
            result = workbench_service.update_requirement(user_id, payload["entity_id"], {"description": f"{item['description'].rstrip()}\n\n{payload['note'].strip()}".strip()})
        else:
            item = workbench_service.get_solution(user_id, payload["entity_id"])
            result = workbench_service.update_solution(user_id, payload["entity_id"], {"description": f"{item['description'].rstrip()}\n\n{payload['note'].strip()}".strip()})
    elif proposal["action"] == "update_draft_content":
        if payload["entity_type"] == "requirement":
            item = workbench_service.get_requirement(user_id, payload["entity_id"])
            if item["status"] != "draft":
                raise HTTPException(status_code=409, detail="只能更新 Draft Requirement")
            result = workbench_service.update_requirement(user_id, payload["entity_id"], {key: value for key, value in payload.items() if key in {"title", "description"}})
        else:
            item = workbench_service.get_solution(user_id, payload["entity_id"])
            if item["status"] != "draft":
                raise HTTPException(status_code=409, detail="只能更新 Draft Solution")
            changes = {key: value for key, value in payload.items() if key == "description"}
            if "title" in payload:
                changes["name"] = payload["title"]
            result = workbench_service.update_solution(user_id, payload["entity_id"], changes)
    else:
        raise HTTPException(status_code=422, detail="当前版本不支持该 Action")
    repository.confirm_agent_action(action_id, result)
    return result
