"""Versioned intelligence reads and source controls."""
from __future__ import annotations

import asyncio
from datetime import date as Date, datetime, timezone
from typing import Literal, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from routers.auth import require_admin
from services.event_service import get_event, list_events, merge_events, split_event, update_event, rescore_event
from services.entity_service import get_entity_detail
from services.source_registry_service import list_sources, create_source, set_source_enabled, update_source, update_source_schedule, test_source_connection
from services.discovery_service import list_candidates, approve_candidate, ignore_candidate
from services.prompt_service import list_prompts, create_draft, publish_prompt
from services.recall_benchmark_service import record_reference, recall_report
from services.repository_service import list_trending_repositories
from services.task_service import TASK_BY_KEY, COMMUNITY_ADAPTERS, source_task_key, recent_runs, run_task, set_task_schedule, task_trigger
from db import get_db

router = APIRouter()


class SourceState(BaseModel):
    enabled: bool


class SourceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    base_url: Optional[str] = Field(default=None, max_length=2000)
    priority: Optional[int] = Field(default=None, ge=0, le=1000)
    authority: Optional[Literal["P0", "P1", "P2"]] = None
    business_scopes: Optional[list[Literal["technology_ecosystem", "ai_applications", "solutions", "community_insights", "competitor_dynamics"]]] = Field(default=None, min_length=1)


class SourceCreate(BaseModel):
    source_key: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=200)
    adapter: Literal["product_hunt_feed", "hacker_news_api", "hugging_face_api", "arxiv_api", "github_search_api", "rss_feed"]
    base_url: str = Field(min_length=8, max_length=2000)
    business_scopes: list[Literal["technology_ecosystem", "ai_applications", "solutions", "community_insights", "competitor_dynamics"]] = Field(min_length=1)
    authority: Literal["P0", "P1", "P2"] = "P1"
    priority: int = Field(default=100, ge=0, le=1000)
    cron: str = Field(default="45 9 * * *", min_length=9, max_length=100)


class SourceScheduleUpdate(BaseModel):
    cron: str = Field(min_length=9, max_length=100)


class EventMerge(BaseModel):
    target_id: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=500)


class EventSplit(BaseModel):
    evidence_ids: list[int] = Field(min_length=1, max_length=100)
    title: str = Field(min_length=3, max_length=300)
    reason: str = Field(min_length=3, max_length=500)


class EventUpdate(BaseModel):
    event_type: Optional[str] = Field(default=None, min_length=3, max_length=80)
    business_scopes: Optional[list[Literal["technology_ecosystem", "ai_applications", "solutions", "community_insights", "competitor_dynamics"]]] = Field(default=None, min_length=1)
    tags: Optional[list[str]] = Field(default=None, max_length=20)
    status: Optional[Literal["active", "ignored", "archived"]] = None


class CandidateApproval(BaseModel):
    business_scopes: list[Literal["technology_ecosystem", "ai_applications", "solutions", "community_insights", "competitor_dynamics"]] = Field(min_length=1)


