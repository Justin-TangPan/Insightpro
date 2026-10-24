import sys, os
import pytest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fastapi.testclient import TestClient
from settings import settings
from main import app
from settings import _required_env, settings

client = TestClient(app)


class TestAPIEndpoints:
    def test_required_environment_config_has_no_fallback(self, monkeypatch):
        monkeypatch.delenv("HERMES_PUBLIC_URL", raising=False)
        with pytest.raises(RuntimeError, match="HERMES_PUBLIC_URL"):
            _required_env("HERMES_PUBLIC_URL")

    def test_root(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "message" in resp.json()
        assert resp.json()["version"] == settings.APP_VERSION

    def test_configured_frontend_origin_is_allowed(self):
        origin = settings.CORS_ORIGINS[0]
        resp = client.get(
            "/api/github-trending/business-eval",
            headers={"Origin": origin},
        )
        assert resp.status_code == 200
        assert resp.headers["access-control-allow-origin"] == origin

    @pytest.mark.parametrize("method,path", [
        ("POST", "/api/github-trending/refresh"),
        ("POST", "/api/github-trending/business-eval/refresh"),
        ("POST", "/api/solutions/aliyun/refresh"),
        ("POST", "/api/solutions/catalog/refresh"),
        ("POST", "/api/crawl/trigger"),
        ("DELETE", "/api/reports/missing"),
        ("GET", "/api/email/subscribers"),
        ("POST", "/api/email/subscribe"),
        ("PUT", "/api/email/subscribers/1"),
        ("POST", "/api/email/subscribers/1/send"),
        ("GET", "/api/email/preview"),
        ("GET", "/api/v2/admin/email-deliveries"),
        ("GET", "/api/v2/admin/coverage/recall-benchmark"),
        ("POST", "/api/v2/admin/coverage/recall-benchmark"),
        ("GET", "/api/analytics"),
        ("GET", "/api/workbench/summary"),
        ("GET", "/api/workbench/requirements"),
        ("POST", "/api/workbench/requirements"),
        ("GET", "/api/workbench/solutions"),
        ("POST", "/api/workbench/solutions"),
        ("POST", "/api/auth/agent/ticket"),
        ("POST", "/api/auth/agent/revoke"),
        ("POST", "/api/agent/chat/stream"),
        ("GET", "/api/agent/artifacts/missing/download"),
    ])
    def test_sensitive_endpoints_require_auth(self, method, path):
        response = client.request(method, path)
        assert response.status_code == 401

    @pytest.mark.parametrize("path", [
        "/api/industry-news",
        "/api/policy/list",
        "/api/bidding/list",
        "/api/demand/signals",
    ])
    def test_removed_insight_endpoints_are_gone(self, path):
        assert client.get(path).status_code == 404

    @pytest.mark.parametrize("source_key", ["aliyun_solutions", "huawei_solutions", "ai_app_official"])
    def test_v2_registry_controls_newly_connected_collectors(self, source_key, monkeypatch):
        from routers.auth import require_admin
        from routers import intelligence_v2
        user_id = uuid4()
        monkeypatch.setitem(client.app.dependency_overrides, require_admin, lambda: SimpleNamespace(id=user_id))
        monkeypatch.setattr(intelligence_v2, "set_source_enabled",
                            lambda key, enabled, actor: {"source_key": key, "enabled": enabled, "actor": actor})

        response = client.patch(f"/api/v2/admin/sources/{source_key}/enabled", json={"enabled": False})

        assert response.status_code == 200
        assert response.json() == {"source_key": source_key, "enabled": False, "actor": str(user_id)}

    def test_v2_admin_can_list_non_active_events(self, monkeypatch):
        from routers.auth import require_admin
        from routers import intelligence_v2
        user_id = uuid4()
        requested = []
        monkeypatch.setitem(client.app.dependency_overrides, require_admin, lambda: SimpleNamespace(id=user_id))
        monkeypatch.setattr(intelligence_v2, "list_events",
                            lambda *args: requested.append(args) or {"items": [], "limit": args[0], "offset": args[1]})

        response = client.get("/api/v2/admin/events?status=ignored")

        assert response.status_code == 200
        assert requested == [(50, 0, None, "ignored")]
        client.app.dependency_overrides.pop(require_admin, None)

    def test_v2_repository_entity_detail_uses_shared_entity_service(self, monkeypatch):
        from routers import intelligence_v2
        requested = []
        monkeypatch.setattr(intelligence_v2, "get_entity_detail",
                            lambda key: requested.append(key) or {"entity": {"entity_key": key}, "events": [], "evidence": [], "metrics": [], "trends": {}})

        response = client.get("/api/v2/entities/github%3Aorg%2Frepo")

        assert response.status_code == 200
        assert requested == ["github:org/repo"]
        assert response.json()["entity"]["entity_key"] == "github:org/repo"

    def test_v2_repository_trending_reads_service(self, monkeypatch):
        from routers import intelligence_v2
        requested = []
        monkeypatch.setattr(intelligence_v2, "list_trending_repositories", lambda *args: requested.append(args) or {
            "items": [], "source": "event_store", "count": 0, "date": "2026-10-23"})

        response = client.get("/api/v2/repositories/trending?period=weekly&date=2026-10-23")

        assert response.status_code == 200
        assert requested == [("weekly", date(2026, 10, 23))]

    def test_v2_recall_benchmark_requires_valid_https_reference_and_admin(self, monkeypatch):
        from routers.auth import require_admin
        from routers import intelligence_v2
        user_id = uuid4()
        monkeypatch.setitem(client.app.dependency_overrides, require_admin, lambda: SimpleNamespace(id=user_id))
        recorded = []
        monkeypatch.setattr(intelligence_v2, "record_reference", lambda item, actor:
                            recorded.append((item, actor)) or {"id": 1, **item})
        body = {"title": "Independent AI project signal", "canonical_url": "https://example.com/project",
                "reference_source": "Maintained benchmark", "reference_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
                "is_relevant": True, "label_reason": "Included by independent reviewer"}

        valid = client.post("/api/v2/admin/coverage/recall-benchmark", json=body)
        invalid = client.post("/api/v2/admin/coverage/recall-benchmark",
                              json={**body, "canonical_url": "http://example.com/project"})

        assert valid.status_code == 201
        assert recorded[0][1] == str(user_id)
        assert invalid.status_code == 422
        client.app.dependency_overrides.pop(require_admin, None)

    def test_business_evaluation_read_uses_v2_without_live_crawl(self, monkeypatch):
        from routers import hotspots
        monkeypatch.setattr(hotspots, "list_repository_business_evaluations", lambda *args: {
            "source": "event_store", "date": "2026-10-23", "items": [{
                "repo_name": "org/repo", "repo_url": "https://github.com/org/repo", "summary": "Evidence based",
                "d1": 8, "d2": 8, "d3": 8, "d4": 8, "recommendation": "Validate deployment",
                "reasoning": "Observed description", "evaluation_mode": "ai"}]})
        monkeypatch.setattr(hotspots, "scrape_github_trending", lambda **_: (_ for _ in ()).throw(AssertionError("GET scraped")))

        response = client.get("/api/github-trending/business-eval?locale=en")

        assert response.status_code == 200
        assert response.json()["source"] == "event_store"
        assert response.json()["items"][0]["repo_name"] == "org/repo"

    def test_v2_admin_can_add_supported_source_disabled(self, monkeypatch):
        from routers.auth import require_admin
        from routers import intelligence_v2
        user_id = uuid4()
        requested = []
        monkeypatch.setitem(client.app.dependency_overrides, require_admin, lambda: SimpleNamespace(id=user_id))
        monkeypatch.setattr(intelligence_v2, "create_source", lambda source, actor:
                            requested.append((source, actor)) or {"source_key": source["source_key"], "enabled": False})

        response = client.post("/api/v2/admin/sources", json={
            "source_key": "custom_hn", "name": "Custom HN", "adapter": "hacker_news_api",
            "base_url": "https://example.test/v0/topstories.json", "business_scopes": ["technology_ecosystem"],
        })

        assert response.status_code == 201
        assert requested[0][0]["adapter"] == "hacker_news_api"
        assert requested[0][1] == str(user_id)
        assert response.json()["enabled"] is False
        client.app.dependency_overrides.pop(require_admin, None)

    def test_v2_source_schedule_updates_the_running_scheduler(self, monkeypatch):
        from routers.auth import require_admin
        from routers import intelligence_v2
        user_id = uuid4()
        calls = []
        class Scheduler:
            def get_job(self, key): return object()
            def reschedule_job(self, key, trigger): calls.append((key, trigger))

        monkeypatch.setitem(client.app.dependency_overrides, require_admin, lambda: SimpleNamespace(id=user_id))
        monkeypatch.setattr(intelligence_v2, "update_source_schedule",
                            lambda key, cron, actor: {"task_key": "github_daily", "cron": cron, "source_keys": [key]})
        monkeypatch.setattr(intelligence_v2, "set_task_schedule", lambda key, cron: calls.append((key, cron)))
        monkeypatch.setattr(client.app.state, "scheduler", Scheduler(), raising=False)

        response = client.patch("/api/v2/admin/sources/github_trending/schedule", json={"cron": "15 7 * * *"})

        assert response.status_code == 200
        assert response.json()["cron"] == "15 7 * * *"
        assert calls[0] == ("github_daily", "15 7 * * *")
        assert calls[1][0] == "github_daily"

    def test_v2_source_connection_test_requires_admin(self, monkeypatch):
        from routers.auth import require_admin
        from routers import intelligence_v2
        monkeypatch.setitem(client.app.dependency_overrides, require_admin,
                            lambda: SimpleNamespace(id=uuid4()))
        monkeypatch.setattr(intelligence_v2, "test_source_connection",
                            lambda key, actor: {"source_key": key, "ok": True})

        response = client.post("/api/v2/admin/sources/hacker_news/test")

        assert response.status_code == 200
        assert response.json() == {"source_key": "hacker_news", "ok": True}
        client.app.dependency_overrides.pop(require_admin, None)

    def test_v2_coverage_recognizes_github_search_adapter(self, monkeypatch):
        from routers.auth import require_admin
        from routers import intelligence_v2

        class Cursor:
            query = ""
            def execute(self, query, *_): self.query = query
            def fetchall(self):
                if "FROM intelligence_sources" in self.query:
                    return [{"source_key": "github_search", "name": "GitHub Search", "adapter": "github_search_api",
                             "authority": "P1", "enabled": True, "priority": 35, "items_24h": 0,
                             "health_status": "unknown", "last_success_at": None, "last_error": None}]
                if "FROM intelligence_raw_items raw" in self.query:
                    return [
                        {"id": 101, "title": "Covered Agent", "canonical_url": "https://example.test/covered",
                         "observed_at": "2026-10-23T09:00:00+00:00", "source_key": "github_search",
                         "name": "GitHub Search", "represented": True},
                        {"id": 102, "title": "Unlinked Agent", "canonical_url": "https://example.test/unlinked",
                         "observed_at": "2026-10-23T09:01:00+00:00", "source_key": "github_search",
                         "name": "GitHub Search", "represented": False},
                    ]
                return []
            def fetchone(self): return {"total": 0, "without_evidence": 0}

        class Connection:
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def cursor(self): return Cursor()

        monkeypatch.setattr(intelligence_v2, "get_db", Connection)
        monkeypatch.setattr(intelligence_v2, "recent_runs", lambda _: [])
        monkeypatch.setitem(client.app.dependency_overrides, require_admin, lambda: SimpleNamespace(id=uuid4()))
        response = client.get("/api/v2/admin/coverage")
        client.app.dependency_overrides.pop(require_admin, None)

        assert response.status_code == 200
        assert response.json()["sources"][0]["adapter_status"] == "supported"
        coverage = response.json()["benchmark_coverage"]
        assert coverage["observed"] == 2 and coverage["represented"] == 1
        assert coverage["coverage_rate"] == 50 and coverage["missing_items"][0]["id"] == 102
