"""认证路由 — 登录/注册/登出/用户信息/Insight-Agent SSO"""
from __future__ import annotations
import asyncio
import hmac
from urllib.parse import quote, urlencode
from uuid import UUID
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel
from supabase import create_client, Client
from settings import settings
from services import opencode_sso_service

router = APIRouter()
security = HTTPBearer(auto_error=False)

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY) if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY else None
supabase_anon: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY) if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY else None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials or not supabase:
        return None
    try:
        user = supabase.auth.get_user(credentials.credentials)
        return user.user
    except Exception:
        return None


async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="未登录，请先登录")
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase 未配置")
    try:
        user = supabase.auth.get_user(credentials.credentials)
        return user.user
    except Exception:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")


async def require_admin(user=Depends(require_auth)):
    if (user.app_metadata or {}).get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class AgentTicketRequest(BaseModel):
    target_user_id: Optional[UUID] = None


class InviteRequest(BaseModel):
    email: str
    name: str = ""
    role: Literal["user", "admin"] = "user"


class MemberUpdateRequest(BaseModel):
    role: Optional[Literal["user", "admin"]] = None
    disabled: Optional[bool] = None


def _member_status(account) -> str:
    return "disabled" if (getattr(account, "app_metadata", None) or {}).get("status") == "disabled" else "active"


def _member_payload(account) -> dict:
    status = _member_status(account)
    return {
        "id": str(account.id),
        "email": account.email,
        "name": (getattr(account, "user_metadata", None) or {}).get("name", ""),
        "role": (getattr(account, "app_metadata", None) or {}).get("role", "user"),
        "status": status,
        "agent_space_status": "已禁用" if status == "disabled" else "首次进入自动创建",
        "created_at": account.created_at,
        "last_sign_in_at": account.last_sign_in_at,
    }


def _is_disabled(account) -> bool:
    return _member_status(account) == "disabled"


async def _require_active_agent_user(user):
    if _is_disabled(user):
        raise HTTPException(status_code=403, detail="当前账号已被禁用，无法进入 Insight-Agent")
    return user


def _gateway_secret() -> str:
    if len(settings.OPENCODE_SSO_SECRET) < 32:
        raise HTTPException(status_code=503, detail="Insight-Agent SSO 尚未配置")
    return settings.OPENCODE_SSO_SECRET


@router.post("/auth/login")
async def auth_login(req: LoginRequest):
    if not supabase_anon:
        raise HTTPException(status_code=500, detail="Supabase 未配置")
    try:
        result = supabase_anon.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password,
        })
        return {
            "access_token": result.session.access_token,
            "refresh_token": result.session.refresh_token,
            "user": {
                "id": result.user.id,
                "email": result.user.email,
                "name": result.user.user_metadata.get("name", ""),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"登录失败: {str(e)}")


@router.post("/auth/register")
async def auth_register(req: RegisterRequest):
    if not supabase_anon:
        raise HTTPException(status_code=500, detail="Supabase 未配置")
    try:
        result = supabase_anon.auth.sign_up({
            "email": req.email,
            "password": req.password,
            "options": {
                "data": {"name": req.name},
                "email_redirect_to": f"{settings.BASE_URL.rstrip('/')}/auth/login",
            },
        })
        return {
            "access_token": result.session.access_token if result.session else None,
            "refresh_token": result.session.refresh_token if result.session else None,
            "user": {
                "id": result.user.id,
                "email": result.user.email,
                "name": result.user.user_metadata.get("name", ""),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"注册失败: {str(e)}")


@router.get("/auth/me")
async def auth_me(user=Depends(get_current_user)):
    if not user:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "id": user.id,
        "email": user.email,
        "name": user.user_metadata.get("name", "") if user.user_metadata else "",
        "role": (user.app_metadata or {}).get("role", "user"),
        "status": _member_status(user),
    }


@router.get("/auth/users")
async def auth_users(_=Depends(require_admin)):
    # ponytail: one admin page covers the current small user base; paginate when it exceeds 200.
    users = await asyncio.to_thread(supabase.auth.admin.list_users, 1, 200)
    return {"users": [_member_payload(item) for item in users], "total": len(users)}


@router.post("/auth/users/invite")
async def invite_user(req: InviteRequest, _=Depends(require_admin)):
    email = req.email.strip().lower()
    if "@" not in email or len(email) > 254:
        raise HTTPException(status_code=422, detail="请输入有效邮箱")
    try:
        result = await asyncio.to_thread(
            supabase.auth.admin.invite_user_by_email,
            email,
            {"data": {"name": req.name.strip()[:80]}, "redirect_to": f"{settings.BASE_URL.rstrip('/')}/auth/login"},
        )
        account = result.user
        account = (await asyncio.to_thread(supabase.auth.admin.update_user_by_id, account.id, {
            "app_metadata": {"role": req.role, "status": "active"},
        })).user
        return {"user": _member_payload(account), "message": "邀请已发送"}
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"邀请发送失败: {error}")


