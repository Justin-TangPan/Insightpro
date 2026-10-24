from datetime import datetime, timezone
from decimal import Decimal

from services.metric_service import _changes


def test_metric_changes_use_observed_values_and_rank_direction():
    now = datetime(2026, 10, 22, tzinfo=timezone.utc)
    yesterday = datetime(2026, 10, 21, tzinfo=timezone.utc)
    current = {"stars": {"metric_value": Decimal(3000), "observed_at": now},
               "rank_daily": {"metric_value": Decimal(1), "observed_at": now}}
    previous = {"stars": {"metric_value": Decimal(300), "observed_at": yesterday},
                "rank_daily": {"metric_value": Decimal(5), "observed_at": yesterday}}

    result = _changes(current, previous, 24, now)

    assert result["stars_delta"] == 2700
    assert result["stars_velocity"] == Decimal("112.5")
    assert result["ranking_change"] == 4
    assert result["mention_growth"] is None
