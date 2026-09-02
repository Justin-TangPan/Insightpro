"""InsightPro-owned Agent Runtime for business tasks.

The runtime owns prompts, context and SSE. Model execution remains a narrow,
OpenAI-compatible call so it can later reuse selected Hermes primitives without
depending on Hermes' dashboard or CLI protocol.
"""
from __future__ import annotations

import json
import re
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx

from settings import settings


_PACKAGED_KNOWLEDGE_ROOT = Path(__file__).resolve().parent.parent / "agent_knowledge"
_SOURCE_KNOWLEDGE_ROOT = Path(__file__).resolve().parents[2] / "services" / "insight-agent"
# Local development reads the source documents; the production image carries the
# same versioned documents under /app/agent_knowledge.
KNOWLEDGE_ROOT = _PACKAGED_KNOWLEDGE_ROOT if _PACKAGED_KNOWLEDGE_ROOT.exists() else _SOURCE_KNOWLEDGE_ROOT
KNOWLEDGE_FILES = (
    "AGENTS.md",
    "BUSINESS_CONTEXT.md",
    "SOLUTION_ENGINEERING_WORKFLOW.md",
    "ROLE_SOLUTION_ARCHITECT.md",
)
PLUGINS_ROOT = KNOWLEDGE_ROOT / "plugins"
STAGES = {
    "technology_research": "Discover / Understand",
    "technology_value": "Understand",
    "solution_analysis": "Understand",
    "solution_architecture": "Design",
    "solution_design": "Design",
    "requirement_analysis": "Understand",
    "requirement_refine": "Design",
    "poc_plan": "PoC",
    "validation": "Validate",
    "implementation": "Build",
    "materials": "Deliver",
}
FILE_BLOCK = re.compile(r"```file:([^\r\n]+)\r?\n(.*?)```", re.DOTALL)


def public_knowledge() -> str:
    """Load only versioned, stable team knowledge in a deterministic order."""
    parts = []
    for name in KNOWLEDGE_FILES:
        try:
            parts.append(f"## {name}\n{(KNOWLEDGE_ROOT / name).read_text(encoding='utf-8').strip()}")
        except OSError:
            continue
    return "\n\n".join(parts)


def plugin_knowledge() -> str:
    """Load enabled, versioned Agent plugins without hard-coding their names."""
    parts = []
    if not PLUGINS_ROOT.is_dir():
        return ""
    for manifest_path in sorted(PLUGINS_ROOT.glob("*/manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            knowledge = (manifest_path.parent / manifest.get("knowledge", "")).resolve()
            knowledge.relative_to(manifest_path.parent.resolve())
            if manifest.get("enabled") is True and knowledge.is_file():
                parts.append(f"## Plugin: {manifest.get('name', manifest_path.parent.name)}\n{knowledge.read_text(encoding='utf-8').strip()}")
        except (OSError, ValueError, json.JSONDecodeError, TypeError):
            continue
    return "\n\n".join(parts)


def _context(session: dict) -> str:
    snapshot = dict(session.get("context_snapshot") or {})
    for key in snapshot.get("excluded_sections", []):
        snapshot.pop(key, None)
    snapshot.pop("excluded_sections", None)
    return json.dumps(snapshot, ensure_ascii=False, default=str)[:18000]


def messages_for(session: dict, message: str) -> list[dict]:
    task = session.get("task_title") or "自由讨论"
    prompt = session.get("default_prompt") or "请基于已注入上下文给出准确、可执行的回答。"
    stage = STAGES.get(session.get("task_key"), "Understand")
    system = f"""你是 Insight-Agent，InsightPro 的 Solution Engineering Agent。

# 公共长期知识（按以下顺序加载）
{public_knowledge()}

# 已启用插件
{plugin_knowledge()}

# 本次动态上下文
当前用户角色：Solution Architect
当前工作阶段：{stage}
当前任务：{task}
任务目标：{prompt}
当前业务对象 Context（仅使用其中可验证的信息，不要编造）：
{_context(session)}

期望输出：与当前任务相匹配的结论、依据、风险、验证要点和下一步。需要交付不超过 100KB 的文本文件时，使用 ```file:文件名.扩展名 换行 文件正文 换行 ```；仅使用常见文本/代码扩展名，不要输出服务器路径。"""
    history = [{"role": item["role"], "content": item["content"]} for item in session.get("conversation", []) if item.get("role") in {"user", "assistant"} and item.get("content")][-12:]
    return [{"role": "system", "content": system}, *history, {"role": "user", "content": message}]


def generated_files(reply: str) -> list[dict]:
    """Extract model-produced text files; validation and persistence stay server-owned."""
    return [{"filename": match.group(1).strip(), "content": match.group(2)} for match in FILE_BLOCK.finditer(reply)]


def reply_without_files(reply: str, filenames: set[str]) -> str:
    cleaned = FILE_BLOCK.sub(lambda match: "" if match.group(1).strip() in filenames else match.group(0), reply).strip()
    return cleaned or "已生成文件。"


async def stream_reply(session: dict, message: str) -> AsyncGenerator[str, None]:
    """Yield provider answer tokens only; reasoning and tool traces are never forwarded."""
    if not settings.CHAT_API_KEY:
        raise RuntimeError("AI 模型未配置")
    async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=15)) as client:
        async with client.stream(
            "POST",
            settings.CHAT_API_URL,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.CHAT_API_KEY}"},
            json={"model": settings.CHAT_MODEL, "messages": messages_for(session, message), "temperature": 0.35, "max_tokens": 4096, "stream": True},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:].strip()
                if payload == "[DONE]":
                    break
                try:
                    event = json.loads(payload)
                    content = event.get("choices", [{}])[0].get("delta", {}).get("content", "")
                except (json.JSONDecodeError, IndexError, TypeError):
                    continue
                if content:
                    yield content
