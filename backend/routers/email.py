"""邮件服务路由"""
from fastapi import APIRouter, Depends, HTTPException
from routers.auth import require_admin
from pydantic import BaseModel
from typing import Optional
from services.email_service import get_subscribers, add_subscriber, send_email, send_daily_digest, build_daily_digest_html
from datetime import datetime
from db import get_db

router = APIRouter()


class EmailRequest(BaseModel):
    email: str
    name: Optional[str] = ""


@router.get("/email/subscribers")
async def list_subscribers(_=Depends(require_admin)):
    subs = get_subscribers()
    return {"subscribers": subs, "count": len(subs)}


@router.post("/email/subscribe")
async def subscribe_email(req: EmailRequest):
    if add_subscriber(req.email, req.name or ""):
        return {"status": "success", "message": f"{req.email} 已订阅每日洞察邮件"}
    return {"status": "exists", "message": f"{req.email} 已在订阅列表中"}


@router.delete("/email/subscribers/{email}")
async def unsubscribe_email(email: str, _=Depends(require_admin)):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE email_subscribers SET active = 0 WHERE email = %s", (email,))
    return {"status": "success", "message": f"{email} 已取消订阅"}


@router.post("/email/test")
async def test_email(req: EmailRequest, _=Depends(require_admin)):
    html = build_daily_digest_html()
    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"[测试] InsightPro · 每日商业洞察 ({today})"
    try:
        if send_email(req.email, subject, html):
            return {"status": "success", "message": f"测试邮件已发送至 {req.email}"}
        raise HTTPException(status_code=500, detail="邮件发送失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"邮件发送异常: {str(e)}")


@router.post("/email/send-now")
async def send_now(_=Depends(require_admin)):
    send_daily_digest()
    return {"status": "success", "message": "邮件发送任务已执行"}
