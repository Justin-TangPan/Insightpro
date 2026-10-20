"""InsightAgent process entrypoint. Agent loop/provider/tool execution are upstream Hermes.

stdin: initial turn, then interaction answers. stdout: NDJSON events only.
No Dashboard, Gateway, CLI command or external runtime service is involved.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import traceback
from pathlib import Path, PurePath
from uuid import uuid4

wire = sys.stdout
write_lock = threading.Lock()


def emit(event_type: str, **payload):
    with write_lock:
        wire.write(json.dumps({"type": event_type, **payload}, ensure_ascii=False) + "\n")
        wire.flush()


def ask_user(question, choices=None, multi_select=False, questions=None):
    # Let Hermes assemble batch tool_results through its existing single-question
    # fallback: this callback intentionally advertises no batch support (below).
    request_id = uuid4().hex
    emit("interaction.request", request_id=request_id, question=question,
         choices=choices or [], multi_select=bool(multi_select), state="waiting_user")
    line = sys.stdin.readline()
    if not line:
        raise RuntimeError("Decision channel closed")
    response = json.loads(line)
    if response.get("request_id") != request_id:
        raise ValueError("Decision does not belong to this request")
    emit("interaction.resolved", request_id=request_id, state="running")
    return response["answer"]


def main():
    payload = json.loads(sys.stdin.readline())
    # Standard upstream configuration: expose this small tool catalog directly.
    Path(os.environ["HERMES_HOME"], "config.yaml").write_text('tools:\n  tool_search:\n    enabled: "off"\n', encoding="utf-8")
    # Upstream imports and tool diagnostics may print; keep stdout strictly NDJSON.
    sys.stdout = sys.stderr
    from run_agent import AIAgent
    from tools.registry import registry

    files = {}

    def deliver_file(args, **_):
        name, content = args.get("filename", ""), args.get("content", "")
        if (not isinstance(name, str) or not name or len(name) > 200
                or PurePath(name).name != name or "\\" in name or name.startswith(".")
                or not isinstance(content, str) or len(content.encode()) > 102400
                or (name not in files and len(files) >= 10)):
            return json.dumps({"error": "Invalid filename or content; only single text filenames are allowed, max 100KB per file"})
        files[name] = {"filename": name, "content": content}
        return json.dumps({"filename": name, "status": "ready_for_download"}, ensure_ascii=False)

    registry.register(
        name="deliver_file", toolset="insight_delivery", handler=deliver_file,
        schema={"name": "deliver_file", "description": "Generate a downloadable text deliverable; does not execute file or deployment operations.",
                "parameters": {"type": "object", "properties": {
                    "filename": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["filename", "content"]}},
    )

    # Individual batch questions are handled sequentially by Hermes clarify_tool.
    def clarify(question, choices=None, multi_select=False):
        return ask_user(question, choices, multi_select)

    agent = AIAgent(
        model=payload["model"], provider="custom", api_mode="chat_completions",
        base_url=payload["base_url"], api_key=payload["api_key"],
        enabled_toolsets=["clarify", "insight_delivery"],
        session_id=payload["session_id"], platform="insight", quiet_mode=True,
        skip_context_files=True, skip_memory=True, skip_background_review=True,
        max_iterations=30, max_tokens=8192,
        clarify_callback=clarify,
        tool_start_callback=lambda call_id, name, args: emit("tool.start", tool_call_id=call_id, name=name, state="tool_running"),
        tool_complete_callback=lambda call_id, name, args, result: emit("tool.end", tool_call_id=call_id, name=name, state="running"),
        # Hermes fires this on every provider delta across every tool-loop round.
        stream_delta_callback=lambda delta: emit("text.delta", delta=delta) if delta else None,
    )
    # Tool allowlist is an executable boundary, never just a prompt instruction.
    if agent.valid_tool_names != {"clarify", "deliver_file"}:
        raise RuntimeError(f"Unexpected core tool configuration: {agent.valid_tool_names}")
    emit("run.start", state="running", engine="hermes-source", tools=sorted(agent.valid_tool_names))
    try:
        result = agent.run_conversation(
            payload["message"], system_message=payload["system"],
            conversation_history=payload.get("history") or None,
        )
        if result.get("error") or result.get("failed") or result.get("interrupted"):
            raise RuntimeError("Hermes core turn did not complete")
        text = str(result.get("final_response") or "")
        if not text.strip() and not files:
            raise RuntimeError("Hermes core returned no content")
        emit("message.end", text=text, files=list(files.values()),
             history=result.get("messages", []), state="done",
             usage={"prompt_tokens": agent.session_input_tokens,
                    "completion_tokens": agent.session_output_tokens})
    finally:
        agent.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("InsightAgent core worker failed")
        traceback.print_exc(file=sys.stderr)
        emit("error", error="Agent execution failed, please retry.", state="failed")
        sys.exit(1)
