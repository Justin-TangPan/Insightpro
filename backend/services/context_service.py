"""The single read boundary between InsightPro entities and interactive AI."""
from __future__ import annotations

from datetime import date
from fastapi import HTTPException

from repositories import context_repository as repository
from services import workbench_service

CONTEXT_TYPES = {"github_project", "cloud_solution", "vendor_update", "requirement", "solution"}
MAX_CONTENT = 12_000


def _content(*parts: str | None) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())[:MAX_CONTENT]


def _context(context_type: str, context_id: str, title: str, summary: str, metadata: dict, content: str, source_url: str | None, related: list[dict] | None = None) -> dict:
    return {
        "context_type": context_type,
        "context_id": str(context_id),
        "title": title,
        "summary": summary[:2000],
        "metadata": metadata,
        "content": content,
        "related_entities": related or [],
        "source_url": source_url or "",
        "snapshot_at": date.today().isoformat(),
    }


def get_context(user_id: str, context_type: str, context_id: str) -> dict:
    if context_type not in CONTEXT_TYPES:
        raise HTTPException(status_code=422, detail="不支持的 Context 类型")
    if context_type == "requirement":
        item = workbench_service.get_requirement(user_id, int(context_id))
        related = [{"type": "solution", "id": str(s["id"]), "title": s["name"]} for s in item["solutions"]]
        return _context(context_type, context_id, item["title"], item["description"], {"status": item["status"], "priority": item["priority"], "source_type": item["source_type"], "source_id": item["source_id"]}, _content(f"Requirement: {item['title']}", item["description"]), item["source_url"], related)
    if context_type == "solution":
        item = workbench_service.get_solution(user_id, int(context_id))
        related = [{"type": "requirement", "id": str(r["id"]), "title": r["title"], "source_type": r["source_type"], "source_id": r["source_id"], "source_url": r["source_url"]} for r in item["requirements"]]
        return _context(context_type, context_id, item["name"], item["description"], {"category": item["category"], "status": item["status"], "version": item["version"]}, _content(f"Solution: {item['name']}", item["description"]), item["reference_url"], related)
    if context_type == "github_project":
        item = repository.github_project(context_id)
        if not item:
            raise HTTPException(status_code=404, detail="GitHub Project 不存在")
        related = [{"type": "requirement", "id": str(r["id"]), "title": r["title"]} for r in repository.related_requirements(user_id, "github_project", context_id)]
        metadata = {key: item.get(key) for key in ("repo_url", "language", "stars", "forks", "today_stars", "scrape_date", "evaluation_score", "evaluation_level", "recommendation")}
        return _context(context_type, context_id, item["repo_name"], item.get("evaluation_summary") or item.get("description") or "", metadata, _content(f"Project: {item['repo_name']}", item.get("description"), item.get("evaluation_summary"), item.get("reasoning")), item.get("repo_url"), related)
    if context_type == "cloud_solution":
        item = repository.cloud_solution(int(context_id))
        if not item:
            raise HTTPException(status_code=404, detail="Cloud Solution 不存在")
        related = [{"type": "requirement", "id": str(r["id"]), "title": r["title"]} for r in repository.related_requirements(user_id, "cloud_solution", context_id)]
        return _context(context_type, context_id, item["title"], item["summary"], {"category": item["category"], "last_changed_date": item["last_changed_date"]}, _content(f"Cloud Solution: {item['title']}", item["summary"], item.get("source_description")), item["url"], related)
    item = repository.vendor_update(int(context_id))
    if not item:
        raise HTTPException(status_code=404, detail="Vendor Update 不存在")
    return _context(context_type, context_id, item["title"], item.get("summary") or "", {"vendor": item["vendor"], "category": item.get("category"), "crawl_date": item["crawl_date"]}, _content(f"Vendor Update: {item['title']}", item.get("summary")), item.get("url"))
