"""Shared display contract for source-backed intelligence records."""
from __future__ import annotations
from typing import Literal, TypedDict


class Intelligence(TypedDict):
    kind: Literal["github_project", "cloud_solution", "competitor_update", "ai_application"]
    key: str
    title: str
    brief: str
    analysis: str | None
    source: str | None
    analysis_id: int | str | None


class SolutionIntelligence(Intelligence, total=False):
    solution_value: str
    open_source_projects: str
    cloud_resources: str


def project(item: dict) -> Intelligence:
    return {"kind": "github_project", "key": item.get("repo_name") or "", "title": item.get("repo_name") or "",
            "brief": item.get("summary") or item.get("description") or "",
            "analysis": item.get("reasoning"), "source": item.get("repo_url"),
            "analysis_id": item.get("analysis_id")}


def solution(item: dict) -> SolutionIntelligence:
    summary = item.get("summary") or ""
    vendor = item.get("vendor") or "Alibaba Cloud"
    value = summary.partition("; Open-source projects:")[0].removeprefix("Solution value:").strip() if summary.startswith("Solution value:") else summary.strip()
    brief = value or (item.get("source_description") or "").strip() or item["title"]
    projects = summary.partition("Open-source projects:")[2].partition(f"; {vendor} resources:")[0].strip() if "Open-source projects:" in summary else ""
    resources = summary.partition(f"{vendor} resources:")[2].strip() if f"{vendor} resources:" in summary else ""
    return {"kind": "cloud_solution", "key": item["url"], "title": item["title"],
            "brief": brief, "analysis": summary if item.get("analysis_mode") != "source" and summary.startswith("Solution value:") else None,
            "source": item["url"], "analysis_id": item.get("id") if item.get("analysis_mode") != "source" else None,
            "solution_value": brief, "open_source_projects": projects,
            "cloud_resources": resources}


def competitor(item: dict) -> Intelligence:
    return {"kind": "competitor_update", "key": f"{item.get('link') or item['vendor']}::{item['title']}",
            "title": item["title"], "brief": item.get("summary") or "",
            "analysis": item.get("analysis"), "source": item.get("link"), "analysis_id": item.get("analysis_id")}


def application(item: dict) -> Intelligence:
    return {"kind": "ai_application", "key": item["url"], "title": item["title"],
            "brief": item.get("summary") or "", "analysis": item.get("analysis"),
            "source": item["url"], "analysis_id": item.get("analysis_id")}
