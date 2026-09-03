"""Admin-managed, restart-safe overrides for non-secret AI settings."""
from urllib.parse import urlparse

from db import get_db
from settings import settings

KEYS = ("CHAT_API_URL", "CHAT_MODEL", "CHAT_MODELS")


def _values() -> dict[str, str]:
    return {key: ",".join(getattr(settings, key)) if key == "CHAT_MODELS" else str(getattr(settings, key)) for key in KEYS}


def load() -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM runtime_settings WHERE key = ANY(%s)", (list(KEYS),))
        apply({row["key"]: row["value"] for row in cursor.fetchall()})


def apply(values: dict[str, str]) -> dict[str, str]:
    for key, value in values.items():
        if key not in KEYS:
            continue
        value = value.strip()
        if key == "CHAT_API_URL" and (urlparse(value).scheme not in {"http", "https"} or not urlparse(value).netloc):
            raise ValueError("AI API 地址必须是 http(s) URL")
        if key == "CHAT_MODEL" and not value:
            raise ValueError("默认模型不能为空")
        if key == "CHAT_MODELS":
            models = tuple(dict.fromkeys(item.strip() for item in value.split(",") if item.strip()))
            if not models:
                raise ValueError("至少配置一个可选模型")
            settings.CHAT_MODELS = models
            continue
        setattr(settings, key, value)
    if settings.CHAT_MODEL not in settings.CHAT_MODELS:
        settings.CHAT_MODELS = (settings.CHAT_MODEL, *settings.CHAT_MODELS)
    return _values()


def update(values: dict[str, str]) -> dict[str, str]:
    current = _values()
    current.update({key: value for key, value in values.items() if key in KEYS})
    result = apply(current)
    with get_db() as conn:
        cursor = conn.cursor()
        for key, value in result.items():
            cursor.execute("INSERT INTO runtime_settings (key, value, updated_at) VALUES (%s, %s, NOW()) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW()", (key, value))
    return result
