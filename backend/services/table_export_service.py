"""Bounded, filter-aware administrator CSV/XLSX exports."""
from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime

from openpyxl import Workbook

from db import get_db


MAX_ROWS = 10000
DATASETS = {
    "event": ("intelligence_events e", "e.last_seen_at", "e.id", ["id", "event_key", "title", "summary", "event_type", "business_scopes", "status", "analysis_status", "content_version", "analysis_version", "published_at", "last_seen_at"], "e.business_scopes"),
    "candidate": ("intelligence_candidates e", "e.last_seen_at", "e.id", ["id", "candidate_key", "title", "canonical_url", "business_scopes", "status", "source_count", "mention_count", "discovery_score", "last_seen_at"], "e.business_scopes"),
    "data_source": ("intelligence_sources e", "e.updated_at", "e.source_key", ["source_key", "name", "adapter", "business_scopes", "enabled", "health_status", "last_success_at", "last_error", "updated_at"], "e.business_scopes"),
    "pipeline_run": ("platform_task_runs e", "e.started_at", "e.id", ["id", "task_key", "trigger", "status", "started_at", "finished_at", "input_count", "new_count", "changed_count", "skipped_count", "failed_count", "error"], None),
    "inspection_result": ("intelligence_inspection_results e JOIN intelligence_sources s ON s.source_key=e.source_key", "e.checked_at", "e.id", ["id", "source_key", "status", "stages", "checked_at"], "s.business_scopes"),
}


def _cell(value):
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, ensure_ascii=False, default=str)
    elif isinstance(value, (date, datetime)):
        value = value.isoformat()
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value if value is not None else ""


def export_table(dataset: str, fmt: str, *, status: str | None = None,
                 business_scope: str | None = None, date_from: date | None = None,
                 date_to: date | None = None, sort: str = "desc") -> bytes:
    if dataset not in DATASETS or fmt not in {"csv", "xlsx"} or sort not in {"asc", "desc"}:
        raise ValueError("Unsupported export dataset, format or sort")
    if date_from and date_to and date_from > date_to:
        raise ValueError("date_from must not exceed date_to")
    table, date_column, key_column, fields, scope_column = DATASETS[dataset]
    conditions, params = (["e.task_key LIKE 'pipeline:%%'"] if dataset == "pipeline_run" else []), []
    if status:
        status_column = "e.health_status" if dataset == "data_source" else "e.status"
        conditions.append(f"{status_column}=%s")
        params.append(status)
    if business_scope:
        if dataset == "pipeline_run":
            conditions.append("e.result->>'domain'=%s")
        else:
            conditions.append(f"%s=ANY({scope_column})")
        params.append(business_scope)
    if date_from:
        conditions.append(f"{date_column}::date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append(f"{date_column}::date <= %s")
        params.append(date_to)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    select_fields = ",".join(f"e.{field}" for field in fields)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) AS count FROM {table}{where}", params)
        if cursor.fetchone()["count"] > MAX_ROWS:
            raise ValueError("Export exceeds 10000 rows; narrow the filters or time range")
        cursor.execute(f"""SELECT {select_fields} FROM {table}{where}
            ORDER BY {date_column} {sort.upper()}, {key_column} {sort.upper()} LIMIT {MAX_ROWS}""", params)
        if fmt == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(fields)
            while rows := cursor.fetchmany(500):
                writer.writerows([_cell(row[field]) for field in fields] for row in rows)
            return ("\ufeff" + output.getvalue()).encode("utf-8")
        workbook = Workbook(write_only=True)
        sheet = workbook.create_sheet(dataset[:31])
        sheet.append(fields)
        while rows := cursor.fetchmany(500):
            for row in rows:
                sheet.append([_cell(row[field]) for field in fields])
        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue()
