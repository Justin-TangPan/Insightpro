from datetime import date, datetime, timedelta, timezone

from services import discovery_service
from services.discovery_service import _candidate_groups, _parse_arxiv_feed, _parse_rss_feed


def test_rss_and_atom_discovery_parses_real_item_evidence():
    payload = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>tag:example.test,2026:item-1</id><title>  New Agent  Framework </title><link href="/posts/1"/><updated>2026-10-23T08:00:00Z</updated><summary>Useful signal</summary></entry></feed>'''
    items = _parse_rss_feed(payload, "https://example.test/feed", "2026-10-23")
    assert items == [{"external_id": "tag:example.test,2026:item-1:2026-10-23", "url": "https://example.test/posts/1",
                      "title": "New Agent Framework", "published_at": "2026-10-23T08:00:00Z",
                      "content": {"summary": "Useful signal", "kind": "feed_item"}}]


def test_rss_discovery_fetches_and_parses_feed_without_following_redirects(monkeypatch):
    calls = []
    class Response:
        content = b'<rss><channel><item><title>Launch</title><link>/launch</link><guid>launch-1</guid></item></channel></rss>'
        status_code = 200
        def raise_for_status(self): pass
    def get(url, **kwargs): calls.append((url, kwargs)); return Response()
    monkeypatch.setattr(discovery_service, "requests", type("Requests", (), {"get": staticmethod(get)}))
    items = discovery_service._fetch_discovery_items({"adapter": "rss_feed", "base_url": "https://example.test/feed"}, "2026-10-23")
    assert calls[0][1]["allow_redirects"] is False
    assert items[0]["url"] == "https://example.test/launch"


def test_discovery_groups_cross_source_evidence_without_promoting_events():
    now = datetime.now(timezone.utc)
    candidates = _candidate_groups([
        {"id": 1, "title": "New Agent Framework", "canonical_url": "https://example.com/a", "source_key": "community_zhihu", "authority": "P2", "observed_at": now},
        {"id": 2, "title": "New Agent Framework!", "canonical_url": "https://example.com/b", "source_key": "community_csdn", "authority": "P2", "observed_at": now},
        {"id": 3, "title": "A one-off discussion", "canonical_url": "https://example.com/c", "source_key": "community_zhihu", "authority": "P2", "observed_at": now},
    ])

    assert len(candidates) == 1
    assert candidates[0]["source_count"] == 2
    assert candidates[0]["mention_count"] == 2
    assert candidates[0]["raw_ids"] == [1, 2]
    assert candidates[0]["business_scopes"] == ["community_insights"]


def test_discovery_keeps_a_single_high_signal_project_as_candidate():
    item = {"id": 4, "title": "Open Agent Framework", "canonical_url": "https://github.com/example/agent",
            "source_key": "hacker_news", "authority": "P1", "observed_at": datetime.now(timezone.utc),
            "content": {"points": 240}}
    candidates = _candidate_groups([item])
    assert len(candidates) == 1
    assert candidates[0]["business_scopes"] == ["technology_ecosystem"]
    assert candidates[0]["discovery_score"] >= 60


def test_discovery_prioritizes_repository_growth_over_static_star_totals():
    now = datetime.now(timezone.utc)
    rows = [
        {"id": 51, "title": "team/agent-kit", "canonical_url": "https://github.com/team/agent-kit",
         "source_key": "github_search", "authority": "P1", "business_scopes": ["technology_ecosystem"],
         "observed_at": now - timedelta(days=1),
         "content": {"kind": "repository", "stars": 300}},
        {"id": 52, "title": "team/agent-kit", "canonical_url": "https://github.com/team/agent-kit",
         "source_key": "github_search", "authority": "P1", "business_scopes": ["technology_ecosystem"],
         "observed_at": now, "content": {"kind": "repository", "stars": 3000}},
    ]
    static = {**rows[0], "id": 53, "title": "team/established", "canonical_url": "https://github.com/team/established",
              "observed_at": now, "content": {"kind": "repository", "stars": 100000}}

    candidates = _candidate_groups([*rows, static])

    assert len(candidates) == 1
    assert candidates[0]["entity_type"] == "repository"
    assert candidates[0]["title"] == "team/agent-kit"


def test_github_search_adapter_returns_real_repo_metrics(monkeypatch):
    requested = []
    monkeypatch.setattr(discovery_service.time, "sleep", lambda _: None)
    item = {"full_name": "team/agent-kit", "html_url": "https://github.com/team/agent-kit",
            "description": "Agent toolkit", "language": "Python", "topics": ["agents"],
            "stargazers_count": 3000, "forks_count": 200, "created_at": "2026-10-01T00:00:00Z",
            "updated_at": "2026-10-23T00:00:00Z"}
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"items": [item]}
    def get(url, **kwargs):
        requested.append((url, kwargs))
        return Response()
    monkeypatch.setattr(discovery_service, "requests", type("Requests", (), {"get": staticmethod(get)}))

    result = discovery_service._fetch_discovery_items({"adapter": "github_search_api",
        "base_url": "https://api.example.test/search/repositories"}, "2026-10-23")

    assert result[0]["content"]["stars"] == 3000
    assert result[0]["content"]["forks"] == 200
    assert len(requested) == 6
    assert requested[0][0] == "https://api.example.test/search/repositories"
    assert requested[0][1]["params"]["per_page"] == 100
    assert requested[0][1]["params"]["q"].startswith("agent pushed:")
    assert all(" OR " not in request[1]["params"]["q"] for request in requested)


def test_github_search_requests_are_rate_limited(monkeypatch):
    clock = {"now": 100.0, "slept": 0.0}
    class FakeTime:
        @staticmethod
        def monotonic(): return clock["now"]
        @staticmethod
        def sleep(seconds):
            clock["slept"] += seconds
            clock["now"] += seconds
    monkeypatch.setattr(discovery_service, "time", FakeTime)
    monkeypatch.setattr(discovery_service, "_GITHUB_SEARCH_LAST_REQUEST", 0.0)
    monkeypatch.setattr(discovery_service, "requests", type("Requests", (), {"get": staticmethod(lambda *args, **kwargs: object())}))

    discovery_service._github_search_request("https://api.example.test/search", "q=agent")
    discovery_service._github_search_request("https://api.example.test/search", "q=MCP")

    assert clock["slept"] == 6.2


def test_github_search_raw_items_share_repository_entity_and_store_metrics(monkeypatch):
    statements = []
    class Cursor:
        def execute(self, query, params=()): statements.append((query, params))
        def fetchone(self): return {"id": 88, "observed_at": datetime.now(timezone.utc)}
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(discovery_service, "get_db", Connection)

    count = discovery_service._store_discovery_raw("github_search", [{
        "external_id": "team/agent-kit:2026-10-23", "url": "https://github.com/team/agent-kit",
        "title": "team/agent-kit", "content": {"kind": "repository", "full_name": "team/agent-kit", "stars": 3000, "forks": 200},
    }])

    entity = next(params for query, params in statements if "INSERT INTO intelligence_entities" in query)
    metric_keys = {params[3] for query, params in statements if "INSERT INTO intelligence_metric_snapshots" in query}
    assert count == 1
    assert entity[:2] == ("github:team/agent-kit", "repository")
    assert {"stars", "forks"} <= metric_keys


def test_approved_github_candidate_reuses_the_existing_repository_event(monkeypatch):
    now = datetime.now(timezone.utc)
    candidate = {"id": 9, "status": "pending", "entity_type": "repository",
                 "canonical_url": "https://github.com/team/agent-kit", "candidate_key": "agent-key",
                 "title": "team/agent-kit", "discovery_score": 82, "first_seen_at": now, "last_seen_at": now}
    statements, scored = [], []

    class Cursor:
        def execute(self, query, params=()):
            statements.append((query, params))
            self.query = query
        def fetchone(self):
            if "SELECT * FROM intelligence_candidates" in self.query:
                return candidate
            if "COUNT(DISTINCT raw.source_key)" in self.query:
                return {"source_count": 2, "evidence_count": 3}
            if "SELECT id,event_key FROM intelligence_events" in self.query:
                return {"id": 77, "event_key": "github-trending:team/agent-kit"}
            if "RETURNING id,event_key,last_seen_at" in self.query:
                return {"id": 77, "event_key": "github-trending:team/agent-kit", "last_seen_at": now}
            raise AssertionError(self.query)
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(discovery_service, "get_db", Connection)
    monkeypatch.setattr(discovery_service, "persist_event_hot_score",
                        lambda *args: scored.append(args[1:]) or {"value": 80})

    result = discovery_service.approve_candidate(9, ["technology_ecosystem"],
                                                 "00000000-0000-0000-0000-000000000001")

    assert result["event_id"] == 77
    assert not any("INSERT INTO intelligence_events" in query for query, _ in statements)
    assert any("event_key LIKE %s" in query and params[-1] == "github-trending:%" for query, params in statements)
    assert any("INSERT INTO intelligence_event_evidence" in query for query, _ in statements)
    assert scored == [(77, "github:team/agent-kit", "github-trending:team/agent-kit", now)]


def test_discovery_uses_registry_business_scopes_for_candidate_routing():
    item = {"id": 41, "title": "New arXiv agent paper", "canonical_url": "https://arxiv.org/abs/1234.5678",
            "source_key": "arxiv_ai", "authority": "P1", "business_scopes": ["technology_ecosystem"],
            "observed_at": datetime.now(timezone.utc), "content": {"kind": "research_paper"}}

    corroboration = {**item, "id": 43, "source_key": "hacker_news", "business_scopes": [],
                     "canonical_url": "https://example.com/paper"}
    candidates = _candidate_groups([item, corroboration])

    assert len(candidates) == 1
    assert candidates[0]["business_scopes"] == ["technology_ecosystem"]


def test_discovery_respects_updated_registry_scope_instead_of_source_key_guess():
    item = {"id": 42, "title": "Hacker News industry discussion", "canonical_url": "https://example.com/story",
            "source_key": "hacker_news", "authority": "P1", "business_scopes": ["community_insights"],
            "observed_at": datetime.now(timezone.utc), "content": {"points": 240}}

    candidates = _candidate_groups([item])

    assert candidates[0]["business_scopes"] == ["community_insights"]


def test_discovery_keeps_a_verified_product_hunt_listing_as_review_candidate():
    item = {"id": 5, "title": "New AI Product", "canonical_url": "https://www.producthunt.com/products/new-ai-product",
            "source_key": "product_hunt", "authority": "P2", "observed_at": datetime.now(timezone.utc),
            "content": {"kind": "ai_product", "tagline": "An AI product"}}
    candidates = _candidate_groups([item])

    assert len(candidates) == 1
    assert candidates[0]["entity_type"] == "ai_product"
    assert candidates[0]["source_count"] == 1
    assert candidates[0]["business_scopes"] == ["ai_applications"]


def test_product_hunt_feed_enters_raw_items_and_records_health(monkeypatch):
    today = date.today().isoformat()
    xml = f'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>VoiceNote</title>
      <published>{today}T12:00:00Z</published><content type="html">&lt;p&gt;AI voice notes for your day&lt;/p&gt;</content>
      <link rel="alternate" href="https://www.producthunt.com/products/voicenote" /></entry></feed>'''.encode()
    class Response:
        content = xml
        def raise_for_status(self): pass

    stored = []
    health = []
    requested = []
    def get(url, **kwargs):
        requested.append(url)
        return Response()
    monkeypatch.setattr(discovery_service, "requests", type("Requests", (), {"get": staticmethod(get)}))
    monkeypatch.setattr("services.source_registry_service.list_sources", lambda: [
        {"source_key": "custom_products", "enabled": True, "adapter": "product_hunt_feed",
         "base_url": "https://feed.example.test/products.xml",
         "schedule": {"task_key": "discovery_sentinel_daily"}},
    ])
    monkeypatch.setattr("services.source_registry_service.record_source_health", lambda *args: health.append(args))
    monkeypatch.setattr(discovery_service, "_store_discovery_raw", lambda source, items: stored.append((source, items)) or len(items))

    result = discovery_service._collect_discovery_feeds()

    assert result["custom_products"] == 1
    assert requested == ["https://feed.example.test/products.xml"]
    assert stored[0][0] == "custom_products"
    assert stored[0][1][0]["content"]["kind"] == "ai_product"
    assert health == [("custom_products", "healthy")]


