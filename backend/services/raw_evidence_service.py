"""Single write path for immutable source evidence versions."""
from __future__ import annotations

import json
from services.data_semantics import canonical_url


def store_raw_version(cursor, *, source_key: str, url: str, title: str, content: dict,
                      content_hash: str, published_at=None, observed_at=None,
                      external_native_id: str | None = None, identity_suffix: str = "") -> dict:
    source_url = str(url or "").strip()
    if not canonical_url(source_url) and not (external_native_id or "").strip():
        raise ValueError("Raw evidence needs a stable source URL or verified native ID")
    if source_url and not canonical_url(source_url):
        raise ValueError("Raw evidence URL is invalid")
    native_id = (external_native_id or "").strip()
    identity = f"native:{native_id}{identity_suffix}" if native_id else source_url + identity_suffix
    if native_id and source_url:
        cursor.execute("""SELECT identity_key FROM intelligence_source_objects
            WHERE source_key=%s AND identity_key=%s""", (source_key, source_url + identity_suffix))
        if cursor.fetchone():
            identity = source_url + identity_suffix
    cursor.execute("""INSERT INTO intelligence_source_objects
        (source_key,identity_key,external_native_id,canonical_url,first_seen_at,last_seen_at)
        VALUES (%s,%s,%s,%s,COALESCE(%s::timestamptz,NOW()),NOW())
        ON CONFLICT (source_key,identity_key) DO UPDATE SET
          last_seen_at=NOW(),updated_at=NOW(),
          canonical_url=COALESCE(EXCLUDED.canonical_url,intelligence_source_objects.canonical_url),
          external_native_id=COALESCE(intelligence_source_objects.external_native_id,EXCLUDED.external_native_id)
        RETURNING id,current_raw_id,current_version,migration_status""",
        (source_key, identity, external_native_id, source_url or None, observed_at))
    obj = cursor.fetchone()
    if obj["migration_status"] != "resolved":
        raise ValueError("Source Object identity or version order needs review")
    if obj["current_raw_id"]:
        cursor.execute("""SELECT id,content_hash,title,canonical_url,published_at,observed_at,source_version
            FROM intelligence_raw_items WHERE id=%s""", (obj["current_raw_id"],))
        current = cursor.fetchone()
        same_published = str(current["published_at"] or "")[:10] == str(published_at or "")[:10]
        if (current["content_hash"] == content_hash and current["title"] == title
                and current["canonical_url"] == (source_url or None) and same_published):
            cursor.execute("UPDATE intelligence_raw_items SET last_seen_at=NOW() WHERE id=%s", (current["id"],))
            return {"id": current["id"], "observed_at": current["observed_at"],
                    "content_version": current["source_version"], "change": "no_change"}
    next_version = obj["current_version"] + 1
    cursor.execute("""INSERT INTO intelligence_raw_items
        (source_key,external_id,canonical_url,title,content,content_hash,observed_at,published_at,
         source_object_id,source_version,content_version)
        VALUES (%s,%s,%s,%s,%s::jsonb,%s,COALESCE(%s::timestamptz,NOW()),%s::timestamptz,%s,%s,%s)
        RETURNING id,observed_at""",
        (source_key, f"source-object:{obj['id']}:v{next_version}", source_url or None, title,
         json.dumps(content, ensure_ascii=False, default=str), content_hash, observed_at, published_at,
         obj["id"], next_version, next_version))
    raw = cursor.fetchone()
    cursor.execute("""UPDATE intelligence_source_objects
        SET current_raw_id=%s,current_version=%s,last_seen_at=NOW(),updated_at=NOW()
        WHERE id=%s""", (raw["id"], next_version, obj["id"]))
    if obj["current_raw_id"]:
        cursor.execute("""INSERT INTO intelligence_raw_changes
            (raw_item_id,old_hash,new_hash,content_version) VALUES (%s,%s,%s,%s)""",
            (raw["id"], current["content_hash"], content_hash, next_version))
    return {"id": raw["id"], "observed_at": raw["observed_at"], "content_version": next_version,
            "change": "changed" if obj["current_raw_id"] else "new"}
