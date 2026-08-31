"""Authenticated Context Bridge and human-confirmed Agent Actions."""
from __future__ import annotations

import asyncio
import hmac
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from routers.auth import require_auth
from services import agent_runtime_service, agent_service, context_service
from settings import settings

router = APIRouter(prefix="/agent")
ContextType = Literal["github_project", "cloud_solution", "vendor_update", "requirement", "solution"]
ActionType = Literal["create_requirement_draft", "create_solution_draft", "append_note", "update_draft_content"]


class SessionCreate(BaseModel):
    context_type: ContextType
    context_id: str = Field(min_length=1, max_length=200)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: str = Field(min_length=1, max_length=64)


class ActionCreate(BaseModel):
    action: ActionType
    payload: dict = Field(default_factory=dict)


class RequirementDraftPayload(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    priority: Literal["low", "medium", "high", "critical"] = "medium"


class SolutionDraftPayload(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    category: str = Field(default="未分类", max_length=100)
    version: str = Field(default="v0.1.0", max_length=50)
    requirement_id: Optional[int] = Field(default=None, gt=0)


class NotePayload(BaseModel):
    entity_type: Literal["requirement", "solution"]
    entity_id: int = Field(gt=0)
    note: str = Field(min_length=1, max_length=2000)


class DraftUpdatePayload(BaseModel):
    entity_type: Literal["requirement", "solution"]
    entity_id: int = Field(gt=0)
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)


@router.get("/context/{context_type}/{context_id}")
async def get_context(context_type: ContextType, context_id: str, user=Depends(require_auth)):
    return await asyncio.to_thread(context_service.get_context, str(user.id), context_type, context_id)


@router.post("/sessions", status_code=201)
async def create_session(payload: SessionCreate, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.create_session, str(user.id), payload.context_type, payload.context_id)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.get_session, str(user.id), session_id)


@router.get("/chat/sessions")
async def list_chat_sessions(user=Depends(require_auth)):
    return {"items": await asyncio.to_thread(agent_service.list_sessions, str(user.id))}


@router.post("/chat/sessions", status_code=201)
async def create_chat_session(user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.create_chat_session, str(user.id))


@router.delete("/chat/sessions/{session_id}", status_code=204)
async def delete_chat_session(session_id: str, user=Depends(require_auth)):
    await asyncio.to_thread(agent_service.delete_session, str(user.id), session_id)


@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest, user=Depends(require_auth)):
    from services import ai_service

    if not settings.CHAT_API_KEY:
        raise HTTPException(status_code=503, detail="Insight-Agent 模型未配置")
    messages = await asyncio.to_thread(agent_service.chat_messages, str(user.id), payload.message, payload.session_id)

    async def stream():
        reply = []
        async for line in ai_service.chat_complete_stream(messages):
            if line.startswith("data: ") and line.strip() != "data: [DONE]":
                try:
                    reply.append(__import__("json").loads(line[6:])["choices"][0]["delta"].get("content", ""))
                except (KeyError, ValueError, IndexError):
                    pass
            yield line
        await asyncio.to_thread(agent_service.record_turn, str(user.id), payload.session_id, payload.message, "".join(reply))

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/sessions/{session_id}/actions", status_code=201)
async def propose_action(session_id: str, payload: ActionCreate, user=Depends(require_auth)):
    if payload.action == "create_requirement_draft":
        action_payload = RequirementDraftPayload.model_validate(payload.payload).model_dump()
    elif payload.action == "create_solution_draft":
        action_payload = SolutionDraftPayload.model_validate(payload.payload).model_dump()
    elif payload.action == "append_note":
        action_payload = NotePayload.model_validate(payload.payload).model_dump()
    else:
        action_payload = DraftUpdatePayload.model_validate(payload.payload).model_dump(exclude_none=True)
        if len(action_payload) == 2:
            raise HTTPException(status_code=422, detail="至少提供一个待更新字段")
    return await asyncio.to_thread(agent_service.propose_action, str(user.id), session_id, payload.action, action_payload)


@router.post("/sessions/{session_id}/actions/import", status_code=201)
async def import_agent_action(session_id: str, user=Depends(require_auth)):
    await asyncio.to_thread(agent_service.get_session, str(user.id), session_id)
    try:
        proposal = await agent_runtime_service.read_action(str(user.id), session_id)
    except Exception:
        raise HTTPException(status_code=404, detail="当前 Agent Session 没有可确认的草稿")
    return await propose_action(session_id, ActionCreate.model_validate(proposal), user)


@router.post("/actions/{action_id}/confirm")
async def confirm_action(action_id: str, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.confirm_action, str(user.id), action_id)


@router.get("/internal/sessions/{session_id}")
async def internal_session(session_id: str, x_insight_runtime_secret: str = Header(default=""), x_insight_user_id: str = Header(default="")):
    if not settings.OPENCODE_SSO_SECRET or not hmac.compare_digest(x_insight_runtime_secret, settings.OPENCODE_SSO_SECRET):
        raise HTTPException(status_code=403, detail="Runtime 验证失败")
    return await asyncio.to_thread(agent_service.get_session, x_insight_user_id, session_id)
