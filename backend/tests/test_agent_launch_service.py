from services import agent_launch_service as service
import pytest


def test_official_launches_survive_unavailable_source(monkeypatch):
    class Forbidden:
        def raise_for_status(self):
            raise service.requests.HTTPError("403")

    monkeypatch.setattr(service.requests, "get", lambda *args, **kwargs: Forbidden())
    items = service.discover()
    assert {"Muse", "dots"}.issubset({item["title"] for item in items})
    assert all(item["url"] not in service.EXCLUDED_APPLICATION_URLS for item in items)
    dot = service._source(next(item for item in items if item["title"] == "dots"))
    assert dot and "always-on personal agents" in dot["source_text"] and dot["source_verified"] is False
    assert service._source({"url": "https://untrusted.example/agent", "title": "Agent"}) is None


def test_official_release_notes_create_dated_updates(monkeypatch):
    class Page:
        text = "<h2>October 15, 2026</h2><p>Codex can now complete tasks across several tools and review the resulting changes before applying them.</p>"
        content = text.encode()
        def raise_for_status(self): pass

    monkeypatch.setattr(service.requests, "get", lambda *args, **kwargs: Page())
    items = service._feed_items(("OpenAI", "Codex", "https://developers.openai.com/codex/changelog", "notes"))
    assert items == []  # Codex's real page uses dated list entries, not date headings.
    items = service._feed_items(("Kimi", "Kimi Work", "https://www.kimi.com/en/help/kimi-work/release-notes", "notes"))
    assert len(items) == 1
    assert items[0]["published"] == "2026-10-15"
    assert service._source(items[0]) == {**items[0], "source_verified": True}


def test_deepseek_official_github_repository_becomes_dated_application_update(monkeypatch):
    class Response:
        def __init__(self, body=None, text=""):
            self.body, self.text = body, text

        def raise_for_status(self):
            pass

        def json(self):
            return self.body

    def get(url, **_):
        if url == "https://api.github.com/repos/deepseek-ai/DeepInfer":
            return Response({"full_name": "deepseek-ai/DeepInfer", "html_url": "https://github.com/deepseek-ai/DeepInfer",
                             "pushed_at": "2026-10-20T11:03:36Z", "default_branch": "main", "description": "Inference framework",
                             "stargazers_count": 100, "forks_count": 12, "language": "Python"})
        return Response(text="# DeepInfer\nOffline inference framework")

    monkeypatch.setattr(service.requests, "get", get)
    items = service._github_repository_items()
    assert len(items) == 1
    assert items[0]["vendor"] == "DeepSeek"
    assert items[0]["title"] == "DeepInfer 推理框架动态"
    assert items[0]["published"] == "2026-10-20"
    assert items[0]["kind"] == "update" and items[0]["feed_verified"]
    assert "Offline inference framework" in items[0]["source_text"]
    assert service.FEED_HEALTH[items[0]["url"]] == "matched"
    assert service._source(items[0]) == {**items[0], "source_verified": True}
    assert service._source({**items[0], "url": "https://github.com/other/DeepInfer"}) is None


def test_openai_rss_keeps_product_news_and_official_excerpt(monkeypatch):
    class Page:
        content = b"""<rss><channel>
          <item><title>ChatGPT adds a new workspace feature</title><link>https://openai.com/index/chatgpt-workspace/</link><category>Product</category><pubDate>Mon, 20 Oct 2025 00:00:00 GMT</pubDate><description>Official update text.</description></item>
          <item><title>Customer grows with Codex</title><link>https://openai.com/index/customer-story/</link><pubDate>Mon, 20 Oct 2025 00:00:00 GMT</pubDate><description>Case study.</description></item>
          <item><title>Kiro model update</title><link>https://openai.com/index/kiro-model/</link><category>Product</category><pubDate>Mon, 20 Oct 2025 00:00:00 GMT</pubDate><description>Other product.</description></item>
        </channel></rss>"""
        def raise_for_status(self): pass

    monkeypatch.setattr(service.requests, "get", lambda *args, **kwargs: Page())
    items = service._feed_items(("OpenAI", "", "https://openai.com/news/rss.xml", "rss"))
    assert len(items) == 1
    assert items[0]["published"] == "2025-10-20"
    assert service._source(items[0])["source_text"] == "Official update text."


def test_monthly_notes_keep_month_precision(monkeypatch):
    class Page:
        content = "<h2>2025 年 08 月</h2><h3>功能更新</h3><p>扣子新增应用创建和协作功能，供团队发布与管理项目。</p><h2>2025 年 07 月</h2><p>旧版更新内容。</p>".encode()
        def raise_for_status(self): pass

    monkeypatch.setattr(service.requests, "get", lambda *args, **kwargs: Page())
    items = service._feed_items(("Volcengine", "扣子", "https://docs.coze.cn/recent-updates", "notes"))
    assert items[0]["published"] == "2025-08"
    assert "旧版更新" not in items[0]["source_text"]


