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
        ("POST", "/api/bidding/refresh"),
        ("POST", "/api/demand/refresh"),
        ("POST", "/api/crawl/trigger"),
        ("DELETE", "/api/reports/missing"),
        ("GET", "/api/email/subscribers"),
        ("GET", "/api/analytics"),
    ])
    def test_sensitive_endpoints_require_auth(self, method, path):
        response = client.request(method, path)
        assert response.status_code == 401
