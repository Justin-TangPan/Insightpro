"""Authenticated Context Bridge and human-confirmed Agent Actions."""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
from collections.abc import AsyncIterator
from contextlib import suppress
from urllib.parse import quote
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError

from routers.auth import require_admin, require_auth
from settings import settings
from services import agent_audit_service, agent_runtime_service, agent_service, context_service, insight_agent_runtime
from services import embedded_agent_service, ai_usage_service, runtime_config_service
from repositories import context_repository
from services.knowledge_service import search as _search_knowledge, overview as _knowledge_overview, sync_public_knowledge

router = APIRouter(prefix="/agent")
logger = logging.getLogger(__name__)
ContextType = Literal["github_project", "cloud_solution", "vendor_update", "requirement", "solution"]
ActionType = Literal["create_requirement_draft", "create_solution_draft", "append_note", "update_draft_content"]


async def _heartbeat_chunks(source: AsyncIterator, interval: float = 2) -> AsyncIterator:
    """Keep SSE alive while the model is still waiting for its next token."""
    iterator = source.__aiter__()
    pending = asyncio.create_task(iterator.__anext__())
    try:
        while True:
            done, _ = await asyncio.wait({pending}, timeout=interval)
            if not done:
                yield None
                continue
            try:
                yield pending.result()
            except StopAsyncIteration:
                break
            pending = asyncio.create_task(iterator.__anext__())
    finally:
        if not pending.done():
            pending.cancel()
        with suppress(asyncio.CancelledError, StopAsyncIteration):
            await pending
        await iterator.aclose()


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


@router.get("/knowledge/search")
async def search_knowledge(q: str = Query(min_length=1, max_length=500), user=Depends(require_auth)):
    return {"items": await asyncio.to_thread(_search_knowledge, str(user.id), q)}


@router.get("/knowledge/overview")
async def knowledge_overview(user=Depends(require_auth)):
    return await asyncio.to_thread(_knowledge_overview, str(user.id))


@router.post("/admin/knowledge/reindex")
async def reindex_knowledge(_=Depends(require_admin)):
    return {"indexed_chunks": await asyncio.to_thread(sync_public_knowledge)}


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: str = Field(min_length=1, max_length=64)
    model: Optional[str] = Field(default=None, max_length=100)


class ChatStopRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)


class InteractionResponse(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    answer: str = Field(min_length=1, max_length=4000)


class PracticeBackgroundCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    reference_url: Optional[str] = Field(default=None, max_length=2000)
    model: Optional[str] = Field(default=None, max_length=100)


class PageChatCreate(BaseModel):
    title: str = Field(default="Current page", min_length=1, max_length=200)
    path: str = Field(default="/", pattern=r"^/[A-Za-z0-9_./?=&-]{0,500}$")
    page_text: str = Field(default="", max_length=12000)


class SuggestionRequest(BaseModel):
    title: str = Field(default="Current page", max_length=200)
    path: str = Field(default="/", max_length=500)
    context: dict = Field(default_factory=dict)
    model: Optional[str] = Field(default=None, max_length=100)


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
    category: str = Field(default="Uncategorized", max_length=100)
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
    await asyncio.to_thread(runtime_config_service.load)
    return {"items": [settings.CHAT_MODEL], "default": settings.CHAT_MODEL}


@router.post("/practice-background")
async def generate_practice_background(payload: PracticeBackgroundCreate, user=Depends(require_auth)):
    await asyncio.to_thread(runtime_config_service.load)
    try:
        content = await insight_agent_runtime.generate_practice_background(payload.model_dump(exclude={"model"}), payload.model, str(user.id))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (RuntimeError, httpx.HTTPError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"content": content}


@router.post("/suggestions")
async def generate_suggestions(payload: SuggestionRequest, user=Depends(require_auth)):
    await asyncio.to_thread(runtime_config_service.load)
    try:
        items = await insight_agent_runtime.generate_suggestions(payload.model_dump(exclude={"model"}), payload.model, str(user.id))
    except (RuntimeError, ValueError, httpx.HTTPError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"items": items}


@router.post("/sessions", status_code=201)
async def create_session(payload: SessionCreate, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.create_session, str(user.id), payload.context_type, payload.context_id)


@router.post("/routes", status_code=201)
async def route_agent_action(payload: RouteCreate, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.route_session, str(user.id), payload.context_type, payload.context_id, payload.action_key)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.get_session, str(user.id), session_id)


