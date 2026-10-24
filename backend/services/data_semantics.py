"""Small shared normalization primitives; alias and taxonomy values are caller supplied."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from urllib.parse import urlsplit, urlunsplit


def canonical_url(value: str, *, strip_query: bool = False) -> str:
    try:
        parsed = urlsplit(str(value or "").strip())
        if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
            return ""
        netloc = parsed.netloc.casefold()
        path = parsed.path.rstrip("/")
        return urlunsplit((parsed.scheme.lower(), netloc, path, "" if strip_query else parsed.query, ""))
    except ValueError:
        return ""


def normalized_entity_name(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).casefold().split())


def resolve_alias(value: str, aliases: dict[str, str] | None = None) -> str:
    normalized = normalized_entity_name(value)
    return next((canonical for alias, canonical in (aliases or {}).items()
                 if normalized_entity_name(alias) == normalized), value.strip())


def map_taxonomy(value: str, mappings: dict[str, str] | None = None) -> str:
    """Map only explicitly supplied aliases; preserve unknown source labels verbatim."""
    normalized = normalized_entity_name(value)
    return next((canonical for alias, canonical in (mappings or {}).items()
                 if normalized_entity_name(alias) == normalized), value)


def time_fields(*, published_at=None, event_at=None, observed_at=None, updated_at=None, analyzed_at=None) -> dict:
    """Keep source, event, observation, record-update and analysis times independent."""
    return {"published_at": published_at, "event_at": event_at, "observed_at": observed_at,
            "updated_at": updated_at, "analyzed_at": analyzed_at}


def published_date(value) -> str | None:
    """Accept an explicit day only; unknown or partial publication dates remain unknown."""
    value = str(value or "")
    return value if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) else None


def explicit_timestamp(value):
    """Accept a full date/time value; reject partial dates instead of inventing a day."""
    if isinstance(value, (date, datetime)):
        return value
    value = str(value or "").strip()
    if not value:
        return None
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value
    except ValueError:
        try:
            date.fromisoformat(value)
            return value
        except ValueError:
            return None
