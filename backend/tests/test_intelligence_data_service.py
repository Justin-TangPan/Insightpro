from services.intelligence_data_service import parse_metric, store_ai_application, store_catalog_change, store_competitor_news, store_community_raw


def test_parse_metric_handles_github_counts():
    assert parse_metric("1,234") == 1234
    assert parse_metric("1.2k") == 1200
    assert parse_metric("2M") == 2_000_000
    assert parse_metric("—") is None


def test_disabled_github_source_does_not_scrape(monkeypatch):
    from crawlers import github_crawler

    monkeypatch.setattr(github_crawler, "source_enabled", lambda _: False)
    monkeypatch.setattr(github_crawler, "scrape_github_trending", lambda **_: (_ for _ in ()).throw(AssertionError("scraped")))

    assert github_crawler.refresh_and_store() == {"status": "skipped", "reason": "source_disabled"}


def test_ai_application_month_precision_does_not_become_a_fabricated_day():
    class Cursor:
        def __init__(self):
            self.calls = []
            self.results = iter(({"id": 10}, {"id": 20}))

        def execute(self, query, params=None):
            self.calls.append((query, params))

        def fetchone(self):
            return next(self.results)

    cursor = Cursor()
    store_ai_application(cursor, {
        "vendor": "OpenAI", "title": "Codex update", "kind": "update",
        "published": "2026-10", "url": "https://openai.com/index/codex/",
        "source_text": "Official update", "source_verified": True,
    })

    raw_params = cursor.calls[0][1]
    event_params = cursor.calls[2][1]
    assert raw_params[4] is None
    assert event_params[3] is None
    assert "INSERT INTO intelligence_event_evidence" in cursor.calls[3][0]


def test_competitor_news_writes_event_and_original_evidence():
    class Cursor:
        def __init__(self):
            self.calls = []
            self.results = iter(({"id": 11}, {"id": 12}))

        def execute(self, query, params=None):
            self.calls.append((query, params))

        def fetchone(self):
            return next(self.results)

    cursor = Cursor()
    store_competitor_news(cursor, {"vendor": "OpenAI", "title": "Product update", "url": "https://example.com/update",
                                   "summary": "Verified source summary", "published_date": "2026-10-20"})
    assert "competitor_news" in cursor.calls[0][0]
    assert "competitor_dynamics" in cursor.calls[2][0]
    assert cursor.calls[3][1] == (12, 11)


def test_solution_event_key_is_scoped_to_the_solution_entity():
    class Cursor:
        def __init__(self):
            self.calls = []

        def execute(self, query, params=None):
            self.calls.append((query, params))

        def fetchone(self):
            return {"id": 1}

    rows = [
        {"url": "https://example.com/solutions/a", "title": "Reference", "vendor": "Vendor",
         "category": "AI", "source_description": "Same content", "summary": "Same content",
         "change_summary": "Same change", "content_snapshot": {}, "is_active": True, "removed_at": None},
        {"url": "https://example.com/solutions/b", "title": "Reference", "vendor": "Vendor",
         "category": "AI", "source_description": "Same content", "summary": "Same content",
         "change_summary": "Same change", "content_snapshot": {}, "is_active": True, "removed_at": None},
    ]
    event_keys = []
    for row in rows:
        cursor = Cursor()
        store_catalog_change(cursor, "aliyun_solutions", row)
        event_keys.append(cursor.calls[2][1][0])

    assert event_keys[0] != event_keys[1]


def test_solution_baseline_uses_a_stable_catalog_event():
    class Cursor:
        def __init__(self): self.calls = []
        def execute(self, query, params=None): self.calls.append((query, params))
        def fetchone(self): return {"id": 1}

    row = {"url": "https://example.com/solutions/baseline", "title": "Baseline", "vendor": "Vendor",
           "category": "AI", "source_description": "Official solution", "summary": "Official summary",
           "change_summary": "", "content_snapshot": {}, "is_active": True, "is_baseline": True,
           "removed_at": None}
    keys = []
    for _ in range(2):
        cursor = Cursor()
        store_catalog_change(cursor, "aliyun_solutions", row)
        event = next(params for query, params in cursor.calls if "INSERT INTO intelligence_events" in query)
        keys.append(event[0])
        assert event[2] == "solution_catalog_entry"

    assert keys[0] == keys[1]


def test_community_items_become_cross_source_events_with_evidence(monkeypatch):
    from services import intelligence_data_service

    class Cursor:
        def __init__(self):
            self.calls = []
            self.results = iter(({"id": 10}, {"id": 20}, {"id": 11}, {"id": 20}))

        def execute(self, query, params=None):
            self.calls.append((query, params))

        def fetchone(self):
            return next(self.results)

    class Connection:
        def __init__(self):
            self.cursor_value = Cursor()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def cursor(self):
            return self.cursor_value

    conn = Connection()
    monkeypatch.setattr(intelligence_data_service, "get_db", lambda: conn)
    items = [
        {"source": source, "title": "New AI agent", "summary": "Trending", "url": f"https://{host}/topic",
         "observed_at": "2026-10-23T08:00:00+08:00"}
        for source, host in (("知乎", "zhihu.com"), ("CSDN", "csdn.net"))
    ]

    assert store_community_raw(items) == 2
    event_writes = [params for query, params in conn.cursor_value.calls if "INSERT INTO intelligence_events" in query]
    evidence_writes = [params for query, params in conn.cursor_value.calls if "INSERT INTO intelligence_event_evidence" in query]
    assert event_writes[0][0] == event_writes[1][0]
    assert evidence_writes == [(20, 10), (20, 11)]
    raw_write = next(params for query, params in conn.cursor_value.calls if "INSERT INTO intelligence_raw_items" in query)
    assert raw_write[5] == "2026-10-23T08:00:00+08:00"
    assert raw_write[-1] is None
