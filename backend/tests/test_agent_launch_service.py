from services import agent_launch_service as service


def test_official_launches_survive_unavailable_source(monkeypatch):
    class Forbidden:
        def raise_for_status(self):
            raise service.requests.HTTPError("403")

    monkeypatch.setattr(service.requests, "get", lambda *args, **kwargs: Forbidden())
    items = service.discover()
    assert {item["title"] for item in items[:2]} == {"Muse", "dots"}
    assert all(item["url"] not in service.EXCLUDED_APPLICATION_URLS for item in items)
    dot = service._source(items[1])
    assert dot and "always-on personal agents" in dot["source_text"]
    assert service._source({"url": "https://untrusted.example/agent", "title": "Agent"}) is None


def test_analysis_uses_official_text(monkeypatch):
    monkeypatch.setattr(service.settings, "CHAT_API_KEY", "test")
    captured = {}
    stored = {}

    class Cursor:
        def execute(self, sql, params):
            self.sql = sql
            self.params = params

        def fetchone(self):
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
    item = {"vendor": "Meta", "title": "Muse", "published": "2026-09-08",
            "url": service.SEEDS[0][3], "source_text": "Official launch evidence"}
    assert service.analyze(item)["analysis"] == "能力。机会。待验证。"
    assert "Official launch evidence" in captured["user_prompt"]
    captured.clear()
    assert service.analyze(item)["analysis_id"] == 1
    assert captured == {}


def test_curated_app_is_kept_when_publisher_uses_generic_heading(monkeypatch):
    class Page:
        url = service.SEEDS[0][3]
        text = "<html><head><title>Community</title></head><body><main>Muse is a personal agent that performs tasks across apps.</main></body></html>"

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
    rows = [
        {"id": 1, "vendor": "Kimi", "name": "Kimi Agent for reports", "url": "https://www.kimi.com/en/agent", "kind": "product", "published_at": "", "summary": "{\"summary\":", "capability": "", "opportunity": "", "limitation": "", "source_text": "English source"},
        {"id": 2, "vendor": "Kimi", "name": "Kimi Agent", "url": "https://www.kimi.com/agent", "kind": "product", "published_at": "", "summary": "可生成文档和报告。", "capability": "生成报告", "opportunity": "", "limitation": "", "source_text": "English source"},
    ]

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
