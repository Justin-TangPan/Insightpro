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
from urllib.parse import urlparse

import httpx

from settings import settings
from services.ai_service import chat_completions_url


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
GITHUB_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
TOOL_MARKERS = ("<|tool_call_start|>", "<|tool_call_end|>", '"name": "web_reader"')


def github_readme_urls(reference: str) -> tuple[str, ...]:
    parsed = urlparse(reference)
    repo = parsed.path.strip("/").removesuffix(".git")
    if parsed.scheme != "https" or parsed.hostname != "github.com" or not GITHUB_REPO.fullmatch(repo):
        return ()
    return tuple(f"https://raw.githubusercontent.com/{repo}/{branch}/README.md" for branch in ("main", "master"))


def valid_background(content: str) -> bool:
    return bool(content) and not any(marker in content for marker in TOOL_MARKERS)


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
    return (settings.CHAT_MODEL,)


def resolve_model(model: str | None) -> str:
    if model and model != settings.CHAT_MODEL:
        raise ValueError("Unsupported model")
    return settings.CHAT_MODEL


def _context(session: dict) -> str:
    snapshot = dict(session.get("context_snapshot") or {})
    for key in snapshot.get("excluded_sections", []):
        snapshot.pop(key, None)
    snapshot.pop("excluded_sections", None)
    return json.dumps(snapshot, ensure_ascii=False, default=str)[:18000]


def messages_for(session: dict, message: str) -> list[dict]:
    task = session.get("task_title") or "Free Discussion"
    prompt = (session.get("default_prompt") or "").strip()
    preset = f"Preset task: {task}\nPreset task description: {prompt}" if prompt and message.strip() == prompt else ""
    stage = STAGES.get(session.get("task_key"), "Understand")
    background_rule = "" if session.get("context_type") != "solution" else "The current business object is a solution practice. Its saved background information and associated background materials are the baseline for this work: first reference and verify, clarifying facts, assumptions, gaps, and items to confirm; do not arbitrarily refresh, rewrite, or overwrite background information."
    solution_contract = ""
    if (session.get("context_snapshot") or {}).get("page_path") == "/workbench/ai":
        solution_contract = """The current entry point is for generating solutions, not executing deployments. When information is insufficient, first ask necessary clarifying questions that would change the solution; once information is sufficient, the final solution must include:
1. Value narrative: application scenarios, solution advantages, applicable customers.
2. Exactly two downloadable deliverables: `cloud-stack.tf` and `deploy-guide.md`.
`cloud-stack.tf` must be a Terraform configuration for Huawei Cloud Resource Orchestration Service (RFS), including necessary variables and outputs; resource parameters that cannot be confirmed must be exposed as variables or marked as to-be-confirmed, and must not be fabricated.
`deploy-guide.md` must describe prerequisites, parameters, steps to create a resource stack in RFS, verification methods, rollback/deletion methods, and risk notices.
Use file code blocks to generate these two files. Only generate solutions and files; do not invoke deployments, cloud resource creation, or other operations with side effects, and do not claim that deployment is complete."""
    system = f"""You are Insight-Agent, InsightPro's Solution Engineering Agent.

# Public long-term knowledge (loaded in the following order)
{public_knowledge()}

# Enabled plugins
{plugin_knowledge(session.get("task_key"))}

# Current dynamic context
Current user role: Solution Architect
Current work stage: {stage}
{preset}
{background_rule}
{solution_contract}
Current business object Context (use only verifiable information from it, do not fabricate):
{_context(session)}

This round's user message takes priority over the preset task: when the user asks a different question, answer only that question, using the current business object as optional background; do not automatically apply the preset task. When delivering text files no larger than 100KB, use ```file:filename.ext newline file content newline ```; use only common text/code extensions, and do not output server paths."""
    if any(token in message.lower() for token in ("csv", "sales", "bar chart", "data analysis")):
        system += """\nData analysis delivery rule: when the user provides a CSV or table and requests analysis, verified key conclusions (including the top three items, values, and sorting criteria) must be presented in the main text first, followed by a concise Markdown table and text bar chart; when the user requests an export, additionally use deliver_file to generate a CSV. Do not provide only a download file while omitting in-page conclusions."""
    history = [{"role": item["role"], "content": item["content"]} for item in session.get("conversation", []) if item.get("role") in {"user", "assistant"} and item.get("content")][-12:]
    return [{"role": "system", "content": system}, *history, {"role": "user", "content": message}]


def generated_files(reply: str) -> list[dict]:
    """Extract model-produced text files; validation and persistence stay server-owned."""
    return [{"filename": match.group(1).strip(), "content": match.group(2)} for match in FILE_BLOCK.finditer(reply)]


