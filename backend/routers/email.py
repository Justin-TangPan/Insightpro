"""Email service routes"""
import re
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from routers.auth import require_admin, require_auth

logger = logging.getLogger(__name__)
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
    language: str = "zh"

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


@router.get("/email/subscribers")
async def list_subscribers(_=Depends(require_admin)):
    subs = get_subscribers()
    return {"subscribers": subs, "count": len(subs)}


@router.post("/email/subscribe")
async def subscribe_email(req: EmailRequest, _=Depends(require_admin)):
    if add_subscriber(req.email, req.name, req.weekdays, req.send_time, req.language):
        return {"status": "success", "message": f"{req.email} subscription saved"}
    raise HTTPException(status_code=500, detail="Subscription save failed")


@router.put("/email/subscribers/{subscriber_id}")
async def configure_subscriber(subscriber_id: int, req: ScheduleRequest, _=Depends(require_admin)):
    subscriber = update_subscriber(subscriber_id, req.weekdays, req.send_time, req.language)
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return {"status": "success", "message": f"{subscriber['email']} delivery schedule saved", "subscriber": subscriber}


@router.post("/email/preference")
async def update_my_email_language(language: str, user=Depends(require_auth)):
    language = "en" if language == "en" else "zh"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE email_subscribers SET language = %s WHERE email = %s AND active = 1", (language, user.email.lower()))
    return {"status": "success", "language": language}


@router.delete("/email/subscribers/{email}")
async def unsubscribe_email(email: str, _=Depends(require_admin)):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("UPDATE email_subscribers SET active = 0 WHERE email = %s", (email,))
    return {"status": "success", "message": f"{email} unsubscribed"}


@router.post("/email/test")
async def test_email(req: EmailRequest, _=Depends(require_admin)):
    html = build_daily_digest_html(req.language)
    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"[Test] InsightPro · AI Radar Daily Snapshot ({today})"
    try:
        if send_email(req.email, subject, html):
            return {"status": "success", "message": f"Test email sent to {req.email}"}
        raise HTTPException(status_code=500, detail="Email send failed")
    except Exception as e:
        logger.exception("Email send error")
        raise HTTPException(status_code=500, detail="Email send failed, please try again later")


@router.post("/email/subscribers/{subscriber_id}/send")
async def send_to_subscriber(subscriber_id: int, _=Depends(require_admin)):
    subscriber = get_subscriber(subscriber_id)
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    language = subscriber.get("language", "zh")
    html = build_daily_digest_html(language)
    subject = f"InsightPro · AI Radar {'Daily Snapshot' if language == 'en' else '每日快照'} ({datetime.now():%Y-%m-%d})"
    if not send_email(subscriber["email"], subject, html):
        raise HTTPException(status_code=500, detail="Email send failed")
    return {"status": "success", "message": f"Email sent to {subscriber['email']}"}


@router.get("/email/preview", response_class=HTMLResponse)
async def preview_email(language: str = "zh", _=Depends(require_admin)):
    return build_daily_digest_html(language)


@router.post("/email/send-now")
async def send_now(_=Depends(require_admin)):
    from services.task_service import run_task
    result = run_task("scheduled_email", "manual", send_daily_digest)
    return {"status": "success", "message": "Email send task executed", **(result or {})}
