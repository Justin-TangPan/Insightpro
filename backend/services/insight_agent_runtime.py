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
from typing import Any

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


def _plugin_file(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    path.relative_to(root.resolve())
    return path


def plugin_knowledge(task_key: str | None = None) -> str:
    """Load enabled, versioned Agent plugins without hard-coding their names."""
    parts = []
    if not PLUGINS_ROOT.is_dir():
        return ""
    for manifest_path in sorted(PLUGINS_ROOT.glob("*/manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            root = manifest_path.parent
            knowledge = _plugin_file(root, manifest.get("knowledge", ""))
            if manifest.get("enabled") is True and knowledge.is_file():
                parts.append(f"## Plugin: {manifest.get('name', manifest_path.parent.name)}\n{knowledge.read_text(encoding='utf-8').strip()}")
                for skill in manifest.get("task_skills", {}).get(task_key, []):
                    path = _plugin_file(root, f"skills/{skill}/SKILL.md")
                    if path.is_file():
                        parts.append(f"## Skill: {skill}\n{path.read_text(encoding='utf-8').strip()}")
                workflow = manifest.get("task_workflows", {}).get(task_key)
                if workflow:
                    path = _plugin_file(root, f"workflows/{workflow}.yaml")
                    if path.is_file():
                        parts.append(f"## Workflow: {workflow}\n{path.read_text(encoding='utf-8').strip()}")
        except (OSError, ValueError, json.JSONDecodeError, TypeError):
            continue
    return "\n\n".join(parts)


def available_models() -> tuple[str, ...]:
    return settings.CHAT_MODELS or (settings.CHAT_MODEL,)


def resolve_model(model: str | None) -> str:
    selected = (model or settings.CHAT_MODEL).strip()
    if selected not in available_models():
        raise ValueError("不支持的模型")
    return selected


def _context(session: dict) -> str:
    snapshot = dict(session.get("context_snapshot") or {})
    for key in snapshot.get("excluded_sections", []):
        snapshot.pop(key, None)
    snapshot.pop("excluded_sections", None)
    return json.dumps(snapshot, ensure_ascii=False, default=str)[:18000]


def messages_for(session: dict, message: str) -> list[dict]:
    task = session.get("task_title") or "自由讨论"
    prompt = (session.get("default_prompt") or "").strip()
    preset = f"预置任务：{task}\n预置任务说明：{prompt}" if prompt and message.strip() == prompt else ""
    stage = STAGES.get(session.get("task_key"), "Understand")
    system = f"""你是 Insight-Agent，InsightPro 的 Solution Engineering Agent。

# 公共长期知识（按以下顺序加载）
{public_knowledge()}

# 已启用插件
{plugin_knowledge(session.get("task_key"))}

# 本次动态上下文
当前用户角色：Solution Architect
当前工作阶段：{stage}
{preset}
当前业务对象 Context（仅使用其中可验证的信息，不要编造）：
{_context(session)}

本轮用户消息优先于预置任务：用户提出其他问题时，只回答该问题，并把当前业务对象作为可选背景；不要自动套用预置任务。需要交付不超过 100KB 的文本文件时，使用 ```file:文件名.扩展名 换行 文件正文 换行 ```；仅使用常见文本/代码扩展名，不要输出服务器路径。"""
    history = [{"role": item["role"], "content": item["content"]} for item in session.get("conversation", []) if item.get("role") in {"user", "assistant"} and item.get("content")][-12:]
    return [{"role": "system", "content": system}, *history, {"role": "user", "content": message}]


def generated_files(reply: str) -> list[dict]:
    """Extract model-produced text files; validation and persistence stay server-owned."""
    return [{"filename": match.group(1).strip(), "content": match.group(2)} for match in FILE_BLOCK.finditer(reply)]


def reply_without_files(reply: str, filenames: set[str]) -> str:
    cleaned = FILE_BLOCK.sub(lambda match: "" if match.group(1).strip() in filenames else match.group(0), reply).strip()
    return cleaned or "已生成文件。"


async def generate_practice_background(payload: dict[str, str], model: str | None = None) -> str:
    """Generate editable background text; saving remains a user action."""
    if not settings.CHAT_API_KEY:
        raise RuntimeError("AI 模型未配置")
    selected = resolve_model(model)
    source = json.dumps(payload, ensure_ascii=False)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": f"""你是 InsightPro 的 Solution Architect。\n\n{plugin_knowledge("solution_analysis")}\n\n根据用户提供的方案实践名称、参考链接和已有材料，输出可直接填入“背景信息”的中文 Markdown。内容包括业务目标、适用场景、范围与约束、关键能力、依赖与风险、待确认项。只陈述已知事实；不把推测说成验证结果，也不声称已部署。"""},
        {"role": "user", "content": source},
    ]
    async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=15)) as client:
        response = await client.post(
            settings.CHAT_API_URL,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.CHAT_API_KEY}"},
            json={"model": selected, "messages": messages, "temperature": 0.25, "max_tokens": 1600},
        )
    response.raise_for_status()
    content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if not content:
        raise RuntimeError("模型未返回背景信息")
    return content[:5000]


async def stream_reply(session: dict, message: str, model: str | None = None) -> AsyncGenerator[str, None]:
    """Yield provider answer tokens only; reasoning and tool traces are never forwarded."""
    if not settings.CHAT_API_KEY:
        raise RuntimeError("AI 模型未配置")
    async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=15)) as client:
        async with client.stream(
            "POST",
            settings.CHAT_API_URL,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.CHAT_API_KEY}"},
            json={"model": resolve_model(model), "messages": messages_for(session, message), "temperature": 0.35, "max_tokens": 4096, "stream": True},
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
