"""Persist admin-managed embeddings API configuration."""
import json
from urllib.parse import urlparse

import httpx

from db import get_db
from settings import settings

PUBLIC_KEYS = ("EMBEDDING_API_URL", "EMBEDDING_MODEL")
KEYS = (*PUBLIC_KEYS, "EMBEDDING_API_KEY")
REQUIRED_KEYS = KEYS


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


def verify(values: dict[str, str]) -> dict:
    url = (values.get("EMBEDDING_API_URL") or settings.EMBEDDING_API_URL).strip()
    key = values.get("EMBEDDING_API_KEY") or settings.EMBEDDING_API_KEY
    model = (values.get("EMBEDDING_MODEL") or settings.EMBEDDING_MODEL).strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Embedding API 地址必须是完整的 HTTP(S) /embeddings 接口地址")
    if not key or not model:
        raise ValueError("Embedding API Key 和模型名称必须完整配置")
    response = httpx.post(url, headers={"Authorization": f"Bearer {key}"},
                          json={"model": model, "input": ["InsightPro embedding connection test"], "encoding_format": "float"},
                          timeout=30)
    response.raise_for_status()
    data = response.json()
    vectors = data.get("data", []) if isinstance(data, dict) else []
    vector = vectors[0].get("embedding") if len(vectors) == 1 and isinstance(vectors[0], dict) else None
    if not isinstance(vector, list) or not vector or any(not isinstance(value, (int, float)) for value in vector):
        raise ValueError("Embedding API 未返回有效向量")
    dimensions = len(vector)
    if dimensions != settings.EMBEDDING_DIMENSIONS:
        raise ValueError(f"向量维度为 {dimensions}，当前知识库固定要求 {settings.EMBEDDING_DIMENSIONS} 维")
    return {"dimensions": dimensions}


def update(values: dict[str, str]) -> dict[str, str]:
    cleaned = {key: value.strip() for key, value in values.items() if key in KEYS and value is not None}
    if not cleaned:
        return _values()
    complete = {key: str(getattr(settings, key, "")) for key in KEYS}
    complete.update(cleaned)
    if not all(complete[key] for key in REQUIRED_KEYS):
        raise ValueError("Embedding API 地址、模型和 API Key 必须完整配置")
    if complete["EMBEDDING_MODEL"] != settings.EMBEDDING_MODEL:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT EXISTS (SELECT 1 FROM knowledge_chunks LIMIT 1) AS has_chunks")
            if cursor.fetchone()["has_chunks"]:
                raise ValueError("知识库已有向量数据，当前尚无安全的全量重建流程，不能在线更换模型")
    parsed = urlparse(complete["EMBEDDING_API_URL"])
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Embedding API 地址必须是完整的 HTTP(S) /embeddings 接口地址")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.executemany(
            """INSERT INTO runtime_settings (key, value, updated_at) VALUES (%s, %s, NOW())
               ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW()""",
            complete.items(),
        )
    return apply(complete)