class CandidateIgnore(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class PromptDraft(BaseModel):
    prompt_name: str = Field(min_length=3, max_length=100, pattern=r"^[a-z0-9_]+$")
    scenario: str = Field(min_length=3, max_length=100)
    system_prompt: str = Field(min_length=20, max_length=20000)
    user_prompt_template: str = Field(default="", max_length=20000)


class RecallBenchmarkLabel(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    canonical_url: str = Field(min_length=12, max_length=2000)
    reference_source: str = Field(min_length=2, max_length=120)
    reference_at: datetime
    is_relevant: bool
    label_reason: str = Field(min_length=5, max_length=1000)

    @field_validator("canonical_url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        parsed = urlparse(value.strip())
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Reference URL must be HTTPS and contain no credentials")
        return value.strip()

    @field_validator("reference_at")
    @classmethod
    def _validate_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Reference time must include a timezone")
        if value > datetime.now(timezone.utc):
            raise ValueError("Reference time cannot be in the future")
        return value


@router.get("/events")
async def events(limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0), business_scope: Optional[str] = None):
    return await asyncio.to_thread(list_events, limit, offset, business_scope)


@router.get("/repositories/trending")
async def trending_repositories(period: Literal["daily", "weekly", "monthly"] = "daily", date: Optional[Date] = None):
    return await asyncio.to_thread(list_trending_repositories, period, date)


@router.get("/events/{event_id}")
async def event_detail(event_id: int):
    event = await asyncio.to_thread(get_event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/entities/{entity_key:path}")
async def entity_detail(entity_key: str):
    entity = await asyncio.to_thread(get_entity_detail, entity_key)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.get("/admin/events")
async def admin_events(status: Literal["active", "ignored", "archived", "all"] = "active",
                       limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                       business_scope: Optional[str] = None, _=Depends(require_admin)):
    return await asyncio.to_thread(list_events, limit, offset, business_scope, status)


@router.get("/admin/sources")
async def sources(_=Depends(require_admin)):
    return {"items": await asyncio.to_thread(list_sources)}


@router.post("/admin/sources", status_code=201)
async def add_source(request: SourceCreate, http_request: Request, admin=Depends(require_admin)):
    try:
        source = await asyncio.to_thread(create_source, request.model_dump(), str(admin.id))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    task_key = "discovery_sentinel_daily"
    set_task_schedule(task_key, request.cron)
    scheduler = getattr(http_request.app.state, "scheduler", None)
    if scheduler and scheduler.get_job(task_key):
        scheduler.reschedule_job(task_key, trigger=task_trigger(TASK_BY_KEY[task_key]))
    return source


@router.get("/admin/coverage")
async def coverage(_=Depends(require_admin)):
    def report():
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""SELECT source.source_key,source.name,source.adapter,source.authority,source.enabled,
                              source.health_status,source.last_success_at,source.last_error,
                              COUNT(raw.id) FILTER (WHERE raw.observed_at >= NOW()-INTERVAL '24 hours')::int AS items_24h
                              FROM intelligence_sources source LEFT JOIN intelligence_raw_items raw ON raw.source_key=source.source_key
                              GROUP BY source.source_key ORDER BY source.priority,source.source_key""")
            sources = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT status,COUNT(*)::int AS count FROM intelligence_candidates GROUP BY status")
            candidates = {row["status"]: row["count"] for row in cursor.fetchall()}
            benchmark_adapters = ["github_trending", "github_search_api", "rss_feed", "hacker_news_api",
                                  "hugging_face_api", "arxiv_api", "product_hunt_feed"]
            cursor.execute("""SELECT raw.id,raw.title,raw.canonical_url,raw.observed_at,
                              source.source_key,source.name,
                              EXISTS(SELECT 1 FROM intelligence_candidate_evidence candidate
                                     WHERE candidate.raw_item_id=raw.id)
                              OR EXISTS(SELECT 1 FROM intelligence_event_evidence evidence
                                        JOIN intelligence_events event ON event.id=evidence.event_id AND event.status='active'
                                        WHERE evidence.raw_item_id=raw.id) AS represented
                              FROM intelligence_raw_items raw
                              JOIN intelligence_sources source ON source.source_key=raw.source_key
                              WHERE source.enabled AND source.adapter=ANY(%s)
                                AND raw.observed_at>=NOW()-INTERVAL '24 hours'
                              ORDER BY raw.observed_at DESC,raw.id DESC""", (benchmark_adapters,))
            benchmark_items = [dict(row) for row in cursor.fetchall()]
            cursor.execute("""SELECT COUNT(DISTINCT event.id)::int AS total,
                              COUNT(DISTINCT event.id) FILTER (WHERE evidence.event_id IS NULL)::int AS without_evidence
                              FROM intelligence_events event LEFT JOIN intelligence_event_evidence evidence ON evidence.event_id=event.id
                              WHERE event.status='active'""")
            events = dict(cursor.fetchone())
        supported = {"github_trending", "github_search_api", "rss_feed", "hacker_news_api", "hugging_face_api", "arxiv_api", "community_zhihu", "community_baidu",
                     "community_tencent", "community_csdn", "aliyun_solutions", "huawei_solutions", "product_hunt_feed",
                     "github_search_api", "ai_applications_official", "competitor_news"}
        for source in sources:
            source["adapter_status"] = "supported" if source["adapter"] in supported else "not_connected"
            source["coverage_status"] = "disabled" if not source["enabled"] else "missing" if not source["items_24h"] else source["health_status"]
        benchmark_by_source = {}
        missing_items = []
        for item in benchmark_items:
            stats = benchmark_by_source.setdefault(item["source_key"],
                {"source_key": item["source_key"], "name": item["name"], "observed": 0, "represented": 0})
            stats["observed"] += 1
            stats["represented"] += int(item["represented"])
            if not item["represented"]:
                missing_items.append({"id": item["id"], "source_key": item["source_key"], "source_name": item["name"],
                    "title": item["title"], "canonical_url": item["canonical_url"], "observed_at": item["observed_at"],
                    "reason": "尚未关联 Candidate 或有效 Event；请检查跨源印证、重复提及与增长阈值。"})
        benchmark_coverage = []
        for stats in benchmark_by_source.values():
            stats["coverage_rate"] = round(stats["represented"] * 100 / stats["observed"], 1)
            benchmark_coverage.append(stats)
        total_benchmark = sum(item["observed"] for item in benchmark_coverage)
        represented_benchmark = sum(item["represented"] for item in benchmark_coverage)
        return {"sources": sources, "candidates": candidates, "events": events,
                "recent_runs": recent_runs(20), "benchmark_coverage": {
                    "window": "24h", "observed": total_benchmark, "represented": represented_benchmark,
                    "missing_count": total_benchmark - represented_benchmark,
                    "coverage_rate": round(represented_benchmark * 100 / total_benchmark, 1) if total_benchmark else None,
                    "by_source": benchmark_coverage, "missing_items": missing_items[:50]},
                "benchmarks": [source["name"] for source in sources
                               if source["enabled"] and source["adapter"] in benchmark_adapters]}
    return await asyncio.to_thread(report)


@router.get("/admin/coverage/recall-benchmark")
async def hotspot_recall_benchmark(days: int = Query(30, ge=1, le=365), _=Depends(require_admin)):
    return await asyncio.to_thread(recall_report, days)


@router.post("/admin/coverage/recall-benchmark", status_code=201)
async def label_hotspot_reference(request: RecallBenchmarkLabel, admin=Depends(require_admin)):
    return await asyncio.to_thread(record_reference, request.model_dump(), str(admin.id))


@router.get("/admin/audit")
async def audit(limit: int = Query(100, ge=1, le=500), _=Depends(require_admin)):
    def rows():
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""SELECT id,actor_user_id,action,object_type,object_key,before_state,after_state,created_at
                              FROM intelligence_audit ORDER BY created_at DESC,id DESC LIMIT %s""", (limit,))
            return [dict(row) for row in cursor.fetchall()]
    return {"items": await asyncio.to_thread(rows)}


@router.get("/admin/email-deliveries")
async def email_deliveries(limit: int = Query(100, ge=1, le=500), _=Depends(require_admin)):
    def rows():
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""SELECT subscriber_id,recipient_email,delivery_date,delivery_type,status,
                              attempts,last_error,sent_at,updated_at FROM email_delivery_attempts
                              ORDER BY delivery_date DESC,updated_at DESC LIMIT %s""", (limit,))
            return [dict(row) for row in cursor.fetchall()]
    return {"items": await asyncio.to_thread(rows)}


@router.patch("/admin/sources/{source_key}/enabled")
async def update_source_state(source_key: str, state: SourceState, admin=Depends(require_admin)):
    source = next((item for item in await asyncio.to_thread(list_sources) if item["source_key"] == source_key), None)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    task_key = source_task_key(source)
    if state.enabled and task_key not in TASK_BY_KEY and source.get("adapter") not in COMMUNITY_ADAPTERS:
        raise HTTPException(status_code=409, detail="No collector task is registered for this source")
    source = await asyncio.to_thread(set_source_enabled, source_key, state.enabled, str(admin.id))
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.patch("/admin/sources/{source_key}")
async def edit_source(source_key: str, changes: SourceUpdate, admin=Depends(require_admin)):
    try:
        source = await asyncio.to_thread(update_source, source_key,
                                         changes.model_dump(exclude_unset=True, exclude_none=True), str(admin.id))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.patch("/admin/sources/{source_key}/schedule")
async def edit_source_schedule(source_key: str, changes: SourceScheduleUpdate, request: Request,
                               admin=Depends(require_admin)):
    try:
        schedule = await asyncio.to_thread(update_source_schedule, source_key, changes.cron, str(admin.id))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if not schedule:
        raise HTTPException(status_code=404, detail="Source not found")
    task_key = schedule["task_key"]
    set_task_schedule(task_key, schedule["cron"])
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler and scheduler.get_job(task_key):
        scheduler.reschedule_job(task_key, trigger=task_trigger(TASK_BY_KEY[task_key]))
    return schedule


@router.post("/admin/sources/{source_key}/test")
async def test_source(source_key: str, admin=Depends(require_admin)):
    result = await asyncio.to_thread(test_source_connection, source_key, str(admin.id))
    if not result:
        raise HTTPException(status_code=404, detail="Source not found")
    return result


@router.post("/admin/sources/{source_key}/run", status_code=202)
async def run_source(source_key: str, background_tasks: BackgroundTasks, _=Depends(require_admin)):
    sources = await asyncio.to_thread(list_sources)
    source = next((item for item in sources if item["source_key"] == source_key), None)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if not source["enabled"]:
        raise HTTPException(status_code=409, detail="Source is disabled")
    task_key = source_task_key(source)
    if source.get("adapter") in COMMUNITY_ADAPTERS:
        from services.community_insight_service import refresh_community_source
        background_tasks.add_task(refresh_community_source, source_key)
        return {"status": "accepted", "source_key": source_key, "mode": "request_cache_source_refresh"}
    if task_key not in TASK_BY_KEY:
        raise HTTPException(status_code=409, detail="No collector task is registered for this source")
    background_tasks.add_task(run_task, task_key, "source_manual")
    return {"status": "accepted", "source_key": source_key, "task_key": task_key}


@router.get("/admin/candidates")
async def candidates(status: Literal["pending", "approved", "ignored"] = "pending",
                     limit: int = Query(50, ge=1, le=200), _=Depends(require_admin)):
    return {"items": await asyncio.to_thread(list_candidates, status, limit)}


@router.post("/admin/candidates/{candidate_id}/approve")
async def approve_candidate_route(candidate_id: int, request: CandidateApproval, admin=Depends(require_admin)):
    try:
        return await asyncio.to_thread(approve_candidate, candidate_id, request.business_scopes, str(admin.id))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/admin/candidates/{candidate_id}/ignore")
async def ignore_candidate_route(candidate_id: int, request: CandidateIgnore, admin=Depends(require_admin)):
    try:
        return await asyncio.to_thread(ignore_candidate, candidate_id, str(admin.id), request.reason)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/admin/prompts")
async def prompts(_=Depends(require_admin)):
    return {"items": await asyncio.to_thread(list_prompts)}


@router.post("/admin/prompts")
async def save_prompt_draft(request: PromptDraft, admin=Depends(require_admin)):
    return await asyncio.to_thread(create_draft, request.prompt_name, request.scenario,
                                   request.system_prompt, request.user_prompt_template, str(admin.id))


@router.post("/admin/prompts/{prompt_id}/publish")
async def publish_prompt_route(prompt_id: int, admin=Depends(require_admin)):
    try:
        return await asyncio.to_thread(publish_prompt, prompt_id, str(admin.id))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/admin/prompts/{prompt_id}/rollback")
async def rollback_prompt_route(prompt_id: int, admin=Depends(require_admin)):
    try:
        return await asyncio.to_thread(publish_prompt, prompt_id, str(admin.id), True)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/admin/events/{source_id}/merge")
async def merge_event(source_id: int, request: EventMerge, admin=Depends(require_admin)):
    try:
        return await asyncio.to_thread(merge_events, source_id, request.target_id, str(admin.id), request.reason)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/admin/events/{event_id}/split")
async def split_event_route(event_id: int, request: EventSplit, admin=Depends(require_admin)):
    try:
        return await asyncio.to_thread(split_event, event_id, request.evidence_ids, request.title, str(admin.id), request.reason)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.patch("/admin/events/{event_id}")
async def correct_event(event_id: int, request: EventUpdate, admin=Depends(require_admin)):
    try:
        return await asyncio.to_thread(update_event, event_id, request.model_dump(exclude_unset=True, exclude_none=True), str(admin.id))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/admin/events/{event_id}/rescore")
async def rescore_event_route(event_id: int, admin=Depends(require_admin)):
    try:
        return await asyncio.to_thread(rescore_event, event_id, str(admin.id))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
