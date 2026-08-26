"""认证路由 — 登录/注册/登出/用户信息/Insight-Agent SSO"""
import asyncio
import hmac
from urllib.parse import urlencode

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


def _require_opencode_user(user) -> None:
    if not user.email or user.email.lower() != settings.OPENCODE_ALLOWED_EMAIL:
        raise HTTPException(status_code=403, detail="当前 Insight-Agent 单实例仅授权指定管理员使用")


def _gateway_secret() -> str:
    if len(settings.OPENCODE_SSO_SECRET) < 32:
        raise HTTPException(status_code=503, detail="OpenCode SSO 尚未配置")
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
            "options": {"data": {"name": req.name}},
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
    }


@router.post("/auth/logout")
async def auth_logout(user=Depends(get_current_user)):
    if supabase and user:
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
    return {"message": "已登出"}


@router.post("/auth/opencode/ticket")
async def create_opencode_ticket(user=Depends(require_auth)):
    _require_opencode_user(user)
    ticket = await asyncio.to_thread(opencode_sso_service.issue_ticket, str(user.id))
    query = urlencode({"ticket": ticket})
    return {"redirect_url": f"{settings.OPENCODE_PUBLIC_URL}/auth/callback?{query}"}


@router.get("/auth/opencode/callback")
async def opencode_callback(x_insight_sso_ticket: str = Header(default="")):
    user_id = await asyncio.to_thread(opencode_sso_service.consume_ticket, x_insight_sso_ticket)
    if not user_id:
        raise HTTPException(status_code=401, detail="SSO ticket 无效、已过期或已使用")
    session = await asyncio.to_thread(opencode_sso_service.create_gateway_session, user_id)
    response = RedirectResponse(f"{settings.OPENCODE_PUBLIC_URL}/L3dvcmtzcGFjZQ/session", status_code=303)
    response.set_cookie(
        "insight_opencode_session",
        session,
        max_age=opencode_sso_service.SESSION_TTL_SECONDS,
        httponly=True,
        secure=settings.OPENCODE_COOKIE_SECURE,
        samesite="lax",
        path="/",
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
    user_id = await asyncio.to_thread(opencode_sso_service.verify_gateway_session, token)
    if not user_id:
        raise HTTPException(status_code=401, detail="OpenCode 授权已过期")
    return Response(status_code=204, headers={"X-Insight-User-Id": user_id, "Cache-Control": "no-store"})


@router.post("/auth/opencode/revoke", status_code=204)
async def revoke_opencode_sessions(user=Depends(require_auth)):
    await asyncio.to_thread(opencode_sso_service.revoke_gateway_sessions, str(user.id))
    return Response(status_code=204)
