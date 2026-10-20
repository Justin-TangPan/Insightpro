"""
Unified AI service layer.
All AI calls go through this module.
"""
from settings import settings
import httpx
import json
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)
_models: tuple[str, ...] = ()


def chat_completions_url(url: str = "") -> str:
    value = (url or settings.CHAT_API_URL).rstrip("/")
    return value if value.endswith("/chat/completions") else f"{value}/chat/completions"


def api_base_url(url: str = "") -> str:
    return chat_completions_url(url).removesuffix("/chat/completions")


def probe_models() -> tuple[str, ...]:
    global _models
    response = httpx.get(
        f"{api_base_url()}/models",
        headers={"Authorization": f"Bearer {settings.CHAT_API_KEY}"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json().get("data", [])
    _models = tuple(dict.fromkeys(str(item.get("id", "")).strip() for item in data if item.get("id")))
    return _models


def available_model_ids() -> tuple[str, ...]:
    return tuple(dict.fromkeys((*_models, settings.CHAT_MODEL)))


def chat_complete(
    messages: list[dict] = None,
    system_prompt: str = "",
    user_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout: float = 60,
) -> str:
    """
    Unified AI call entry point.
    Supports passing messages directly, or auto-constructing from system_prompt + user_prompt.
    """
    from services import runtime_config_service
    runtime_config_service.load()
    if messages is None:
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": user_prompt})
        messages = msgs

    resp = httpx.post(
        chat_completions_url(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.CHAT_API_KEY}",
        },
        json={
            "model": settings.CHAT_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "enable_thinking": False,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    payload = resp.json()
    content = payload["choices"][0]["message"]["content"]
    from services import ai_usage_service
    ai_usage_service.record(None, payload.get("model") or settings.CHAT_MODEL, "backend", payload.get("usage"))
    return content


def extract_json(raw: str):
    """Parse JSON from AI response, compatible with ```json fence"""
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
        logger.debug("JSON decode failed at top level, attempting sub-extraction")
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start: end + 1])
        except json.JSONDecodeError:
            return None
    return None


def extract_json_array(raw: str) -> list:
    """Parse JSON array from AI response, compatible with ```json fence"""
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
    except Exception as e:
        logger.debug("JSON array parse failed: %s", e)
        return []


async def chat_complete_stream(messages: list[dict]) -> AsyncGenerator[str, None]:
    """Streaming AI call"""
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream(
            "POST", chat_completions_url(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.CHAT_API_KEY}",
            },
            json={
                "model": settings.CHAT_MODEL,
                "messages": messages,
                "temperature": 0.7, "max_tokens": 1024, "stream": True,
                "enable_thinking": False,
            },
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    yield f"{line}\n\n"
            yield "data: [DONE]\n\n"
