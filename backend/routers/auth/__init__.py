"""Auth routes — login/register/logout/user info/admin/Insight-Agent SSO/knowledge base

Split into three sub-modules, combined via include_router under the same /auth prefix.
"""
from __future__ import annotations
import asyncio
import logging
from uuid import UUID
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from supabase import create_client, Client
from settings import settings
from services import agent_audit_service, agent_runtime_service, agent_sso_service

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer(auto_error=False)

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY) if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY else None
supabase_anon: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY) if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY else None


# ── Shared dependencies and utility functions ──

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials or not supabase:
        return None
    try:
        user = supabase.auth.get_user(credentials.credentials)
        return user.user if _is_internal_member(user.user) else None
    except Exception:
        logger.debug("get_current_user: token verification failed", exc_info=True)
        return None


async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated, please log in first")
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        user = supabase.auth.get_user(credentials.credentials)
        if not _is_internal_member(user.user):
            raise HTTPException(status_code=403, detail="Internal access required")
        return user.user
    except HTTPException:
        raise
    except Exception:
        logger.warning("require_auth: token verification failed", exc_info=True)
        raise HTTPException(status_code=401, detail="Login expired, please log in again")


async def require_admin(user=Depends(require_auth)):
    if (user.app_metadata or {}).get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ── Shared Pydantic models ──

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class AgentTicketRequest(BaseModel):
    target_user_id: Optional[UUID] = None
    agent_session_id: Optional[UUID] = None


class InviteRequest(BaseModel):
    email: str
    name: str = ""
    role: Literal["user", "admin"] = "user"


class TestUserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=80)
    role: Literal["user", "admin"] = "user"


class MemberUpdateRequest(BaseModel):
    role: Optional[Literal["user", "admin"]] = None
    disabled: Optional[bool] = None


class RuntimeConfigPatch(BaseModel):
    CHAT_API_URL: Optional[str] = None
    CHAT_MODEL: Optional[str] = None
    CHAT_API_KEY: Optional[str] = None


# ── Shared helper functions ──

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
        "agent_space_status": "disabled" if status == "disabled" else "Auto-created on first access",
        "created_at": account.created_at,
        "last_sign_in_at": account.last_sign_in_at,
    }


def _is_disabled(account) -> bool:
    return _member_status(account) == "disabled"


def _is_internal_member(account) -> bool:
    metadata = getattr(account, "app_metadata", None) or {}
    return metadata.get("role") in ("user", "admin") and metadata.get("status") != "disabled"


async def _require_active_agent_user(user):
    if _is_disabled(user):
        raise HTTPException(status_code=403, detail="Account disabled, cannot access Insight-Agent")
    return user


def _gateway_secret() -> str:
    if len(settings.HERMES_SSO_SECRET) < 32:
        raise HTTPException(status_code=503, detail="Insight-Agent SSO not configured")
    return settings.HERMES_SSO_SECRET


# ── Compose sub-routers ──
from routers.auth._login import router as login_router
from routers.auth._admin import router as admin_router
from routers.auth._agent_sso import router as agent_sso_router

# ── Re-export route handler functions for test access ──
from routers.auth._agent_sso import create_agent_ticket, agent_callback, verify_agent_gateway, revoke_agent_sessions
from routers.auth._login import auth_login, auth_register, auth_me, auth_users, invite_user, create_test_user, update_user, auth_logout
from routers.auth._admin import (
    agent_spaces, runtime_config, verify_runtime_config, update_runtime_config,
    start_agent_space, stop_agent_space,
    public_knowledge, upload_public_knowledge, delete_public_knowledge,
)

router.include_router(login_router)
router.include_router(admin_router)
router.include_router(agent_sso_router)
