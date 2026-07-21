from crawlers import _is_quality_item
from routers.hotspots import _heuristic_score_project
from services import startup_service
from services.system_health_service import evaluate_readiness


def test_quality_gate_rejects_mojibake_and_relative_links():
    assert not _is_quality_item({"title": "ä¸\xadè¯\x81500", "url": "https://www.cls.cn/telegraph"})
    assert not _is_quality_item({"title": "有效的政府采购公告", "url": "./detail/1"})


def test_quality_gate_accepts_traceable_news():
    assert _is_quality_item({"title": "国务院发布最新数字经济行动方案", "url": "https://www.gov.cn/example"})


def test_heuristic_technical_evaluation_is_displayable():
    result = _heuristic_score_project({
        "repo_name": "example/cloud-agent",
        "repo_url": "https://github.com/example/cloud-agent",
        "description": "AI agent runtime for Kubernetes and cloud deployment",
        "language": "Python",
        "stars": "1000",
    })
    assert result["repo_name"] == "example/cloud-agent"
    assert result["evaluation_mode"] == "heuristic"
    assert result["total"] > 0
    assert result["level"]


def test_startup_job_only_runs_when_dataset_is_missing(monkeypatch):
    calls = []
    monkeypatch.setattr(startup_service, "has_rows_today", lambda _: False)
    assert startup_service._run_if_missing("github_trending", "github", lambda: calls.append("run"))
    assert calls == ["run"]

    monkeypatch.setattr(startup_service, "has_rows_today", lambda _: True)
    assert not startup_service._run_if_missing("github_trending", "github", lambda: calls.append("again"))
    assert calls == ["run"]


def test_readiness_requires_fresh_nonempty_technical_data():
    healthy = evaluate_readiness(
        {"status": "fresh", "datasets": []},
        {"business_date": "2026-07-13", "trending_count": 17, "evaluation_count": 10},
    )
    assert healthy["status"] == "healthy"
    assert healthy["failed_checks"] == []

    empty_evaluation = evaluate_readiness(
        {"status": "fresh", "datasets": []},
        {"business_date": "2026-07-13", "trending_count": 17, "evaluation_count": 0},
    )
    assert empty_evaluation["status"] == "unhealthy"
    assert "technical_evaluation_nonempty" in empty_evaluation["failed_checks"]


def test_readiness_rejects_stale_data_even_when_rows_exist():
    report = evaluate_readiness(
        {"status": "stale", "datasets": []},
        {"business_date": "2026-07-13", "trending_count": 17, "evaluation_count": 10},
    )
    assert report["status"] == "unhealthy"
    assert "freshness" in report["failed_checks"]