@router.get("/internal/sessions/{session_id}", include_in_schema=False)
async def runtime_session_context(
    session_id: str,
    x_insight_runtime_secret: str = Header(default=""),
    x_insight_user_id: str = Header(default=""),
):
    if not settings.HERMES_SSO_SECRET or not hmac.compare_digest(x_insight_runtime_secret, settings.HERMES_SSO_SECRET):
        raise HTTPException(status_code=403, detail="Runtime not authorized")
    return await asyncio.to_thread(agent_service.get_session, x_insight_user_id, session_id)


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
    if not item: raise HTTPException(status_code=404, detail="Pending artifact not found")
    filename = f"artifact-{artifact_id}.md"
    result = await asyncio.to_thread(artifact_repository.publish, artifact_id, f"artifact://{artifact_id}", str(admin.id))
    from services.knowledge_service import upsert_document
    await asyncio.to_thread(upsert_document, "agent_artifact", artifact_id, item["title"], item["content"], f"artifact://{artifact_id}")
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
    await asyncio.to_thread(runtime_config_service.load)
    try:
        model = insight_agent_runtime.resolve_model(payload.model)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    async def stream():
        reply = ""
        runtime = "hermes-source"
        result = {}
        try:
            yield 'data: {"status":"Insight Agent is analyzing..."}\n\n'
            async for event in _heartbeat_chunks(embedded_agent_service.stream(str(user.id), session, payload.message, model)):
                if event is None:
                    yield 'data: {"status":"Still waiting for model response..."}\n\n'
                    continue
                if event.get("type") == "text.delta":
                    reply += str(event.get("delta") or "")
                elif event.get("type") == "message.end":
                    result = event
                    reply = str(event.get("text") or reply)
                    continue  # Persist before telling the UI this turn succeeded.
                yield f'data: {json.dumps({**event, "runtime": runtime}, ensure_ascii=False, default=str)}\n\n'
            if not result:
                raise RuntimeError("Agent stream interrupted before completion")
            if not reply.strip() and not result.get("files"):
                raise RuntimeError("Model returned no content")
            runtime_files = result.get("files", [])
            generated = insight_agent_runtime.generated_files(reply) + [item for item in runtime_files if isinstance(item, dict)]
            artifacts = await asyncio.to_thread(agent_service.create_generated_artifacts, str(user.id), payload.session_id, generated)
            references = [{key: item.get(key) for key in ("id", "session_id", "title", "filename", "mime_type", "size_bytes", "type", "knowledge_status", "created_at")} for item in artifacts]
            await asyncio.to_thread(agent_service.record_turn, str(user.id), payload.session_id, payload.message, insight_agent_runtime.reply_without_files(reply, {item["filename"] for item in references}), references)
            await asyncio.to_thread(context_repository.save_runtime_history, str(user.id), payload.session_id, result.get("history", []))
            await asyncio.to_thread(ai_usage_service.record, str(user.id), model, "agent", result.get("usage"))
            if references:
                yield f'data: {json.dumps({"artifacts": references}, ensure_ascii=False, default=str)}\n\n'
            yield f'data: {json.dumps({"type": "message.end", "text": insight_agent_runtime.reply_without_files(reply, {item["filename"] for item in references}), "state": "done", "runtime": runtime}, ensure_ascii=False)}\n\n'
        except HTTPException as error:
            logger.info("Insight-Agent request rejected: %s", error.detail)
            yield f'data: {json.dumps({"error": str(error.detail)}, ensure_ascii=False)}\n\n'
        except Exception:
            logger.exception("Insight-Agent execution failed")
            yield 'data: {"error":"Insight-Agent execution failed, please retry."}\n\n'
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


@router.post("/chat/stop", status_code=204)
async def stop_chat(payload: ChatStopRequest, user=Depends(require_auth)):
    session = await asyncio.to_thread(agent_service.get_session, str(user.id), payload.session_id)
    await embedded_agent_service.stop(str(user.id), session["id"])


@router.post("/interactions/{interaction_id}/resolve", status_code=204)
async def resolve_interaction(interaction_id: str, payload: InteractionResponse, user=Depends(require_auth)):
    if not interaction_id or len(interaction_id) > 120:
        raise HTTPException(status_code=422, detail="Invalid decision request")
    session = await asyncio.to_thread(agent_service.get_session, str(user.id), payload.session_id)
    await embedded_agent_service.resolve(str(user.id), session["id"], interaction_id, payload.answer)


@router.post("/sessions/{session_id}/actions", status_code=201)
async def propose_action(session_id: str, payload: ActionCreate, user=Depends(require_auth)):
    try:
        action_payload = _validate_action(payload)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail="Action parameters invalid") from error
    return await asyncio.to_thread(agent_service.propose_action, str(user.id), session_id, payload.action, action_payload)


def _validate_action(payload: ActionCreate) -> dict:
    if payload.action == "create_requirement_draft":
        return RequirementDraftPayload.model_validate(payload.payload).model_dump()
    elif payload.action == "create_solution_draft":
        return SolutionDraftPayload.model_validate(payload.payload).model_dump()
    elif payload.action == "append_note":
        return NotePayload.model_validate(payload.payload).model_dump()
    action_payload = DraftUpdatePayload.model_validate(payload.payload).model_dump(exclude_none=True)
    if len(action_payload) == 2:
        raise HTTPException(status_code=422, detail="At least one field to update required")
    return action_payload


async def _import_runtime_action(user_id: str, session_id: str) -> dict | None:
    raw = await agent_runtime_service.read_action(user_id, session_id)
    try:
        payload = ActionCreate.model_validate(raw)
        action_payload = _validate_action(payload)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail="Hermes Action parameters invalid") from error
    proposal = await asyncio.to_thread(agent_service.propose_action, user_id, session_id, payload.action, action_payload)
    await agent_runtime_service.clear_action(user_id, session_id)
    return proposal


@router.post("/sessions/{session_id}/actions/import", status_code=201)
async def import_agent_action(session_id: str, user=Depends(require_auth)):
    return await _import_runtime_action(str(user.id), session_id)


@router.get("/sessions/{session_id}/actions/pending")
async def pending_agent_action(session_id: str, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.pending_action, str(user.id), session_id)


@router.post("/actions/{action_id}/confirm")
async def confirm_action(action_id: str, user=Depends(require_auth)):
    return await asyncio.to_thread(agent_service.confirm_action, str(user.id), action_id)