def test_publication_timestamp_uses_shanghai_day():
    assert service._date("2025-10-19T20:30:00Z") == "2025-10-20"


def test_official_source_page_sets_verified_evidence_and_seed_date_is_not_trusted(monkeypatch):
    class Page:
        url = "https://openai.com/index/introducing-dots/"
        content = b'<html><head><title>Introducing dots</title><meta name="description" content="Personal agent"></head><body><article>' + b"Official product details. " * 20 + b"</article></body></html>"
        def raise_for_status(self): pass

    monkeypatch.setattr(service.requests, "get", lambda *args, **kwargs: Page())
    item = {"vendor": "OpenAI", "title": "dots", "published": "2026-09-29", "discovery_seed": True,
            "url": "https://openai.com/index/introducing-dots/", "kind": "launch"}
    verified = service._source(item)
    assert verified["source_verified"] is True
    assert verified["published"] == ""


def test_disabled_ai_application_source_skips_all_collection(monkeypatch):
    from services import source_registry_service
    monkeypatch.setattr(source_registry_service, "source_enabled", lambda _: False)
    monkeypatch.setattr(service, "discover", lambda: (_ for _ in ()).throw(AssertionError("discovery ran")))

    assert service._ingest() == 0


def test_analysis_uses_official_text(monkeypatch):
    monkeypatch.setattr(service.settings, "CHAT_API_KEY", "test")
    captured = {}
    stored = {}
    application = {}
    upsert_sql = []

    class Cursor:
        def execute(self, sql, params):
            self.sql = sql
            self.params = params
            if "INSERT INTO vendor_ai_applications" in sql:
                upsert_sql.append(sql)
                prior = application.get((params[0], params[2]), {})
                application[(params[0], params[2])] = {
                    "source_fingerprint": params[-3],
                    "analyzed_source_fingerprint": params[-1],
                    "analysis_status": params[-2],
                    "source_updated_at": prior.get("source_updated_at"),
                    "analyzed_at": object() if params[13] else prior.get("analyzed_at"),
                }

        def fetchone(self):
            if self.sql.startswith("SELECT source_fingerprint"):
                return application.get(self.params)
            if self.sql.startswith("SELECT id"):
                return stored.get(self.params[0])
            if self.sql.startswith("INSERT"):
                stored[self.params[0]] = {"id": 1, "analysis": self.params[1]}
                return {"id": 1}
            return None

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(service, "get_db", Connection)

    def complete(**kwargs):
        captured.update(kwargs)
        return "能力。机会。待验证。"

    monkeypatch.setattr(service.ai_service, "chat_complete", complete)
    item = {"vendor": "Meta", "title": "Muse", "kind": "launch", "published": "2026-09-08",
            "url": service.SEEDS[0][3], "source_text": "Official launch evidence"}
    application[(item["vendor"], item["url"])] = {
        "vendor": item["vendor"], "name": item["title"], "title": item["title"], "kind": item["kind"],
        "published": item["published"], "source_text": item["source_text"],
        "source_fingerprint": service._source_fingerprint(item),
        "analyzed_source_fingerprint": None,
        "analysis_status": "pending",
        "source_updated_at": None,
        "analyzed_at": None,
    }
    assert service.analyze(item)["analysis"] == "能力。机会。待验证。"
    assert "Official launch evidence" in captured["user_prompt"]
    assert "vendor_ai_applications.source_fingerprint = EXCLUDED.source_fingerprint" in upsert_sql[0]
    analyzed_at = application[(item["vendor"], item["url"])]["analyzed_at"]
    captured.clear()
    assert service.analyze(item)["analysis_id"] == 1
    assert captured == {}
    assert application[(item["vendor"], item["url"])]["analyzed_at"] is analyzed_at


def test_analysis_drops_result_if_source_changes_during_ai_call(monkeypatch):
    item = {"vendor": "Meta", "title": "Muse", "published": "2026-09-08",
            "url": service.SEEDS[0][3], "kind": "launch", "source_text": "Old official source"}
    expected = service._source_fingerprint(item)
    source_reads = 0
    statements = []

    class Cursor:
        def execute(self, sql, params=()):
            nonlocal source_reads
            statements.append(sql)
            self.sql = sql
            if sql.startswith("SELECT source_fingerprint"):
                source_reads += 1
                self.row = ({"source_fingerprint": expected, "analyzed_source_fingerprint": None,
                             "analysis_status": "pending", "source_updated_at": None, "analyzed_at": None}
                            if source_reads == 1 else {**item, "source_text": "Changed source", "source_fingerprint": "new-source-fingerprint"})
            elif sql.startswith("SELECT id, analysis"):
                self.row = None
        def fetchone(self): return self.row

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return Cursor()

    monkeypatch.setattr(service, "get_db", Connection)
    monkeypatch.setattr(service.settings, "CHAT_API_KEY", "test")
    monkeypatch.setattr(service, "_analyze_with_retry", lambda *_args, **_kwargs: ('{"summary":"能力描述。","capability":"可处理任务。","opportunity":"适用场景。","limitation":"仍需验证。"}', None, 1))

    result = service.analyze(item)

    assert result["analysis"] is None
    assert result["analysis_stale"] is True
    assert not any("INSERT INTO intelligence_analysis" in sql for sql in statements)
    assert not any("INSERT INTO vendor_ai_applications" in sql for sql in statements)


