"""AI 智能客服路由"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import httpx
from settings import settings
from deep_searcher_integration import retrieve_context, context_to_str

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = None


KNOWLEDGE_BASE = """你是 InsightPro 商业洞察平台的专属 AI 助手。

## 平台概述
InsightPro 是面向云服务商业市场业务领导的 AI 驱动商业洞察平台。

## 核心功能
1. 首页洞察（/）：每日商业简报、关键统计和模块预览。
2. 热点追踪（/insights/hotspots）：GitHub Trending 项目监测和 AI 业务价值评估。
3. 行业洞察（/insights/industry）：融合行业全景、云厂商竞争格局和标杆案例库。
4. 政策法规（/insights/policy）：政策雷达和合规机会判断。
5. 系统设置（/settings）：账号、订阅和系统配置。

## 回答规则
回答简洁专业，适合商业决策者阅读。不编造数据。"""


@router.post("/chat")
async def chat_with_ai(req: ChatRequest):
    if not settings.CHAT_API_KEY:
        raise HTTPException(status_code=500, detail="AI 客服未配置")
    try:
        ctx_results = retrieve_context(req.message, top_k=8)
        ctx_str = context_to_str(ctx_results)
    except Exception:
        ctx_str = ""
    system_content = KNOWLEDGE_BASE
    if ctx_str:
        system_content += f"\n\n## 检索到的相关知识\n{ctx_str}"
    messages = [{"role": "system", "content": system_content}]
    if req.history:
        messages.extend(req.history[-6:])
    messages.append({"role": "user", "content": req.message})
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                settings.CHAT_API_URL,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.CHAT_API_KEY}"},
                json={"model": settings.CHAT_MODEL, "messages": messages, "temperature": 0.7, "max_tokens": 1024},
            )
            resp.raise_for_status()
            return {"reply": resp.json()["choices"][0]["message"]["content"], "model": settings.CHAT_MODEL}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI 响应超时")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 服务异常: {str(e)}")


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    if not settings.CHAT_API_KEY:
        raise HTTPException(status_code=500, detail="AI 客服未配置")
    try:
        ctx_results = retrieve_context(req.message, top_k=8)
        ctx_str = context_to_str(ctx_results)
    except Exception:
        ctx_str = ""
    system_content = KNOWLEDGE_BASE
    if ctx_str:
        system_content += f"\n\n## 检索到的相关知识\n{ctx_str}"
    messages = [{"role": "system", "content": system_content}]
    if req.history:
        messages.extend(req.history[-6:])
    messages.append({"role": "user", "content": req.message})

    async def generate():
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream("POST", settings.CHAT_API_URL,
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.CHAT_API_KEY}"},
                    json={"model": settings.CHAT_MODEL, "messages": messages, "temperature": 0.7, "max_tokens": 1024, "stream": True},
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            yield f"{line}\n\n"
                    yield "data: [DONE]\n\n"
        except Exception as e:
            yield f'data: {{"error": "{str(e)}"}}\n\n'

    return StreamingResponse(generate(), media_type="text/event-stream")
