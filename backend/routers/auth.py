"""认证路由 — 登录/注册/登出/用户信息"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from supabase import create_client, Client
from settings import settings

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
