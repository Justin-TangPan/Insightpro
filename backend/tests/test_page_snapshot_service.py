from datetime import date

from fastapi.testclient import TestClient

from main import app
from services import page_snapshot_service, radar_service


def test_public_page_reads_only_the_published_snapshot(monkeypatch):
    monkeypatch.setattr(page_snapshot_service, "get_page_snapshot", lambda path: {
        "id": 12, "snapshot_date": date(2026, 10, 25), "content": {"as_of": "2026-10-25", "events": []}})
    monkeypatch.setattr(radar_service, "build_intelligence_radar", lambda: (_ for _ in ()).throw(AssertionError("live aggregation ran")))
    response = TestClient(app).get("/api/radar/intelligence")
    assert response.status_code == 200
    assert response.json() == {"as_of": "2026-10-25", "events": []}
    assert response.headers["x-page-snapshot-date"] == "2026-10-25"


def test_unpublished_page_does_not_build_on_request(monkeypatch):
    monkeypatch.setattr(page_snapshot_service, "get_page_snapshot", lambda path: None)
    monkeypatch.setattr(radar_service, "build_intelligence_radar", lambda: (_ for _ in ()).throw(AssertionError("live aggregation ran")))
    assert TestClient(app).get("/api/radar/intelligence").status_code == 503
