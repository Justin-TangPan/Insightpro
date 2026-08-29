"""Session snapshots and human-confirmed Insight-Agent business actions."""
from __future__ import annotations

from uuid import uuid4
from fastapi import HTTPException

from repositories import context_repository as repository
from services import context_service, workbench_service


def create_session(user_id: str, context_type: str, context_id: str) -> dict:
    context = context_service.get_context(user_id, context_type, context_id)
    return repository.create_agent_session(str(uuid4()), user_id, context)


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
