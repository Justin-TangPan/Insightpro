"""Admin-only bridge to the isolated Insight-Agent Runtime Manager."""
from __future__ import annotations

import httpx

from settings import settings


def _url(path: str) -> str:
    return f"{settings.OPENCODE_PUBLIC_URL}/_insight/runtime/{path}"


def _headers(user_id: str = "", role: str = "", display_name: str = "") -> dict:
    return {
        "X-Insight-Runtime-Secret": settings.OPENCODE_SSO_SECRET,
        "X-Insight-User-Id": user_id,
        "X-Insight-Agent-Role": role,
        "X-Insight-Auth-Role": "admin",
        "X-Insight-Display-Name": display_name,
    }


async def overview() -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(_url("overview"), headers=_headers())
        response.raise_for_status()
        return response.json()


async def start(user_id: str, role: str, display_name: str) -> dict:
    async with httpx.AsyncClient(timeout=40) as client:
        response = await client.post(_url(f"start?user_id={user_id}"), headers=_headers(user_id, role, display_name))
        response.raise_for_status()
        return response.json()


async def stop(user_id: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(_url(f"stop?user_id={user_id}"), headers=_headers())
        response.raise_for_status()
