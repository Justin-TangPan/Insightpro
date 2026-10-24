from datetime import datetime, timezone

from services import scoring_service
from services.scoring_service import github_hot_score, signal_hot_score


def test_relative_growth_can_outweigh_large_star_total():
    breakout = github_hot_score(3000, 2700)
    established = github_hot_score(101000, 1000)

    assert breakout["value"] > established["value"]
    assert breakout["stars_delta"] == 2700
    assert github_hot_score(100, 200) is None


def test_generic_score_uses_growth_corroboration_authority_and_freshness():
    now = datetime(2026, 10, 23, tzinfo=timezone.utc)
    growing = signal_hot_score({"24h": {"metrics": {"downloads": {"delta": 100, "baseline": 100}}}},
                               3, 5, ["P1", "P2"], now, now)
    static = signal_hot_score({"24h": {"metrics": {}}}, 1, 1, ["P2"], now, now)

    assert growing["value"] > static["value"]
    assert growing["momentum_basis"] == "downloads"
    assert growing["corroboration"] == 25
    assert growing["authority"] == 10
    assert growing["version"] == "signal_hot_v1"


def test_generic_score_does_not_reward_stale_or_negative_growth():
    now = datetime(2026, 10, 23, tzinfo=timezone.utc)
    stale = signal_hot_score({"24h": {"metrics": {"likes": {"delta": -50, "baseline": 100}}}},
                             1, 1, ["P2"], now.replace(day=19), now)

    assert stale["momentum"] == 0
    assert stale["freshness"] == 0


def test_generic_score_persists_metric_and_evidence_basis(monkeypatch):
    statements = []
    class Cursor:
        def execute(self, query, params=()): statements.append((query, params))
        def fetchone(self): return {"source_count": 2, "evidence_count": 3, "authorities": ["P1", "P2"]}
    monkeypatch.setattr(scoring_service, "trends_for_entity", lambda cursor, key: {"windows": {"24h": {"metrics": {}}}})

    score = scoring_service.persist_signal_hot_score(
        Cursor(), "url:abc", 17, datetime(2026, 10, 23, tzinfo=timezone.utc))

    assert score["corroboration"] == 15
    assert score["source_count"] == 2
    assert any("UPDATE intelligence_events SET scores=jsonb_set" in query for query, _ in statements)
