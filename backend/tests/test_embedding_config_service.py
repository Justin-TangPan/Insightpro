from services import embedding_config_service as service


def test_verify_sends_embedding_request_and_checks_storage_dimensions(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [{"embedding": [0.1] * 1024}]}

    def post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return Response()

    monkeypatch.setattr(service.httpx, "post", post)
    result = service.verify({"EMBEDDING_API_URL": "https://embed.example/v1/embeddings",
                             "EMBEDDING_MODEL": "bge-m3", "EMBEDDING_API_KEY": "secret"})
    assert captured["url"] == "https://embed.example/v1/embeddings"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["json"]["model"] == "bge-m3"
    assert result == {"dimensions": 1024}


def test_verify_rejects_a_vector_dimension_incompatible_with_pgvector(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [{"embedding": [0.1] * 768}]}

    monkeypatch.setattr(service.httpx, "post", lambda *_, **__: Response())
    try:
        service.verify({"EMBEDDING_API_URL": "https://embed.example/v1/embeddings",
                        "EMBEDDING_MODEL": "small-model", "EMBEDDING_API_KEY": "secret"})
    except ValueError as error:
        assert "1024" in str(error)
    else:
        raise AssertionError("dimension mismatch must fail before saving")


def test_update_persists_secrets_without_returning_them(monkeypatch):
    saved = {}

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return self
        def executemany(self, _sql, rows): saved.update(rows)

    monkeypatch.setattr(service, "get_db", Connection)
    monkeypatch.setattr(service.settings, "EMBEDDING_API_URL", "")
    monkeypatch.setattr(service.settings, "EMBEDDING_API_KEY", "")
    monkeypatch.setattr(service.settings, "EMBEDDING_MODEL", "bge-m3")
    result = service.update({"EMBEDDING_API_URL": "https://embed.example/v1/embeddings",
                             "EMBEDDING_API_KEY": "secret"})
    assert saved["EMBEDDING_API_KEY"] == "secret"
    assert result == {"EMBEDDING_API_URL": "https://embed.example/v1/embeddings", "EMBEDDING_MODEL": "bge-m3"}
    assert "EMBEDDING_API_KEY" not in result


def test_load_ignores_incomplete_database_configuration(monkeypatch):
    class Cursor:
        def execute(self, *_): pass
        def fetchall(self): return [{"key": "EMBEDDING_MODEL", "value": "partial"}]

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return Cursor()

    monkeypatch.setattr(service, "get_db", Connection)
    monkeypatch.setattr(service.settings, "EMBEDDING_MODEL", "environment-model")
    service.load()
    assert service.settings.EMBEDDING_MODEL == "environment-model"


def test_update_refuses_model_change_when_knowledge_vectors_exist(monkeypatch):
    class Cursor:
        def execute(self, *_): pass
        def fetchone(self): return {"has_chunks": True}

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return Cursor()

    monkeypatch.setattr(service, "get_db", Connection)
    monkeypatch.setattr(service.settings, "EMBEDDING_API_URL", "https://embed.example/v1/embeddings")
    monkeypatch.setattr(service.settings, "EMBEDDING_API_KEY", "secret")
    monkeypatch.setattr(service.settings, "EMBEDDING_MODEL", "old-model")
    try:
        service.update({"EMBEDDING_MODEL": "new-model"})
    except ValueError as error:
        assert "不能在线更换模型" in str(error)
    else:
        raise AssertionError("model change must not invalidate existing vectors")
