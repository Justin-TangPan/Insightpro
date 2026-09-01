"""Admin-only bridge to the isolated Insight-Agent Runtime Manager."""
from __future__ import annotations

import httpx

from settings import settings


def _url(path: str) -> str:
    return f"{settings.AGENT_RUNTIME_CONTROL_URL}/_insight/runtime/{path}"


def _knowledge_url(path: str) -> str:
    return f"{settings.AGENT_RUNTIME_CONTROL_URL}/_insight/knowledge/{path}"


def _headers(user_id: str = "", role: str = "", display_name: str = "", session_id: str = "") -> dict:
    return {
        "X-Insight-Runtime-Secret": settings.HERMES_SSO_SECRET,
        "X-Insight-User-Id": user_id,
        "X-Insight-Agent-Role": role,
        "X-Insight-Auth-Role": "admin",
        "X-Insight-Display-Name": display_name,
        "X-Insight-Agent-Session-Id": session_id,
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


async def read_action(user_id: str, session_id: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(_url("action"), params={"session_id": session_id}, headers=_headers(user_id))
        response.raise_for_status()
        return response.json()


async def chat(user_id: str, role: str, display_name: str, session_id: str, message: str) -> dict:
    async with httpx.AsyncClient(timeout=320) as client:
        response = await client.post(
            _url("chat"), json={"message": message},
            headers=_headers(user_id, role, display_name, session_id),
        )
        response.raise_for_status()
        return response.json()


async def delete_session(user_id: str, role: str, display_name: str, session_id: str, hermes_session_id: str) -> None:
    async with httpx.AsyncClient(timeout=40) as client:
        response = await client.delete(
            _url("session"), params={"hermes_session_id": hermes_session_id},
            headers=_headers(user_id, role, display_name, session_id),
        )
        response.raise_for_status()


async def knowledge_list(query: str = "") -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(_knowledge_url("list"), params={"q": query}, headers=_headers())
        response.raise_for_status()
        return response.json()


async def knowledge_upload(filename: str, category: str, content: bytes) -> None:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(_knowledge_url("upload"), params={"category": category}, content=content, headers={**_headers(), "X-Insight-Knowledge-Name": filename})
        response.raise_for_status()


async def knowledge_delete(path: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(_knowledge_url("delete"), params={"path": path}, headers=_headers())
        response.raise_for_status()