@pytest.mark.parametrize("stored_fingerprint", [None, "legacy-fingerprint"])
def test_analysis_allows_legacy_fingerprint_only_when_locked_snapshot_matches(monkeypatch, stored_fingerprint):
    item = {"vendor": "Meta", "title": "Muse", "published": "2026-09-08",
            "url": service.SEEDS[0][3], "kind": "launch", "source_text": "Stored official source"}
    fingerprint = service._source_fingerprint(item)
    reads = 0
    statements = []

    class Cursor:
        def execute(self, sql, params=()):
            nonlocal reads
            statements.append(sql)
            self.sql = sql
            if sql.startswith("SELECT source_fingerprint"):
                reads += 1
                self.row = ({"source_fingerprint": stored_fingerprint, "analyzed_source_fingerprint": None,
                             "analysis_status": "pending", "source_updated_at": None, "analyzed_at": None}
                            if reads == 1 else {**item, "source_fingerprint": stored_fingerprint})
            elif sql.startswith("SELECT id, analysis"):
                self.row = None
            elif sql.startswith("INSERT INTO intelligence_analysis"):
                self.row = {"id": 9}
        def fetchone(self): return self.row

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return Cursor()

    monkeypatch.setattr(service, "get_db", Connection)
    monkeypatch.setattr(service.settings, "CHAT_API_KEY", "test")
    monkeypatch.setattr(service, "_analyze_with_retry", lambda *_args, **_kwargs: ('{"summary":"能力描述。","capability":"可处理任务。","opportunity":"适用场景。","limitation":"仍需验证。"}', None, 1))
    result = service.analyze(item)
    assert result["analysis"]
    assert any("INSERT INTO intelligence_analysis" in sql for sql in statements)
    assert any("INSERT INTO vendor_ai_applications" in sql for sql in statements)
    upsert = next(sql for sql in statements if "INSERT INTO vendor_ai_applications" in sql)
    assert "source_fingerprint = EXCLUDED.source_fingerprint" in upsert
    assert "vendor_ai_applications.source_text IS NOT DISTINCT FROM EXCLUDED.source_text" in upsert


def test_stored_pending_analysis_does_not_ingest(monkeypatch):
    row = {"vendor": "Meta", "title": "Muse", "published": "", "url": "https://example.test/muse",
           "kind": "launch", "source_text": "stored snapshot"}
    analyzed = []
    monkeypatch.setattr(service, "_pending_rows", lambda _: [row])
    monkeypatch.setattr(service, "_ingest", lambda: (_ for _ in ()).throw(AssertionError("ingest called")))
    monkeypatch.setattr(service, "analyze", lambda item: analyzed.append(item))
    monkeypatch.setattr(service, "_read_structured", lambda: [])
    monkeypatch.setattr(service.time, "sleep", lambda _: None)
    assert service.analyze_stored_pending() == []
    assert analyzed == [row]


def test_analysis_staleness_tracks_source_fingerprint_and_timestamps():
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    current = {"analysis_status": "done", "analyzed_at": now,
               "source_updated_at": now - timedelta(seconds=1),
               "source_fingerprint": "same", "analyzed_source_fingerprint": "same"}
    assert service._analysis_is_stale(current) is False
    assert service._analysis_is_stale({**current, "source_fingerprint": "changed"}) is True
    assert service._analysis_is_stale({**current, "source_updated_at": now + timedelta(seconds=1)}) is True
    assert service._analysis_is_stale({**current, "analyzed_at": None}) is True
    assert service._analysis_is_stale(None) is True


