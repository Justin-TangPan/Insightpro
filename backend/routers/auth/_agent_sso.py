"""Insight-Agent SSO routes — ticket, callback, verify, revoke"""
from __future__ import annotations
import asyncio
import hmac
import logging
from urllib.parse import quote
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header, Request
from fastapi.responses import RedirectResponse, Response

from routers.auth import (
    supabase, logger,
    require_auth,
    AgentTicketRequest,
    _require_active_agent_user, _gateway_secret,
)
from services import agent_sso_service
from settings import settings

router = APIRouter()


@router.post("/auth/agent/ticket")
async def create_agent_ticket(req: Optional[AgentTicketRequest] = None, user=Depends(require_auth)):
    await _require_active_agent_user(user)
    target_user_id = str(req.target_user_id) if req and req.target_user_id else None
    if target_user_id and target_user_id != str(user.id):
        if (user.app_metadata or {}).get("role") != "admin":
            raise HTTPException(status_code=403, detail="Only admins can enter another user's AI space")
        try:
            target_account = (await asyncio.to_thread(supabase.auth.admin.get_user_by_id, target_user_id)).user
        except Exception:
            logger.warning("create_agent_ticket: target user lookup failed for %s", target_user_id, exc_info=True)
            raise HTTPException(status_code=404, detail="Target user not found")
        await _require_active_agent_user(target_account)
    agent_session_id = str(req.agent_session_id) if req and req.agent_session_id else None
    if agent_session_id:
        from services import agent_service
        await asyncio.to_thread(agent_service.get_session, str(user.id), agent_session_id)
    return {"redirect_url": f"{settings.BASE_URL.rstrip('/')}/"}


@router.get("/auth/agent/callback")
async def agent_callback(x_insight_sso_ticket: str = Header(default="")):
    ticket = await asyncio.to_thread(agent_sso_service.consume_ticket, x_insight_sso_ticket)
    if not ticket:
        raise HTTPException(status_code=401, detail="SSO ticket invalid, expired, or already used")
    try:
        auth_account = (await asyncio.to_thread(supabase.auth.admin.get_user_by_id, ticket["user_id"])).user
        agent_account = auth_account if ticket["agent_user_id"] == ticket["user_id"] else (
            await asyncio.to_thread(supabase.auth.admin.get_user_by_id, ticket["agent_user_id"])
        ).user
    except Exception:
        logger.warning("agent_callback: SSO user lookup failed", exc_info=True)
        raise HTTPException(status_code=401, detail="SSO user no longer valid")
    auth_role = (auth_account.app_metadata or {}).get("role", "admin")
    agent_role = (agent_account.app_metadata or {}).get("role", "admin")
    await _require_active_agent_user(auth_account)
    await _require_active_agent_user(agent_account)
    display_name = ((agent_account.user_metadata or {}).get("name") or (agent_account.email or "").split("@")[0]).strip()[:80]
    session = await asyncio.to_thread(
        agent_sso_service.create_gateway_session,
        ticket["user_id"], ticket["agent_user_id"], auth_role, agent_role, display_name, ticket.get("agent_session_id"),
    )
    response = RedirectResponse(f"{settings.HERMES_PUBLIC_URL}/chat", status_code=303)
    response.set_cookie(
        "insight_agent_session",
        session,
        max_age=agent_sso_service.SESSION_TTL_SECONDS,
        httponly=True,
        secure=settings.HERMES_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    if display_name:
        response.set_cookie(
            "insight_agent_name", quote(display_name, safe=""),
            max_age=agent_sso_service.SESSION_TTL_SECONDS,
            secure=settings.HERMES_COOKIE_SECURE, samesite="lax", path="/",
        )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/auth/agent/verify")
async def verify_agent_gateway(
    request: Request,
    x_insight_gateway_secret: str = Header(default=""),
):
    secret = _gateway_secret()
    if not hmac.compare_digest(x_insight_gateway_secret, secret):
        raise HTTPException(status_code=403, detail="Gateway verification failed")
    token = request.cookies.get("insight_agent_session", "")
    session = await asyncio.to_thread(agent_sso_service.verify_gateway_session, token)
    if not session:
        raise HTTPException(status_code=401, detail="Insight-Agent authorization expired")
    return Response(status_code=204, headers={
        "X-Insight-User-Id": session["agent_user_id"],
        "X-Insight-Agent-Role": session["agent_role"],
        "X-Insight-Auth-Role": session["auth_role"],
        "X-Insight-Display-Name": quote(session["display_name"], safe=""),
        "X-Insight-Agent-Session-Id": session.get("agent_session_id") or "",
        "Cache-Control": "no-store",
    })


@router.post("/auth/agent/revoke", status_code=204)
async def revoke_agent_sessions(user=Depends(require_auth)):
    await asyncio.to_thread(agent_sso_service.revoke_gateway_sessions, str(user.id))
    response = Response(status_code=204)
    response.delete_cookie("insight_agent_session", path="/")
    response.delete_cookie("insight_agent_name", path="/")
    return response
