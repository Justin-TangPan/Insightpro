"""Session snapshots and human-confirmed Insight-Agent business actions."""
from __future__ import annotations

from uuid import uuid4
from fastapi import HTTPException

from repositories import context_repository as repository
from services import context_service, workbench_service


def chat_messages(user_id: str, message: str, session_id: str) -> list[dict]:
    """Build the small, server-owned prompt for the native Insight-Agent chat."""
    session = get_session(user_id, session_id)
    context = session["context_snapshot"] if session["context_type"] != "chat" else None
    system = "你是 InsightPro 的 Insight-Agent。用中文给出清晰、可执行的技术分析；不要编造未提供的事实。"
    if context:
        system += f"\n\n当前已授权业务上下文：\n{__import__('json').dumps(context, ensure_ascii=False)}"
    history = session.get("conversation") or []
    return [{"role": "system", "content": system}, *history[-12:], {"role": "user", "content": message}]


def create_session(user_id: str, context_type: str, context_id: str) -> dict:
    context = context_service.get_context(user_id, context_type, context_id)
    return repository.create_agent_session(str(uuid4()), user_id, context)


def create_chat_session(user_id: str) -> dict:
    return repository.create_chat_session(str(uuid4()), user_id)


def list_sessions(user_id: str) -> list[dict]:
    return repository.list_agent_sessions(user_id)


def delete_session(user_id: str, session_id: str) -> None:
    if not repository.delete_agent_session(user_id, session_id):
        raise HTTPException(status_code=404, detail="Agent Session 不存在")


def record_turn(user_id: str, session_id: str, message: str, reply: str) -> None:
    repository.append_conversation(user_id, session_id, message, reply)


def get_session(user_id: str, session_id: str) -> dict:
    session = repository.get_agent_session(user_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Agent Session 不存在")
    return session


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
