"""Admin routes — Agent Spaces, Runtime config, public knowledge base"""
from __future__ import annotations
import asyncio
import logging

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from fastapi.responses import Response
import httpx
from uuid import UUID

from routers.auth import (
    supabase, logger,
    require_auth, require_admin,
    RuntimeConfigPatch,
    EmbeddingConfigPatch,
    _member_payload, _require_active_agent_user,
)
from services import agent_audit_service, agent_runtime_service
from settings import settings

router = APIRouter()


@router.get("/auth/agent-spaces")
async def agent_spaces(_=Depends(require_admin)):
    try:
        runtime = await agent_runtime_service.overview()
    except Exception:
        logger.warning("agent_spaces: runtime overview failed", exc_info=True)
        raise HTTPException(status_code=503, detail="Insight-Agent Runtime Manager unavailable")
    accounts = await asyncio.to_thread(supabase.auth.admin.list_users, 1, 200)
    states = {item["user_id"]: item for item in runtime["spaces"]}
    spaces = []
    for account in accounts:
        member = _member_payload(account)
        state = states.get(member["id"], {
            "runtime_status": "stopped", "workspace_status": "not_created", "last_used_at": None, "disk_bytes": 0,
        })
        spaces.append({**member, **state})
    return {**runtime, "spaces": spaces}


@router.get("/auth/admin/runtime-config")
async def runtime_config(_=Depends(require_admin)):
    from services import ai_usage_service, runtime_config_service
    return {"config": runtime_config_service._values(), "api_key_configured": bool(settings.CHAT_API_KEY), "usage": await asyncio.to_thread(ai_usage_service.summary)}


@router.post("/auth/admin/runtime-config/verify")
async def verify_runtime_config(payload: RuntimeConfigPatch, _=Depends(require_admin)):
    from services import runtime_config_service
    values = payload.model_dump(exclude_none=True)
    if not values.get("CHAT_API_KEY"):
        values.pop("CHAT_API_KEY", None)
    try:
        return await asyncio.to_thread(runtime_config_service.verify, values)
    except httpx.HTTPError as error:
        logger.warning("runtime config verification failed: %s", error)
        raise HTTPException(status_code=422, detail="AI API 配置验证失败") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.patch("/auth/admin/runtime-config")
async def update_runtime_config(payload: RuntimeConfigPatch, admin=Depends(require_admin)):
    from services import runtime_config_service
    values = payload.model_dump(exclude_none=True)
    if not values.get("CHAT_API_KEY"):
        values.pop("CHAT_API_KEY", None)
    try:
        verification = await asyncio.to_thread(runtime_config_service.verify, values)
        config = await asyncio.to_thread(runtime_config_service.update, values)
    except httpx.HTTPError as error:
        logger.warning("runtime config verification failed: %s", error)
        raise HTTPException(status_code=422, detail="AI API 配置验证失败，未保存") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    agent_audit_service.log(str(admin.id), "runtime_config_update", detail=",".join(values))
    return {"config": config, "api_key_configured": True, **verification}


@router.get("/auth/admin/embedding-config")
async def embedding_config(_=Depends(require_admin)):
    from services import embedding_config_service
    return {"config": embedding_config_service._values(),
            "api_key_configured": bool(settings.EMBEDDING_API_KEY),
            "dimensions": settings.EMBEDDING_DIMENSIONS}


@router.post("/auth/admin/embedding-config/verify")
async def verify_embedding_config(payload: EmbeddingConfigPatch, _=Depends(require_admin)):
    from services import embedding_config_service
    values = payload.model_dump(exclude_none=True)
    if not values.get("EMBEDDING_API_KEY"):
        values.pop("EMBEDDING_API_KEY", None)
    try:
        return await asyncio.to_thread(embedding_config_service.verify, values)
    except httpx.HTTPError as error:
        logger.warning("embedding config verification failed: %s", error)
        raise HTTPException(status_code=422, detail="Embedding API 配置验证失败") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.patch("/auth/admin/embedding-config")
