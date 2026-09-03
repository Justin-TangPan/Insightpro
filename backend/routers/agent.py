"""Authenticated Context Bridge and human-confirmed Agent Actions."""
from __future__ import annotations

import asyncio
import json
from urllib.parse import quote
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.responses import Response
from pydantic import BaseModel, Field

from routers.auth import require_admin, require_auth
from settings import settings
from services import agent_audit_service, agent_service, context_service, insight_agent_runtime

router = APIRouter(prefix="/agent")
ContextType = Literal["github_project", "cloud_solution", "vendor_update", "requirement", "solution"]
ActionType = Literal["create_requirement_draft", "create_solution_draft", "append_note", "update_draft_content"]


class SessionCreate(BaseModel):
    context_type: ContextType
    context_id: str = Field(min_length=1, max_length=200)


class RouteCreate(SessionCreate):
    action_key: str = Field(min_length=1, max_length=80)


class ContextPatch(BaseModel):
    supplement: str = Field(default="", max_length=4000)
    excluded_sections: list[Literal["summary", "content", "metadata", "related_entities"]] = Field(default_factory=list)


class ArtifactCreate(BaseModel):
    title: str = Field(default="", max_length=200)
    type: str = Field(default="Markdown", max_length=80)
    content: str = Field(default="", max_length=102400)
    filename: str = Field(default="", max_length=255)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: str = Field(min_length=1, max_length=64)
    model: Optional[str] = Field(default=None, max_length=100)


class PracticeBackgroundCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    reference_url: Optional[str] = Field(default=None, max_length=2000)
    model: Optional[str] = Field(default=None, max_length=100)


class PageChatCreate(BaseModel):
    title: str = Field(default="当前页面", min_length=1, max_length=200)
    path: str = Field(default="/", pattern=r"^/[A-Za-z0-9_./?=&-]{0,500}$")
    page_text: str = Field(default="", max_length=12000)


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


@router.get("/models")
async def list_models(_=Depends(require_auth)):
    return {"items": list(insight_agent_runtime.available_models()), "default": settings.CHAT_MODEL}


@router.post("/practice-background")
async def generate_practice_background(payload: PracticeBackgroundCreate, user=Depends(require_auth)):
    try:
        content = await insight_agent_runtime.generate_practice_background(payload.model_dump(exclude={"model"}), payload.model, str(user.id))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (RuntimeError, httpx.HTTPError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"content": content}


@router.post("/sessions", status_code=201)
async def create_session(payload: SessionCreate, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.create_session, str(user.id), payload.context_type, payload.context_id)


@router.post("/routes", status_code=201)
async def route_agent_action(payload: RouteCreate, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.route_session, str(user.id), payload.context_type, payload.context_id, payload.action_key)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.get_session, str(user.id), session_id)


@router.post("/sessions/{session_id}/context/refresh")
async def refresh_context(session_id: str, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.refresh_context, str(user.id), session_id)


@router.patch("/sessions/{session_id}/context")
async def patch_context(session_id: str, payload: ContextPatch, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.patch_context, str(user.id), session_id, payload.supplement, payload.excluded_sections)


@router.post("/sessions/{session_id}/artifacts", status_code=201)
async def create_artifact(session_id: str, payload: ArtifactCreate, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.create_artifact, str(user.id), session_id, payload.title, payload.type, payload.content, payload.filename)


@router.get("/artifacts")
async def list_artifacts(user=Depends(require_auth)):
    return {"items": await asyncio.to_thread(agent_service.list_artifacts, str(user.id))}


@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.get_artifact, str(user.id), artifact_id)


@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(artifact_id: str, user=Depends(require_auth)):
    item = await asyncio.to_thread(agent_service.get_artifact, str(user.id), artifact_id)
    filename = quote(item.get("filename") or f"{item['title'] or 'agent-output'}.md")
    mime_type = item.get("mime_type") or "text/markdown"
    return Response(item["content"], media_type=f"{mime_type}; charset=utf-8", headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}", "X-Content-Type-Options": "nosniff"})


@router.post("/artifacts/{artifact_id}/knowledge-request")
async def request_knowledge(artifact_id: str, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.request_knowledge, str(user.id), artifact_id)


@router.get("/admin/artifacts/requests")
async def artifact_requests(_=Depends(require_admin)):
    from repositories import artifact_repository
    return {"items": await asyncio.to_thread(artifact_repository.requested)}


@router.post("/admin/artifacts/{artifact_id}/publish")
async def publish_artifact(artifact_id: str, admin=Depends(require_admin)):
    from repositories import artifact_repository
    item = next((row for row in await asyncio.to_thread(artifact_repository.requested) if row["id"] == artifact_id), None)
    if not item: raise HTTPException(status_code=404, detail="待审核 Artifact 不存在")
    filename = f"artifact-{artifact_id}.md"
    result = await asyncio.to_thread(artifact_repository.publish, artifact_id, f"artifact://{artifact_id}", str(admin.id))
    agent_audit_service.log(str(admin.id), "artifact_publish", detail=artifact_id)
    return result


@router.get("/chat/sessions")
async def list_chat_sessions(user=Depends(require_auth)):
    return {"items": await asyncio.to_thread(agent_service.list_sessions, str(user.id))}


@router.post("/chat/sessions", status_code=201)
async def create_chat_session(payload: Optional[PageChatCreate] = None, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.create_chat_session, str(user.id), payload.title if payload else "", payload.path if payload else "", payload.page_text if payload else "")


@router.delete("/chat/sessions/{session_id}", status_code=204)
async def delete_chat_session(session_id: str, user=Depends(require_auth)):
    await asyncio.to_thread(agent_service.delete_session, str(user.id), session_id)


@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest, user=Depends(require_auth)):
    session = await asyncio.to_thread(agent_service.get_session, str(user.id), payload.session_id)
    try:
        model = insight_agent_runtime.resolve_model(payload.model)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    async def stream():
        reply = ""
        try:
            yield 'data: {"status":"Insight-Agent 正在分析…"}\n\n'
            async for content in insight_agent_runtime.stream_reply(session, payload.message, model):
                reply += content
                yield f'data: {json.dumps({"choices": [{"delta": {"content": content}}]}, ensure_ascii=False)}\n\n'
            if not reply.strip():
                raise RuntimeError("模型未返回内容")
            artifacts = await asyncio.to_thread(agent_service.create_generated_artifacts, str(user.id), payload.session_id, insight_agent_runtime.generated_files(reply))
            references = [{key: item.get(key) for key in ("id", "session_id", "title", "filename", "mime_type", "size_bytes", "type", "knowledge_status", "created_at")} for item in artifacts]
            await asyncio.to_thread(agent_service.record_turn, str(user.id), payload.session_id, payload.message, insight_agent_runtime.reply_without_files(reply, {item["filename"] for item in references}), references)
            if references:
                yield f'data: {json.dumps({"artifacts": references}, ensure_ascii=False, default=str)}\n\n'
        except Exception:
            yield 'data: {"error":"Insight-Agent 执行失败，请重试。"}\n\n'
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
    raise HTTPException(status_code=422, detail="请使用 Insight-Agent 的结构化成果操作创建草稿")


@router.post("/actions/{action_id}/confirm")
async def confirm_action(action_id: str, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.confirm_action, str(user.id), action_id)
