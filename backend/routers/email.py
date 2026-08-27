"""邮件服务路由"""
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from routers.auth import require_admin
from pydantic import BaseModel, Field, field_validator
from services.email_service import (
    add_subscriber,
    build_daily_digest_html,
    get_subscriber,
    get_subscribers,
    send_daily_digest,
    send_email,
    update_subscriber,
)
from db import get_db

router = APIRouter()


class EmailRequest(BaseModel):
    email: str
    name: str = ""
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)), min_length=1, max_length=7)
    send_time: str = "09:05"

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("请输入有效邮箱")
        return value

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, value: list[int]) -> list[int]:
        if any(day not in range(7) for day in value):
            raise ValueError("星期必须为 0 至 6")
        return sorted(set(value))

    @field_validator("send_time")
    @classmethod
    def validate_send_time(cls, value: str) -> str:
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("时间必须为 HH:MM")
        return value


class ScheduleRequest(BaseModel):
    weekdays: list[int] = Field(min_length=1, max_length=7)
    send_time: str

    _validate_weekdays = field_validator("weekdays")(EmailRequest.validate_weekdays.__func__)
    _validate_send_time = field_validator("send_time")(EmailRequest.validate_send_time.__func__)


@router.get("/email/subscribers")
async def list_subscribers(_=Depends(require_admin)):
    subs = get_subscribers()
    return {"subscribers": subs, "count": len(subs)}


@router.post("/email/subscribe")
async def subscribe_email(req: EmailRequest, _=Depends(require_admin)):
    if add_subscriber(req.email, req.name, req.weekdays, req.send_time):
        return {"status": "success", "message": f"{req.email} 订阅已保存"}
    raise HTTPException(status_code=500, detail="订阅保存失败")


@router.put("/email/subscribers/{subscriber_id}")
async def configure_subscriber(subscriber_id: int, req: ScheduleRequest, _=Depends(require_admin)):
    subscriber = update_subscriber(subscriber_id, req.weekdays, req.send_time)
    if not subscriber:
        raise HTTPException(status_code=404, detail="订阅者不存在")
    return {"status": "success", "message": f"{subscriber['email']} 投递计划已保存", "subscriber": subscriber}


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
    subject = f"[测试] InsightPro · 技术解决方案日报 ({today})"
    try:
        if send_email(req.email, subject, html):
            return {"status": "success", "message": f"测试邮件已发送至 {req.email}"}
        raise HTTPException(status_code=500, detail="邮件发送失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"邮件发送异常: {str(e)}")


@router.post("/email/subscribers/{subscriber_id}/send")
async def send_to_subscriber(subscriber_id: int, _=Depends(require_admin)):
    subscriber = get_subscriber(subscriber_id)
    if not subscriber:
        raise HTTPException(status_code=404, detail="订阅者不存在")
    html = build_daily_digest_html()
    subject = f"InsightPro · 技术解决方案日报 ({datetime.now():%Y-%m-%d})"
    if not send_email(subscriber["email"], subject, html):
        raise HTTPException(status_code=500, detail="邮件发送失败")
    return {"status": "success", "message": f"邮件已发送至 {subscriber['email']}"}


@router.get("/email/preview", response_class=HTMLResponse)
async def preview_email(_=Depends(require_admin)):
    return build_daily_digest_html()


@router.post("/email/send-now")
async def send_now(_=Depends(require_admin)):
    result = send_daily_digest()
    return {"status": "success", "message": "邮件发送任务已执行", **(result or {})}
