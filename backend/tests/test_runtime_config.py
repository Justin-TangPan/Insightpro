from services import runtime_config_service


def test_apply_runtime_config(monkeypatch):
    monkeypatch.setattr(runtime_config_service.settings, "CHAT_API_URL", "https://old/v1")
    runtime_config_service.apply({"CHAT_API_URL": "https://new/v2", "UNKNOWN": "ignored"})
    assert runtime_config_service.settings.CHAT_API_URL == "https://new/v2"


def test_rejects_invalid_url():
    try:
        runtime_config_service.update({"CHAT_API_URL": "not-a-url"})
    except ValueError as error:
        assert "HTTP(S)" in str(error)
    else:
        raise AssertionError("invalid URL accepted")


def test_verify_uses_proposed_config(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def raise_for_status(self):
            return None

        def iter_lines(self):
            return iter(['data: {"choices":[{"delta":{"content":"OK"}}]}'])

        def json(self):
            return {"data": [{"id": "new-model"}]}

    def stream(method, url, **kwargs):
        captured.update(url=url, **kwargs)
        return Response()

    monkeypatch.setattr(runtime_config_service.httpx, "stream", stream)
    monkeypatch.setattr(runtime_config_service.httpx, "get", lambda *_, **__: Response())
    result = runtime_config_service.verify({"CHAT_API_URL": "https://new/v1/chat/completions", "CHAT_MODEL": "new-model", "CHAT_API_KEY": "new-key"})
    assert captured["url"] == "https://new/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer new-key"
    assert captured["json"]["model"] == "new-model"
    assert result["models"] == ["new-model"]


def test_load_ignores_incomplete_database_config(monkeypatch):
    class Cursor:
        def execute(self, *_):
            pass

        def fetchall(self):
            return [{"key": "CHAT_API_URL", "value": "https://partial/v1"}, {"key": "CHAT_MODEL", "value": "partial-model"}]

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(runtime_config_service, "get_db", Connection)
    monkeypatch.setattr(runtime_config_service.settings, "CHAT_API_URL", "https://environment/v1")
    runtime_config_service.load()
    assert runtime_config_service.settings.CHAT_API_URL == "https://environment/v1"