async def update_embedding_config(payload: EmbeddingConfigPatch, admin=Depends(require_admin)):
    from services import embedding_config_service
    values = payload.model_dump(exclude_none=True)
    if not values.get("EMBEDDING_API_KEY"):
        values.pop("EMBEDDING_API_KEY", None)
    try:
        verification = await asyncio.to_thread(embedding_config_service.verify, values)
        config = await asyncio.to_thread(embedding_config_service.update, values)
    except httpx.HTTPError as error:
        logger.warning("embedding config verification failed: %s", error)
        raise HTTPException(status_code=422, detail="Embedding API 配置验证失败，未保存") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    agent_audit_service.log(str(admin.id), "embedding_config_update", detail=",".join(values))
    return {"config": config, "api_key_configured": True, **verification}


@router.post("/auth/agent-spaces/{user_id}/start")
async def start_agent_space(user_id: UUID, _=Depends(require_admin)):
    try:
        account = (await asyncio.to_thread(supabase.auth.admin.get_user_by_id, str(user_id))).user
    except Exception:
        logger.warning("start_agent_space: user lookup failed for %s", user_id, exc_info=True)
        raise HTTPException(status_code=404, detail="User not found")
    await _require_active_agent_user(account)
    try:
        state = await agent_runtime_service.start(
            str(account.id), (account.app_metadata or {}).get("role", "admin"),
            ((account.user_metadata or {}).get("name") or (account.email or "").split("@")[0])[:80],
        )
        agent_audit_service.log(str(_.id), "runtime_start", str(user_id))
        return {"state": state}
    except Exception:
        logger.exception("start_agent_space: runtime start failed for %s", user_id)
        raise HTTPException(status_code=503, detail="Insight-Agent Runtime start failed")


@router.post("/auth/agent-spaces/{user_id}/stop", status_code=204)
async def stop_agent_space(user_id: UUID, _=Depends(require_admin)):
    try:
        await agent_runtime_service.stop(str(user_id))
        agent_audit_service.log(str(_.id), "runtime_stop", str(user_id))
    except Exception:
        logger.warning("stop_agent_space: runtime stop failed for %s", user_id, exc_info=True)
        raise HTTPException(status_code=503, detail="Insight-Agent Runtime unavailable")
    return Response(status_code=204)


@router.get("/auth/public-knowledge")
async def public_knowledge(query: str = "", _=Depends(require_auth)):
    try:
        return await agent_runtime_service.knowledge_list(query)
    except Exception:
        logger.warning("public_knowledge: knowledge list failed", exc_info=True)
        raise HTTPException(status_code=503, detail="Public knowledge base unavailable")


@router.post("/auth/public-knowledge", status_code=201)
async def upload_public_knowledge(file: UploadFile = File(...), category: str = "", _=Depends(require_admin)):
    content = await file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File must not exceed 10 MB")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="Knowledge base only supports UTF-8 text files")
    path = "/".join(part for part in (category.strip("/ "), file.filename or "") if part)
    try:
        await agent_runtime_service.knowledge_upload(file.filename or "", category, content)
        from services.knowledge_service import upsert_document
        await asyncio.to_thread(upsert_document, "public_file", path, file.filename or path, text, f"knowledge://{path}")
        agent_audit_service.log(str(_.id), "knowledge_upload", detail=f"{category}/{file.filename}")
    except Exception:
        logger.warning("upload_public_knowledge: upload failed for %s", file.filename, exc_info=True)
        raise HTTPException(status_code=400, detail="Upload failed")
    return Response(status_code=201)


@router.delete("/auth/public-knowledge")
async def delete_public_knowledge(path: str, _=Depends(require_admin)):
    try:
        await agent_runtime_service.knowledge_delete(path)
        from services.knowledge_service import delete_document
        await asyncio.to_thread(delete_document, "public_file", path)
        agent_audit_service.log(str(_.id), "knowledge_delete", detail=path)
    except Exception:
        logger.warning("delete_public_knowledge: delete failed for %s", path, exc_info=True)
        raise HTTPException(status_code=400, detail="Delete failed or file is protected")
    return Response(status_code=204)
