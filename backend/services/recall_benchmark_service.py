"""Record independent hotspot labels and measure collector recall against them."""
import json

from db import get_db


def record_reference(item: dict, actor_user_id: str) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT id,title,reference_source,is_relevant,label_reason,labeled_by
                          FROM intelligence_recall_benchmark
                          WHERE canonical_url=%s AND reference_at=%s FOR UPDATE""",
                       (item["canonical_url"], item["reference_at"]))
        previous = cursor.fetchone()
        cursor.execute("""INSERT INTO intelligence_recall_benchmark
            (title,canonical_url,reference_source,reference_at,is_relevant,label_reason,labeled_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s::uuid)
            ON CONFLICT (canonical_url,reference_at) DO UPDATE SET
              title=EXCLUDED.title,reference_source=EXCLUDED.reference_source,
              is_relevant=EXCLUDED.is_relevant,label_reason=EXCLUDED.label_reason,
              labeled_by=EXCLUDED.labeled_by,updated_at=NOW()
            RETURNING id,title,canonical_url,reference_source,reference_at,is_relevant,label_reason,labeled_by,updated_at""",
            (item["title"], item["canonical_url"], item["reference_source"], item["reference_at"],
             item["is_relevant"], item["label_reason"], actor_user_id))
        saved = dict(cursor.fetchone())
        cursor.execute("""INSERT INTO intelligence_audit
            (actor_user_id,action,object_type,object_key,before_state,after_state)
            VALUES (%s::uuid,'hotspot_benchmark_labeled','recall_benchmark',%s,%s::jsonb,%s::jsonb)""",
            (actor_user_id, str(saved["id"]), json.dumps(dict(previous) if previous else None, default=str),
             json.dumps(saved, default=str)))
    return saved


def recall_report(days: int = 30, limit: int = 100) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""WITH reviewed AS (
            SELECT reference.id,reference.title,reference.canonical_url,reference.reference_source,
                   reference.reference_at,reference.is_relevant,reference.label_reason,
                   match.raw_id,match.source_key,match.event_id,COALESCE(match.represented,FALSE) AS represented
            FROM intelligence_recall_benchmark reference
            LEFT JOIN LATERAL (
                SELECT raw.id AS raw_id,raw.source_key,
                       (SELECT evidence.event_id FROM intelligence_event_evidence evidence
                        JOIN intelligence_events event ON event.id=evidence.event_id AND event.status='active'
                        WHERE evidence.raw_item_id=raw.id ORDER BY evidence.event_id LIMIT 1) AS event_id,
                       EXISTS(SELECT 1 FROM intelligence_candidate_evidence candidate
                              WHERE candidate.raw_item_id=raw.id)
                       OR EXISTS(SELECT 1 FROM intelligence_event_evidence evidence
                                 WHERE evidence.raw_item_id=raw.id) AS represented
                FROM intelligence_raw_items raw
                WHERE lower(raw.canonical_url)=lower(reference.canonical_url)
                  AND raw.observed_at>=reference.reference_at
                  AND raw.observed_at<reference.reference_at+INTERVAL '24 hours'
                ORDER BY represented DESC,raw.observed_at,raw.id LIMIT 1
            ) match ON TRUE
            WHERE reference.reference_at>=NOW()-(%s * INTERVAL '1 day')
        ) SELECT * FROM reviewed ORDER BY reference_at DESC,id DESC""", (days,))
        rows = [dict(row) for row in cursor.fetchall()]

    relevant = [row for row in rows if row["is_relevant"]]
    found = [row for row in relevant if row["raw_id"] is not None]
    represented = [row for row in relevant if row["represented"]]
    by_source = {}
    for row in relevant:
        item = by_source.setdefault(row["reference_source"], {"reference_source": row["reference_source"],
                                                                "relevant": 0, "found": 0, "represented": 0})
        item["relevant"] += 1
        item["found"] += int(row["raw_id"] is not None)
        item["represented"] += int(row["represented"])
    for item in by_source.values():
        item["recall_rate"] = round(item["found"] * 100 / item["relevant"], 1)
        item["event_rate"] = round(item["represented"] * 100 / item["relevant"], 1)
    return {
        "window_days": days,
        "match_window_hours": 24,
        "sample_count": len(rows),
        "relevant_count": len(relevant),
        "found_count": len(found),
        "missed_count": len(relevant) - len(found),
        "recall_rate": round(len(found) * 100 / len(relevant), 1) if relevant else None,
        "represented_count": len(represented),
        "event_rate": round(len(represented) * 100 / len(relevant), 1) if relevant else None,
        "by_source": sorted(by_source.values(), key=lambda item: item["reference_source"]),
        "items": [{**row, "found": row["raw_id"] is not None,
                   "represented": bool(row["represented"])} for row in rows[:limit]],
    }