@router.patch("/auth/users/{user_id}")
async def update_user(user_id: UUID, req: MemberUpdateRequest, admin=Depends(require_admin)):
    if str(admin.id) == str(user_id):
        raise HTTPException(status_code=400, detail="不能修改自己的管理员角色或状态")
    try:
        account = (await asyncio.to_thread(supabase.auth.admin.get_user_by_id, str(user_id))).user
    except Exception:
        raise HTTPException(status_code=404, detail="用户不存在")
    metadata = dict(account.app_metadata or {})
    if req.role is not None:
        metadata["role"] = req.role
    if req.disabled is not None:
        metadata["status"] = "disabled" if req.disabled else "active"
    try:
        updated = (await asyncio.to_thread(supabase.auth.admin.update_user_by_id, str(user_id), {"app_metadata": metadata})).user
        if req.disabled:
            await asyncio.to_thread(opencode_sso_service.revoke_member_gateway_sessions, str(user_id))
        return {"user": _member_payload(updated)}
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"成员更新失败: {error}")


@router.post("/auth/logout")
async def auth_logout(user=Depends(get_current_user)):
    if supabase and user:
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
    return {"message": "已登出"}


@router.post("/auth/opencode/ticket")
async def create_opencode_ticket(req: Optional[AgentTicketRequest] = None, user=Depends(require_auth)):
    await _require_active_agent_user(user)
    target_user_id = str(req.target_user_id) if req and req.target_user_id else None
    if target_user_id and target_user_id != str(user.id):
        if (user.app_metadata or {}).get("role") != "admin":
            raise HTTPException(status_code=403, detail="只有管理员可以进入其他用户的 AI 空间")
        try:
            target_account = (await asyncio.to_thread(supabase.auth.admin.get_user_by_id, target_user_id)).user
        except Exception:
            raise HTTPException(status_code=404, detail="目标用户不存在")
        await _require_active_agent_user(target_account)
    ticket = await asyncio.to_thread(opencode_sso_service.issue_ticket, str(user.id), target_user_id)
    query = urlencode({"ticket": ticket})
    return {"redirect_url": f"{settings.OPENCODE_PUBLIC_URL}/auth/callback?{query}"}


@router.get("/auth/opencode/callback")
async def opencode_callback(x_insight_sso_ticket: str = Header(default="")):
    ticket = await asyncio.to_thread(opencode_sso_service.consume_ticket, x_insight_sso_ticket)
    if not ticket:
        raise HTTPException(status_code=401, detail="SSO ticket 无效、已过期或已使用")
    try:
        auth_account = (await asyncio.to_thread(supabase.auth.admin.get_user_by_id, ticket["user_id"])).user
        agent_account = auth_account if ticket["agent_user_id"] == ticket["user_id"] else (
            await asyncio.to_thread(supabase.auth.admin.get_user_by_id, ticket["agent_user_id"])
        ).user
    except Exception:
        raise HTTPException(status_code=401, detail="SSO 用户已失效")
    auth_role = (auth_account.app_metadata or {}).get("role", "user")
    agent_role = (agent_account.app_metadata or {}).get("role", "user")
    await _require_active_agent_user(auth_account)
    await _require_active_agent_user(agent_account)
    display_name = ((agent_account.user_metadata or {}).get("name") or (agent_account.email or "").split("@")[0]).strip()[:80]
    session = await asyncio.to_thread(
        opencode_sso_service.create_gateway_session,
        ticket["user_id"], ticket["agent_user_id"], auth_role, agent_role, display_name,
    )
    response = RedirectResponse(f"{settings.OPENCODE_PUBLIC_URL}/chat", status_code=303)
    response.set_cookie(
        "insight_opencode_session",
        session,
        max_age=opencode_sso_service.SESSION_TTL_SECONDS,
        httponly=True,
        secure=settings.OPENCODE_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    if display_name:
        response.set_cookie(
            "insight_agent_name", quote(display_name, safe=""),
            max_age=opencode_sso_service.SESSION_TTL_SECONDS,
            secure=settings.OPENCODE_COOKIE_SECURE, samesite="lax", path="/",
        )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/auth/opencode/verify")
async def verify_opencode_gateway(
    request: Request,
    x_insight_gateway_secret: str = Header(default=""),
):
    secret = _gateway_secret()
    if not hmac.compare_digest(x_insight_gateway_secret, secret):
        raise HTTPException(status_code=403, detail="Gateway 验证失败")
    token = request.cookies.get("insight_opencode_session", "")
    session = await asyncio.to_thread(opencode_sso_service.verify_gateway_session, token)
    if not session:
        raise HTTPException(status_code=401, detail="Insight-Agent 授权已过期")
    return Response(status_code=204, headers={
        "X-Insight-User-Id": session["agent_user_id"],
        "X-Insight-Agent-Role": session["agent_role"],
        "X-Insight-Auth-Role": session["auth_role"],
        "X-Insight-Display-Name": quote(session["display_name"], safe=""),
        "Cache-Control": "no-store",
    })


@router.post("/auth/opencode/revoke", status_code=204)
async def revoke_opencode_sessions(user=Depends(require_auth)):
    await asyncio.to_thread(opencode_sso_service.revoke_gateway_sessions, str(user.id))
    response = Response(status_code=204)
    response.delete_cookie("insight_opencode_session", path="/")
    response.delete_cookie("insight_agent_name", path="/")
    return response
