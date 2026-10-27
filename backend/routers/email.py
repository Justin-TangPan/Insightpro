"""Email service routes"""
import re
import logging
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from routers.auth import require_admin, require_auth

logger = logging.getLogger(__name__)
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from services.email_service import (
    SHANGHAI_TZ,
    add_subscriber,
    build_daily_digest_html,
    build_technical_digest_html,
    create_business_snapshot,
    create_email_snapshot,
    get_business_snapshot,
    get_subscriber,
    get_subscribers,
    send_daily_digest,
    send_email,
    send_subscriber_briefs,
    update_subscriber,
    update_subscription,
)
from db import get_db

router = APIRouter()


class EmailRequest(BaseModel):
    email: str
    name: str = ""
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)), min_length=1, max_length=7)
    send_time: str = "10:05"
    language: str = "zh"
    template: Literal["business", "technical", "both"] = "both"
    email_types: list[Literal["business", "technical"]] = Field(default_factory=lambda: ["business", "technical"], min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Please enter a valid email")
        return value

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, value: list[int]) -> list[int]:
        if any(day not in range(7) for day in value):
            raise ValueError("Weekday must be 0-6")
        return sorted(set(value))

    @field_validator("send_time")
    @classmethod
    def validate_send_time(cls, value: str) -> str:
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("Time must be HH:MM")
        return value

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return "en" if value == "en" else "zh"


class ScheduleRequest(BaseModel):
    weekdays: list[int] = Field(min_length=1, max_length=7)
    send_time: str
    language: str = "zh"

    _validate_weekdays = field_validator("weekdays")(EmailRequest.validate_weekdays.__func__)
    _validate_send_time = field_validator("send_time")(EmailRequest.validate_send_time.__func__)
    _validate_language = field_validator("language")(EmailRequest.validate_language.__func__)


class SubscriptionRequest(BaseModel):
    enabled: bool
    weekdays: list[int] = Field(min_length=1, max_length=7)
    send_time: str
    timezone: str = "Asia/Shanghai"

    _validate_weekdays = field_validator("weekdays")(EmailRequest.validate_weekdays.__func__)
    _validate_send_time = field_validator("send_time")(EmailRequest.validate_send_time.__func__)


class LanguageRequest(BaseModel):
    language: Literal["zh", "en"]


@router.get("/email/subscribers")
async def list_subscribers(_=Depends(require_admin)):
    subs = get_subscribers()
    return {"subscribers": subs, "count": len(subs)}


@router.post("/email/subscribe")
async def subscribe_email(req: EmailRequest, _=Depends(require_admin)):
    if add_subscriber(req.email, req.name, req.weekdays, req.send_time, req.language, tuple(req.email_types)):
        return {"status": "success", "message": f"{req.email} subscription saved"}
    raise HTTPException(status_code=500, detail="Subscription save failed")


@router.put("/email/subscribers/{subscriber_id}")
async def configure_subscriber(subscriber_id: int, req: ScheduleRequest, _=Depends(require_admin)):
    subscriber = update_subscriber(subscriber_id, req.weekdays, req.send_time, req.language)
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return {"status": "success", "message": f"{subscriber['email']} delivery schedule saved", "subscriber": subscriber}


@router.put("/email/subscribers/{subscriber_id}/subscriptions/{email_type}")
async def configure_subscription(subscriber_id: int, email_type: Literal["business", "technical"], req: SubscriptionRequest, _=Depends(require_admin)):
    try:
        subscription = update_subscription(subscriber_id, email_type, req.enabled, req.weekdays, req.send_time, req.timezone)
    except Exception as error:
        if isinstance(error, (ValueError, KeyError)):
            raise HTTPException(status_code=422, detail="Invalid timezone") from error
        raise
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return subscription


@router.post("/email/preference")
async def update_my_email_language(language: str, user=Depends(require_auth)):
    language = "en" if language == "en" else "zh"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE email_subscribers SET language = %s WHERE email = %s AND active = 1", (language, user.email.lower()))
    return {"status": "success", "language": language}


@router.patch("/email/subscribers/{subscriber_id}/language")
async def configure_subscriber_language(subscriber_id: int, req: LanguageRequest, _=Depends(require_admin)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE email_subscribers SET language=%s WHERE id=%s AND active=1 RETURNING id", (req.language, subscriber_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Subscriber not found")
    return {"language": req.language}


@router.delete("/email/subscribers/{email}")
async def unsubscribe_email(email: str, _=Depends(require_admin)):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE email_subscribers SET active = 0 WHERE email = %s", (email,))
    return {"status": "success", "message": f"{email} unsubscribed"}


@router.post("/email/test")
async def test_email(req: EmailRequest, _=Depends(require_admin)):
    today = datetime.now(SHANGHAI_TZ).strftime("%Y-%m-%d")
    messages = []
    for kind in ("business", "technical"):
        if req.template in (kind, "both"):
            _, html = await asyncio.to_thread(create_email_snapshot, kind, req.language)
            messages.append(("商业洞察" if kind == "business" else "技术项目", html))
    try:
        results = await asyncio.to_thread(lambda: [send_email(req.email, f"[Test] 小雷达 · {label} ({today})", html) for label, html in messages])
        if all(results):
            return {"status": "success", "message": f"{len(results)} test email(s) sent to {req.email}"}
        raise HTTPException(status_code=500, detail="Email send failed")
    except Exception as e:
        logger.exception("Email send error")
        raise HTTPException(status_code=500, detail="Email send failed, please try again later")


@router.post("/email/subscribers/{subscriber_id}/send")
async def send_to_subscriber(subscriber_id: int, snapshot_id: Optional[str] = None,
                             email_type: Optional[Literal["business", "technical"]] = None, _=Depends(require_admin)):
    subscriber = get_subscriber(subscriber_id)
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    try:
        result = await asyncio.to_thread(send_subscriber_briefs, subscriber, snapshot_id=snapshot_id, email_type=email_type)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if not result["sent"]:
        raise HTTPException(status_code=500, detail="Email send failed")
    return {"status": "success", "message": f"{result['deliveries']} emails sent to {subscriber['email']}"}


@router.get("/email/preview", response_class=HTMLResponse)
async def preview_email(language: str = "zh", template: Literal["business", "technical"] = "business", _=Depends(require_admin)):
    snapshot_id, html = await asyncio.to_thread(create_email_snapshot, template, language)
    return HTMLResponse(html, headers={"X-Email-Snapshot-Id": snapshot_id})


@router.get("/email/snapshots/{snapshot_id}", response_class=HTMLResponse)
async def view_email_snapshot(snapshot_id: str, _=Depends(require_admin)):
    snapshot = get_business_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return HTMLResponse(snapshot["html"])


@router.post("/email/send-now")
async def send_now(_=Depends(require_admin)):
    from services.task_service import run_task
    result = run_task("scheduled_email", "manual", send_daily_digest)
    return {"status": "success", "message": "Email send task executed", **(result or {})}
