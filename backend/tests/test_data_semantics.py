from services.data_semantics import (
    canonical_url, explicit_timestamp, map_taxonomy, normalized_entity_name,
    published_date, resolve_alias, time_fields,
)


def test_canonical_url_and_entity_name_normalization_are_stable():
    assert canonical_url("HTTPS://Example.COM/path/?q=1#section") == "https://example.com/path?q=1"
    assert canonical_url("https://example.com/path/?q=1#section", strip_query=True) == "https://example.com/path"
    assert canonical_url("javascript:alert(1)") == ""
    assert normalized_entity_name("  Ａgent   Cloud ") == "agent cloud"


def test_alias_and_taxonomy_mapping_only_use_caller_supplied_values():
    aliases = {"ＡＷＳ": "AWS"}
    assert resolve_alias("aws", aliases) == "AWS"
    assert resolve_alias("Unknown Vendor", aliases) == "Unknown Vendor"
    assert map_taxonomy("Agent", {"智能体": "Agent"}) == "Agent"
    assert map_taxonomy("Unmapped label") == "Unmapped label"


def test_time_fields_keep_publication_event_observation_and_analysis_distinct():
    times = time_fields(published_at=None, event_at="2026-10-20T08:00:00Z",
                        observed_at="2026-10-23T09:00:00+08:00", updated_at="record-time", analyzed_at="ai-time")
    assert times == {"published_at": None, "event_at": "2026-10-20T08:00:00Z",
                     "observed_at": "2026-10-23T09:00:00+08:00", "updated_at": "record-time",
                     "analyzed_at": "ai-time"}
    assert published_date("2026-10") is None
    assert explicit_timestamp("2026-10") is None
    assert explicit_timestamp("2026-10-20T08:00:00Z") == "2026-10-20T08:00:00Z"