def test_latest_analyzes_each_pending_snapshot_once(monkeypatch):
    rows = [
        {"vendor": "OpenAI", "title": "A", "url": "https://example.test/a", "kind": "launch", "published": "", "source_text": "evidence A"},
        {"vendor": "OpenAI", "title": "B", "url": "https://example.test/b", "kind": "launch", "published": "", "source_text": "evidence B"},
    ]
    analyzed = []
    monkeypatch.setattr(service, "_ingest", lambda: 0)
    monkeypatch.setattr(service, "_pending_rows", lambda _limit: rows)
    monkeypatch.setattr(service, "analyze", lambda item: analyzed.append(item["url"]))
    monkeypatch.setattr(service.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(service, "_read_structured", lambda: [])

    assert service.latest() == []
    assert analyzed == [row["url"] for row in rows]


def test_source_fingerprint_is_stable_and_uses_persisted_source_snapshot():
    item = {"vendor": "Meta", "title": "Muse", "kind": "launch", "published": "",
            "source_text": "evidence" * 400}
    assert service._source_fingerprint(item) == service._source_fingerprint(dict(item))
    assert service._source_fingerprint({**item, "source_text": item["source_text"][:2000] + "ignored"}) == service._source_fingerprint(item)
    assert service._source_fingerprint({**item, "published": "2026-09-08"}) != service._source_fingerprint(item)


def test_curated_app_is_kept_when_publisher_uses_generic_heading(monkeypatch):
    class Page:
        url = service.SEEDS[0][3]
        text = "<html><head><title>Community</title></head><body><main>Muse is a personal agent that performs tasks across apps.</main></body></html>"
        content = text.encode()

        def raise_for_status(self):
            pass

    monkeypatch.setattr(service.requests, "get", lambda *args, **kwargs: Page())
    item = {"vendor": "Meta", "title": "Muse", "published": "2026-09-08", "url": Page.url, "kind": "launch"}
    assert service._source(item)["title"] == "Muse"


def test_truncated_structured_reply_is_retried(monkeypatch):
    replies = iter(['{"summary":"中文摘要", "capability":', '{"summary":"中文摘要","capability":"可执行任务","opportunity":"","limitation":""}'])
    monkeypatch.setattr(service.ai_service, "chat_complete", lambda **_: next(replies))
    monkeypatch.setattr(service.time, "sleep", lambda _: None)
    result = service._analyze_with_retry({"vendor": "测试", "title": "产品", "url": "https://example.com", "source_text": "官方说明"})
    assert service._parse_structured(result)["capability"] == "可执行任务"
    assert service._parse_structured('{"summary":"中文摘要", "capability":') is None


def test_read_hides_raw_json_and_duplicate_language_page(monkeypatch):
    import datetime
    fingerprint = service._source_fingerprint({"vendor": "Kimi", "title": "Kimi Agent", "kind": "product", "published": "", "source_text": "English source"})
    rows = [
        {"id": 1, "vendor": "Kimi", "name": "Kimi Agent for reports", "url": "https://www.kimi.com/en/agent", "kind": "product", "published_at": "", "summary": "{\"summary\":", "capability": "", "opportunity": "", "limitation": "", "source_text": "English source", "analysis_status": "done", "analyzed_at": "2026-10-23T00:00:00+00:00", "source_updated_at": "2026-10-23T00:00:00+00:00", "source_fingerprint": "a", "analyzed_source_fingerprint": "a"},
        {"id": 2, "vendor": "Kimi", "name": "Kimi Agent", "url": "https://www.kimi.com/agent", "kind": "product", "published_at": "", "summary": "可生成文档和报告。", "capability": "生成报告", "opportunity": "", "limitation": "", "source_text": "English source", "analysis_status": "done", "analyzed_at": "2026-10-23T00:00:00+00:00", "source_updated_at": "2026-10-23T00:00:00+00:00", "source_fingerprint": "a", "analyzed_source_fingerprint": "a"},
    ]
    for row in rows:
        row.update(analysis_status="done", analyzed_at=datetime.datetime(2026, 10, 23), source_updated_at=datetime.datetime(2026, 10, 23), source_fingerprint=fingerprint, analyzed_source_fingerprint=fingerprint)

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return self
        def execute(self, *_): pass
        def fetchall(self): return rows

    monkeypatch.setattr(service, "get_db", Connection)
    items = service._read_structured()
    assert len(items) == 1
    assert items[0]["summary"] == "可生成文档和报告。"
    assert items[0]["analysis"] == "生成报告"


def test_read_hides_analysis_when_source_fingerprint_changed(monkeypatch):
    row = {"id": 3, "vendor": "Kimi", "name": "Kimi Agent", "url": "https://www.kimi.com/agent", "kind": "product", "published_at": "", "summary": "旧摘要。", "capability": "旧能力", "opportunity": "旧机会", "limitation": "旧限制", "source_text": "updated source", "analysis_status": "done", "analyzed_at": "2026-10-22", "source_updated_at": "2026-10-23", "source_fingerprint": "new", "analyzed_source_fingerprint": "old"}
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return self
        def execute(self, *_): pass
        def fetchall(self): return [row]
    monkeypatch.setattr(service, "get_db", Connection)
    item = service._read_structured()[0]
    assert item["analysis_stale"] is True
    assert item["analysis_status"] == "stale"
    assert item["summary"] == item["analysis"] == ""