def test_new_evidence_refreshes_the_active_event_of_an_approved_candidate(monkeypatch):
    now = datetime.now(timezone.utc)
    rows = [{"id": index, "source_key": "hacker_news", "canonical_url": "https://example.test/agent",
             "title": "A Rising Agent Framework", "content": {"points": 120}, "observed_at": now,
             "authority": "P1", "business_scopes": ["technology_ecosystem"]}
            for index in (101, 102, 103)]
    statements, rescored = [], []

    class Cursor:
        def execute(self, query, params=()):
            statements.append(query)
            self.query = query
        def fetchall(self): return rows
        def fetchone(self):
            if "INSERT INTO intelligence_candidates" in self.query:
                return None
            if "SELECT id,status,resolution_event_id" in self.query:
                return {"id": 9, "status": "approved", "resolution_event_id": 55}
            if "RETURNING event.entity_key,event.event_key,event.last_seen_at" in self.query:
                return {"entity_key": "url:abc", "event_key": "discovery:agent", "last_seen_at": now}
            raise AssertionError(self.query)
        def executemany(self, query, params): statements.append(query)
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()

    monkeypatch.setattr(discovery_service, "_collect_discovery_feeds", lambda: {})
    monkeypatch.setattr(discovery_service, "get_db", Connection)
    monkeypatch.setattr(discovery_service, "persist_event_hot_score",
                        lambda *args: rescored.append(args[1:]) or {"value": 33})

    result = discovery_service.discover_candidates()

    assert result["discovered"] == 1
    assert any("INSERT INTO intelligence_event_evidence" in query for query in statements)
    assert rescored == [(55, "url:abc", "discovery:agent", now)]


def test_discovery_reports_source_failures_without_dropping_candidates(monkeypatch):
    class Cursor:
        def execute(self, *_): pass
        def fetchall(self): return []
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()

    monkeypatch.setattr(discovery_service, "_collect_discovery_feeds",
                        lambda: {"github": 2, "broken_source_error": "request timed out"})
    monkeypatch.setattr(discovery_service, "get_db", Connection)

    assert discovery_service.discover_candidates() == {
        "status": "partial", "discovered": 0, "source_errors": {"broken_source": "request timed out"}}


def test_arxiv_feed_preserves_original_published_time_and_summary():
    payload = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>https://arxiv.org/abs/1234.5678</id>
    <title>  Agent   Systems </title><published>2026-10-21T10:00:00Z</published><summary>Original research abstract</summary></entry></feed>'''
    items = _parse_arxiv_feed(payload, "2026-10-22")
    assert items[0]["title"] == "Agent Systems"
    assert items[0]["published_at"] == "2026-10-21T10:00:00Z"
    assert items[0]["content"]["summary"] == "Original research abstract"
