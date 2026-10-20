"""Persist admin-managed AI runtime configuration."""
import json
import time
from urllib.parse import urlparse

import httpx

from db import get_db
from settings import settings

PUBLIC_KEYS = ("CHAT_API_URL", "CHAT_MODEL")
KEYS = (*PUBLIC_KEYS, "CHAT_API_KEY")
REQUIRED_KEYS = ("CHAT_API_URL", "CHAT_MODEL", "CHAT_API_KEY")


def _values() -> dict[str, str]:
    return {key: str(getattr(settings, key, "")) for key in PUBLIC_KEYS}


def load() -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM runtime_settings WHERE key = ANY(%s)", (list(KEYS),))
        values = {row["key"]: row["value"] for row in cursor.fetchall()}
        if all(values.get(key, "").strip() for key in REQUIRED_KEYS):
            apply(values)


def apply(values: dict[str, str]) -> dict[str, str]:
    for key, value in values.items():
        if key in KEYS and value is not None:
            setattr(settings, key, value.strip())
    return _values()


def normalize_base_url(value: str) -> str:
    return value.strip().rstrip("/").removesuffix("/chat/completions")


def verify(values: dict[str, str]) -> dict:
    base_url = normalize_base_url(values.get("CHAT_API_URL") or settings.CHAT_API_URL)
    key = values.get("CHAT_API_KEY") or settings.CHAT_API_KEY
    model = values.get("CHAT_MODEL") or settings.CHAT_MODEL
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    started = time.perf_counter()
    with httpx.stream(
        "POST", f"{base_url}/chat/completions", headers=headers,
        json={"model": model, "messages": [{"role": "user", "content": "Reply only OK."}], "temperature": 0, "max_tokens": 8, "stream": True, "enable_thinking": False},
        timeout=20,
    ) as response:
        response.raise_for_status()
        if not any(line.startswith("data:") and line[5:].strip() not in {"", "[DONE]"} for line in response.iter_lines()):
            raise ValueError("AI API 未返回有效的流式响应")
    models = []
    try:
        response = httpx.get(f"{base_url}/models", headers=headers, timeout=10)
        response.raise_for_status()
        models = [str(item["id"]) for item in response.json().get("data", []) if item.get("id")]
    except (httpx.HTTPError, KeyError, TypeError, json.JSONDecodeError):
        pass
    return {"latency_ms": round((time.perf_counter() - started) * 1000), "models": models}


def update(values: dict[str, str]) -> dict[str, str]:
    cleaned = {key: value.strip() for key, value in values.items() if key in KEYS and value is not None}
    if "CHAT_API_URL" in cleaned:
        cleaned["CHAT_API_URL"] = normalize_base_url(cleaned["CHAT_API_URL"])
        parsed = urlparse(cleaned["CHAT_API_URL"])
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("AI API 地址必须是有效的 HTTP(S) 地址")
    if "CHAT_MODEL" in cleaned and not cleaned["CHAT_MODEL"]:
        raise ValueError("模型 ID 不能为空")
    if not cleaned:
        return _values()
    complete = {key: str(getattr(settings, key, "")) for key in KEYS}
    complete.update(cleaned)
    if not all(complete[key] for key in REQUIRED_KEYS):
        raise ValueError("AI API 地址、模型和 API Key 必须完整配置")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.executemany(
            """INSERT INTO runtime_settings (key, value, updated_at) VALUES (%s, %s, NOW())
               ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW()""",
            complete.items(),
        )
    return apply(complete)
