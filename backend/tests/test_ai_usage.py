from datetime import timedelta

from services import ai_service, ai_usage_service


def test_summary_uses_shanghai_day_and_reports_token_coverage(monkeypatch):
    calls = []

    class Cursor:
        def execute(self, sql, params):
            calls.append((sql, params))

        def fetchone(self):
            return {"requests": 2, "input_tokens": 10, "output_tokens": 5, "token_requests": 1}

        def fetchall(self):
            return [{"model": "test-model", "requests": 2, "input_tokens": 10, "output_tokens": 5, "token_requests": 1}]

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(ai_usage_service, "get_db", Connection)
    result = ai_usage_service.summary()
    today_start = calls[0][1][0]
    assert today_start.hour == today_start.minute == 0
    assert today_start.tzinfo.key == "Asia/Shanghai"
    assert calls[1][1][0] == today_start - timedelta(days=6)
    assert result["today"]["token_requests"] == 1


def test_backend_completion_records_provider_usage(monkeypatch):
    calls = []
    from services import runtime_config_service
    monkeypatch.setattr(runtime_config_service, "load", lambda: None)

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"model": "provider-model", "choices": [{"message": {"content": "done"}}], "usage": {"prompt_tokens": 12, "completion_tokens": 3}}

    monkeypatch.setattr(ai_service.httpx, "post", lambda *_args, **_kwargs: Response())
    monkeypatch.setattr(ai_usage_service, "record", lambda *args: calls.append(args))
    assert ai_service.chat_complete(user_prompt="hello") == "done"
    assert calls == [(None, "provider-model", "backend", {"prompt_tokens": 12, "completion_tokens": 3})]
    assert ai_usage_service._has_usage({"prompt_tokens": 0, "completion_tokens": 0})
    assert not ai_usage_service._has_usage(None)


def test_backend_completion_refreshes_model_before_request(monkeypatch):
    from services import runtime_config_service

    calls = []
    monkeypatch.setattr(ai_service.settings, "CHAT_MODEL", "old-model")
    monkeypatch.setattr(runtime_config_service, "load", lambda: setattr(ai_service.settings, "CHAT_MODEL", "current-model"))

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "done"}}]}

    def post(_url, **kwargs):
        calls.append(kwargs["json"]["model"])
        return Response()

    monkeypatch.setattr(ai_service.httpx, "post", post)
    monkeypatch.setattr(ai_usage_service, "record", lambda *_: None)
    assert ai_service.chat_complete(user_prompt="hello") == "done"
    assert calls == ["current-model"]
