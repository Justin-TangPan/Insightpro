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


KNOWLEDGE_BASE = """你是 InsightPro 技术解决方案洞察平台的专属 AI 助手。

## 平台概述
InsightPro 持续跟踪技术项目、云厂商解决方案与产品变化，帮助用户理解方案价值并辅助技术选型。

## 核心功能
1. 首页洞察（/）：技术解决方案简报、关键统计和模块预览。
2. 热点追踪（/insights/hotspots）：GitHub Trending 项目监测和 AI 业务价值评估。
3. 解决方案洞察（/insights/solutions）：每日跟踪阿里云、华为云官方技术解决方案，展示简要分析并优先标记新增或变更方案。
4. 友商洞察（/insights/competitors）：跟踪云厂商产品变化并进行能力对比。
5. Requirements（/workbench/requirements）：将洞察转为可跟踪的技术需求，并关联解决方案。
6. Solutions（/workbench/solutions）：管理自己的技术方案并查看相关 Requirements；与外部云厂商方案目录相互独立。
7. 全局搜索（/search）：按相关性检索技术项目、方案洞察、友商动态，以及登录用户自己的 Requirements 和 Solutions。
8. 系统设置（/settings）：账号、订阅和系统配置。

## 核心闭环
用户可以从解决方案洞察创建 Requirement，再关联已有 Solution 或创建并自动关联新 Solution。

## 回答规则
回答简洁专业，适合技术决策者阅读。不编造数据。"""


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
