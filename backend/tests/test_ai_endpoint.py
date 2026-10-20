from services import ai_service


def test_chat_endpoint_accepts_base_or_full_url():
    base = "https://api.modelarts-maas.com/v2"
    full = f"{base}/chat/completions"
    assert ai_service.chat_completions_url(base) == full
    assert ai_service.chat_completions_url(f"{base}/") == full
    assert ai_service.chat_completions_url(full) == full
    assert ai_service.api_base_url(full) == base


def test_model_probe_reads_openai_compatible_list(monkeypatch):
    monkeypatch.setattr(ai_service, "_models", ())
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"id": "model-a"}, {"id": "model-b"}, {"id": "model-a"}]}

    monkeypatch.setattr(ai_service.httpx, "get", lambda *args, **kwargs: Response())
    assert ai_service.probe_models() == ("model-a", "model-b")
    assert "model-a" in ai_service.available_model_ids()
