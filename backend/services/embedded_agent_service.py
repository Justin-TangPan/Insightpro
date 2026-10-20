"""Run pinned Hermes Python source locally, with one process per active turn."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path

from fastapi import HTTPException

from settings import settings
from services import insight_agent_runtime

# ponytail: one API worker owns its active turns; shared routing is needed before
# running multiple API workers. Process isolation avoids Hermes global-state races.
active_turns: dict[tuple[str, str], dict] = {}


async def stop(user_id: str, session_id: str) -> bool:
    """End a live Hermes turn explicitly when a proxied browser stream closes."""
    key = (user_id, session_id)
    turn = active_turns.get(key)
    process = turn.get("process") if turn else None
    if process is None or process.returncode is not None:
        return False
    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), 5)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
    if active_turns.get(key) is turn:
        active_turns.pop(key, None)
    return True


async def resolve(user_id: str, session_id: str, request_id: str, answer: str):
    turn = active_turns.get((user_id, session_id))
    pending = turn.get("pending") if turn else None
    if not pending or pending["request_id"] != request_id:
        raise HTTPException(409, "Decision expired or does not belong to the current session")
    if turn.get("resolving"):
        raise HTTPException(409, "Decision is being submitted")
    if not answer.strip() or len(answer) > 4000:
        raise HTTPException(422, "Please provide valid decision content")
    turn["resolving"] = True
    try:
        turn["process"].stdin.write((json.dumps({"request_id": request_id, "answer": answer}) + "\n").encode())
        await turn["process"].stdin.drain()
        turn["pending"] = None
    except (BrokenPipeError, ConnectionResetError):
        raise HTTPException(409, "Agent has ended, please retry")
    finally:
        turn["resolving"] = False


async def stream(user_id: str, session: dict, message: str, model: str):
    key = (user_id, session["id"])
    if key in active_turns:
        raise HTTPException(409, "Current session is still running")
    if len(active_turns) >= 6:
        raise HTTPException(429, "Agent is busy, please try again later")
    turn = {}
    active_turns[key] = turn
    process = None
    try:
        from services.knowledge_service import augment_message
        augmented = await asyncio.to_thread(augment_message, user_id, message)
        messages = insight_agent_runtime.messages_for(session, augmented)
        from services.ai_service import api_base_url
        payload = {
            "session_id": session["id"], "model": model,
            "api_key": settings.CHAT_API_KEY, "base_url": api_base_url(),
            "system": messages[0]["content"] + "\nNecessary user decisions must invoke the clarify tool, waiting for an actual response before continuing. Prefer the deliver_file tool for generating deliverables. Do not deploy or invoke business write APIs.",
            "history": session.get("runtime_history") or messages[1:-1], "message": augmented,
        }
        with tempfile.TemporaryDirectory(prefix="insight-core-") as workspace:
            env = {
                "PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
                "PYTHONPATH": os.getenv("INSIGHT_HERMES_SOURCE", "/opt/hermes"),
                "HERMES_HOME": workspace, "HERMES_DISABLE_LAZY_INSTALLS": "1",
                "PYTHONUNBUFFERED": "1",
            }
            process = await asyncio.create_subprocess_exec(
                os.getenv("INSIGHT_HERMES_PYTHON", "/opt/hermes/.venv/bin/python"),
                str(Path(__file__).with_name("hermes_core_worker.py")),
                cwd=workspace, env=env, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, limit=4 * 1024 * 1024,
                start_new_session=True,
            )
            turn["process"] = process
            process.stdin.write((json.dumps(payload, ensure_ascii=False) + "\n").encode())
            await process.stdin.drain()
            completed = False
            # Wall deadline includes time spent awaiting a human; never auto-consent.
            async with asyncio.timeout(1800):
                while line := await process.stdout.readline():
                    event = json.loads(line)
                    if event.get("type") == "interaction.request":
                        turn["pending"] = event
                    if event.get("type") == "interaction.resolved":
                        turn["pending"] = None
                    if event.get("type") == "error":
                        raise RuntimeError(event["error"])
                    if event.get("type") == "message.end":
                        completed = True
                    yield event
                    if completed:
                        break
            if not completed:
                raise RuntimeError("Agent stream ended without completion")
    finally:
        if process is not None and process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), 5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        if active_turns.get(key) is turn:
            active_turns.pop(key, None)