def reply_without_files(reply: str, filenames: set[str]) -> str:
    cleaned = FILE_BLOCK.sub(lambda match: "" if match.group(1).strip() in filenames else match.group(0), reply).strip()
    return cleaned or "Files generated."


async def generate_practice_background(payload: dict[str, str], model: str | None = None, user_id: str = "") -> str:
    """Generate editable background text; saving remains a user action."""
    if not settings.CHAT_API_KEY:
        raise RuntimeError("AI model not configured")
    selected = resolve_model(model)
    reference = payload.get("reference_url") or ""
    async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=15)) as client:
        for url in github_readme_urls(reference):
            try:
                readme = await client.get(url)
                if readme.status_code == 200:
                    payload["reference_content"] = readme.text[:20000]
                    break
            except httpx.HTTPError:
                break
        source = json.dumps(payload, ensure_ascii=False)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": f"""You are InsightPro's Solution Architect.\n\n{plugin_knowledge("solution_analysis")}\n\nBased on the solution practice name, reference link, reference content, and existing materials provided by the user, output Markdown that can be directly filled into the 'Background Information' field. Content should include business objectives, applicable scenarios, scope and constraints, key capabilities, dependencies and risks, and items to confirm. Only state known facts; do not present speculation as verified results, and do not claim deployment is complete. Output only the final Markdown; do not output thinking processes, tool calls, JSON, or `<|tool_call...|>` markers. When reference content is missing, explicitly state what needs to be supplemented; do not read URLs on your own."""},
            {"role": "user", "content": source},
        ]
        for attempt in range(2):
            response = await client.post(
                chat_completions_url(),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.CHAT_API_KEY}"},
                json={"model": selected, "messages": messages, "temperature": 0.25, "max_tokens": 1600},
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if valid_background(content):
                if user_id:
                    from services import ai_usage_service
                    ai_usage_service.record(user_id, selected, "practice_background", result.get("usage"))
                return content[:5000]
            if attempt == 0:
                messages.append({"role": "user", "content": "The previous result is not background information. Please output the final Markdown directly, without calling or describing any tools."})
    raise RuntimeError("Model did not return valid background information, please retry")


async def generate_suggestions(payload: dict[str, Any], model: str | None = None, user_id: str = "") -> list[str]:
    """Generate short, context-grounded starter questions for a free discussion."""
    if not settings.CHAT_API_KEY:
        raise RuntimeError("AI model not configured")
    selected = resolve_model(model)
    context = json.dumps(payload, ensure_ascii=False, default=str)[:9000]
    messages = [
        {"role": "system", "content": "You are the conversation guide for an enterprise AI insights product. Based on the current page context, generate 4 questions that users can click and send directly. Questions must specifically reference the current page object; avoid vague expressions like 'continue refining' or 'what to do next'. Each question must be no longer than 22 characters. Output only a JSON string array; no Markdown, explanations, or tool calls."},
        {"role": "user", "content": context},
    ]
    async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=10)) as client:
        response = await client.post(chat_completions_url(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.CHAT_API_KEY}"}, json={"model": selected, "messages": messages, "temperature": 0.7, "max_tokens": 180})
        response.raise_for_status()
        result = response.json()
    items = [str(item).strip() for item in _json_array(result.get("choices", [{}])[0].get("message", {}).get("content", "")) if str(item).strip()]
    items = list(dict.fromkeys(item[:80] for item in items))[:4]
    if len(items) < 3:
        raise RuntimeError("Model did not return enough context suggestions")
    if user_id:
        from services import ai_usage_service
        ai_usage_service.record(user_id, selected, "suggestions", result.get("usage"))
    return items


def _json_array(raw: str) -> list[Any]:
    text = (raw or "").strip().strip("`")
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        return []
    try:
        value = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


async def stream_reply(session: dict, message: str, model: str | None = None) -> AsyncGenerator[str, None]:
    """Yield provider answer tokens only; reasoning and tool traces are never forwarded."""
    if not settings.CHAT_API_KEY:
        raise RuntimeError("AI model not configured")
    selected = resolve_model(model)
    usage: dict[str, Any] | None = None
    from services import ai_usage_service
    record_id = ai_usage_service.start(str(session.get("user_id", "")), selected, "chat")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=15)) as client:
            async with client.stream(
                "POST",
                chat_completions_url(),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.CHAT_API_KEY}"},
                json={"model": selected, "messages": messages_for(session, message), "temperature": 0.35, "max_tokens": 4096, "stream": True, "stream_options": {"include_usage": True}},
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
                        usage = event.get("usage") or usage
                    except (json.JSONDecodeError, IndexError, TypeError):
                        continue
                    if content:
                        yield content
    finally:
        ai_usage_service.finish(record_id, usage)
