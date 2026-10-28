"""Login, register, logout, user info"""
from __future__ import annotations
import asyncio
import logging

from fastapi import APIRouter, HTTPException, Depends
from routers.auth import (
    supabase, supabase_anon, logger,
    get_current_user, require_admin,
    LoginRequest, InviteRequest, MemberUpdateRequest,
    _member_payload, _member_status, _is_disabled, _is_internal_member,
)
from services import agent_audit_service, agent_runtime_service, agent_sso_service
from settings import settings
from uuid import UUID

router = APIRouter()


@router.post("/auth/login")
async def auth_login(req: LoginRequest):
    if not supabase_anon:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        result = supabase_anon.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password,
        })
        if not _is_internal_member(result.user):
            raise HTTPException(status_code=403, detail="Internal access required")
        return {
            "access_token": result.session.access_token,
            "refresh_token": result.session.refresh_token,
            "user": {
                "id": result.user.id,
                "email": result.user.email,
                "name": result.user.user_metadata.get("name", ""),
            }
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("auth_login: login failed")
        raise HTTPException(status_code=401, detail="Login failed, please check your email and password")


@router.get("/auth/me")
async def auth_me(user=Depends(get_current_user)):
    if not user:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "id": user.id,
        "email": user.email,
        "name": user.user_metadata.get("name", "") if user.user_metadata else "",
        "role": "admin",
        "status": _member_status(user),
    }


@router.get("/auth/users")
async def auth_users(_=Depends(require_admin)):
    users = await asyncio.to_thread(supabase.auth.admin.list_users, 1, 200)
    admins = [item for item in users if (item.app_metadata or {}).get("role") == "admin"]
    return {"users": [_member_payload(item) for item in admins], "total": len(admins)}


@router.post("/auth/users/invite")
async def invite_user(req: InviteRequest, _=Depends(require_admin)):
    email = req.email.strip().lower()
    if "@" not in email or len(email) > 254:
        raise HTTPException(status_code=422, detail="Please enter a valid email")
    try:
        result = await asyncio.to_thread(
            supabase.auth.admin.invite_user_by_email,
            email,
            {"data": {"name": req.name.strip()[:80]}, "redirect_to": f"{settings.BASE_URL.rstrip('/')}/admin/login"},
        )
        account = result.user
        account = (await asyncio.to_thread(supabase.auth.admin.update_user_by_id, account.id, {
            "app_metadata": {"role": "admin", "status": "active"},
        })).user
        return {"user": _member_payload(account), "message": "Invitation sent"}
    except Exception:
        logger.exception("invite_user: invite failed")
        raise HTTPException(status_code=400, detail="Invitation send failed, please try again later")


@router.patch("/auth/users/{user_id}")
async def update_user(user_id: UUID, req: MemberUpdateRequest, admin=Depends(require_admin)):
    if str(admin.id) == str(user_id):
        raise HTTPException(status_code=400, detail="Cannot modify your own admin role or status")
    try:
        account = (await asyncio.to_thread(supabase.auth.admin.get_user_by_id, str(user_id))).user
    except Exception:
        logger.warning("update_user: user lookup failed for %s", user_id, exc_info=True)
        raise HTTPException(status_code=404, detail="User not found")
    if (account.app_metadata or {}).get("role") != "admin":
        raise HTTPException(status_code=404, detail="Administrator not found")
    metadata = dict(account.app_metadata or {})
    if req.disabled is not None:
        metadata["status"] = "disabled" if req.disabled else "active"
    try:
        updated = (await asyncio.to_thread(supabase.auth.admin.update_user_by_id, str(user_id), {"app_metadata": metadata})).user
        if req.disabled:
            await asyncio.to_thread(agent_sso_service.revoke_member_gateway_sessions, str(user_id))
            try:
                await agent_runtime_service.stop(str(user_id))
            except Exception:
                logger.debug("update_user: runtime stop failed for %s", user_id, exc_info=True)
        agent_audit_service.log(str(admin.id), "member_update", str(user_id), str(req.model_dump(exclude_none=True)))
        return {"user": _member_payload(updated)}
    except Exception:
        logger.exception("update_user: member update failed for %s", user_id)
        raise HTTPException(status_code=400, detail="Member update failed, please try again later")


@router.post("/auth/logout")
async def auth_logout(user=Depends(get_current_user)):
    if supabase and user:
        try:
            supabase.auth.sign_out()
        except Exception:
            logger.debug("auth_logout: sign_out failed", exc_info=True)
    return {"message": "Logged out"}
