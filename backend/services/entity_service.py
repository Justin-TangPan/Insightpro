"""Entity detail backed by the shared Event, Evidence and Metric model."""
from __future__ import annotations

from db import get_db
from services.metric_service import trends_for_entity


def get_entity_detail(entity_key: str) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT entity_key,entity_type,canonical_name,canonical_url,metadata
                          FROM intelligence_entities WHERE entity_key=%s""", (entity_key,))
        entity = cursor.fetchone()
        if not entity:
            return None
        cursor.execute("""SELECT id,event_type,title,summary,business_scopes,scores,first_seen_at,last_seen_at
                          FROM intelligence_events WHERE entity_key=%s AND status='active'
                          ORDER BY last_seen_at DESC,id DESC LIMIT 100""", (entity_key,))
        events = [dict(row) for row in cursor.fetchall()]
        cursor.execute("""SELECT DISTINCT ON (raw.id) raw.id,raw.title,raw.canonical_url,raw.published_at,
                                 raw.observed_at,source.name AS source_name,source.authority
                          FROM intelligence_event_evidence evidence
                          JOIN intelligence_events event ON event.id=evidence.event_id AND event.status='active'
                          JOIN intelligence_raw_items raw ON raw.id=evidence.raw_item_id
                          JOIN intelligence_sources source ON source.source_key=raw.source_key
                          WHERE event.entity_key=%s ORDER BY raw.id,raw.observed_at DESC""", (entity_key,))
        evidence = [dict(row) for row in cursor.fetchall()]
        cursor.execute("""SELECT metric_key,metric_value,observed_at,source_key,raw_item_id
                          FROM intelligence_metric_snapshots WHERE entity_key=%s
                          ORDER BY observed_at DESC,id DESC LIMIT 100""", (entity_key,))
        metrics = [dict(row) for row in cursor.fetchall()]
        trends = trends_for_entity(cursor, entity_key)
    return {"entity": dict(entity), "events": events, "evidence": evidence, "metrics": metrics, "trends": trends}
