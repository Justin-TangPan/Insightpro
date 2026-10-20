"""AI chat assistant routes"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import httpx
from settings import settings
from services import ai_service, runtime_config_service

logger = logging.getLogger(__name__)
from deep_searcher_integration import retrieve_context, context_to_str

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = None


KNOWLEDGE_BASE = """You are the dedicated AI assistant for the InsightPro tech solution insights platform.

## Platform Overview
InsightPro continuously tracks technology projects, cloud vendor solutions and product changes, helping users understand solution value and assisting with technology selection.

## Core Features
1. Home Insights (/): Tech solution brief, key statistics, and module previews.
2. GitHub (/insights/hotspots): GitHub Trending project monitoring and AI solution value evaluation.
3. AI Applications (/insights/app-launches): Official AI application launches across major vendors, with source-grounded analysis.
4. Solutions (/insights/solutions): Daily tracking of Alibaba Cloud and Huawei Cloud official tech solutions, with brief analysis and priority marking for new or changed solutions.
5. Competitor Insights (/insights/competitors): Track cloud vendor product changes and compare capabilities.
6. Requirements (/workbench/requirements): Convert insights into trackable tech requirements and link them to solutions.
7. Solutions (/workbench/solutions): Manage your own tech solutions and view related Requirements; independent from external cloud vendor solution catalogs.
8. Global Search (/search): Search tech projects, solution insights, competitor updates, and the logged-in user's own Requirements and Solutions by relevance.
9. System Settings (/settings): Account, subscriptions, and system configuration.

## Core Loop
Users can create a Requirement from solution insights, then link it to an existing Solution or create and auto-link a new Solution.

## Response Rules
Keep answers concise and professional, suitable for technology decision-makers. Do not fabricate data."""


@router.post("/chat")
async def chat_with_ai(req: ChatRequest):
    await asyncio.to_thread(runtime_config_service.load)
    if not settings.CHAT_API_KEY:
        raise HTTPException(status_code=500, detail="AI chat not configured")
    try:
        ctx_results = retrieve_context(req.message, top_k=8)
        ctx_str = context_to_str(ctx_results)
    except Exception:
        ctx_str = ""
    system_content = KNOWLEDGE_BASE
    if ctx_str:
        system_content += f"\n\n## Retrieved relevant knowledge\n{ctx_str}"
    messages = [{"role": "system", "content": system_content}]
    if req.history:
        messages.extend(req.history[-6:])
    messages.append({"role": "user", "content": req.message})
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                ai_service.chat_completions_url(),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.CHAT_API_KEY}"},
                json={"model": settings.CHAT_MODEL, "messages": messages, "temperature": 0.7, "max_tokens": 1024, "enable_thinking": False},
            )
            resp.raise_for_status()
            return {"reply": resp.json()["choices"][0]["message"]["content"], "model": settings.CHAT_MODEL}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI response timeout")
    except Exception as e:
        logger.exception("AI service error")
        raise HTTPException(status_code=500, detail="AI service temporarily unavailable, please try again later")


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    await asyncio.to_thread(runtime_config_service.load)
    if not settings.CHAT_API_KEY:
        raise HTTPException(status_code=500, detail="AI chat not configured")
    try:
        ctx_results = retrieve_context(req.message, top_k=8)
        ctx_str = context_to_str(ctx_results)
    except Exception:
        ctx_str = ""
    system_content = KNOWLEDGE_BASE
    if ctx_str:
        system_content += f"\n\n## Retrieved relevant knowledge\n{ctx_str}"
    messages = [{"role": "system", "content": system_content}]
    if req.history:
        messages.extend(req.history[-6:])
    messages.append({"role": "user", "content": req.message})

    async def generate():
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream("POST", ai_service.chat_completions_url(),
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.CHAT_API_KEY}"},
                    json={"model": settings.CHAT_MODEL, "messages": messages, "temperature": 0.7, "max_tokens": 1024, "stream": True, "enable_thinking": False},
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            yield f"{line}\n\n"
                    yield "data: [DONE]\n\n"
        except Exception as e:
            yield f'data: {{"error": "{str(e)}"}}\n\n'

    return StreamingResponse(generate(), media_type="text/event-stream")
