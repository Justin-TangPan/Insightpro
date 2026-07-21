"""
统一 AI 服务层
所有 AI 调用通过此模块。
"""
from settings import settings
import httpx
import json
from typing import AsyncGenerator


def chat_complete(
    messages: list[dict] = None,
    system_prompt: str = "",
    user_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout: float = 60,
) -> str:
    """
    统一 AI 调用入口。
    支持 messages 直接传，或 system_prompt + user_prompt 自动构造。
    """
    if messages is None:
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": user_prompt})
        messages = msgs

    resp = httpx.post(
        settings.CHAT_API_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.CHAT_API_KEY}",
        },
        json={
            "model": settings.CHAT_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def extract_json(raw: str):
    """从 AI 响应中解析 JSON，兼容 ```json fence"""
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start: end + 1])
        except json.JSONDecodeError:
            return None
    return None


def extract_json_array(raw: str) -> list:
    """从 AI 响应中解析 JSON 数组，兼容 ```json fence"""
    if not raw:
        return []
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        return json.loads(text[start:end + 1])
    except Exception:
        return []


async def chat_complete_stream(messages: list[dict]) -> AsyncGenerator[str, None]:
    """流式 AI 调用"""
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream(
            "POST", settings.CHAT_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.CHAT_API_KEY}",
            },
            json={
                "model": settings.CHAT_MODEL,
                "messages": messages,
                "temperature": 0.7, "max_tokens": 1024, "stream": True,
            },
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    yield f"{line}\n\n"
            yield "data: [DONE]\n\n"
