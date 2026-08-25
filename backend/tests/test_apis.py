import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestAPIEndpoints:
    def test_root(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "message" in resp.json()
        assert resp.json()["version"] == "0.4.0"

    def test_lan_frontend_origin_is_allowed(self):
        resp = client.get(
            "/api/github-trending/business-eval",
            headers={"Origin": "http://192.168.0.191:3000"},
        )
        assert resp.status_code == 200
        assert resp.headers["access-control-allow-origin"] == "http://192.168.0.191:3000"

    @pytest.mark.parametrize("method,path", [
        ("POST", "/api/github-trending/refresh"),
        ("POST", "/api/github-trending/business-eval/refresh"),
        ("POST", "/api/solutions/aliyun/refresh"),
        ("POST", "/api/crawl/trigger"),
        ("DELETE", "/api/reports/missing"),
        ("GET", "/api/email/subscribers"),
        ("POST", "/api/email/subscribe"),
        ("PUT", "/api/email/subscribers/1"),
        ("POST", "/api/email/subscribers/1/send"),
        ("GET", "/api/email/preview"),
        ("GET", "/api/analytics"),
        ("GET", "/api/workbench/summary"),
        ("GET", "/api/workbench/requirements"),
        ("POST", "/api/workbench/requirements"),
        ("GET", "/api/workbench/solutions"),
        ("POST", "/api/workbench/solutions"),
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
