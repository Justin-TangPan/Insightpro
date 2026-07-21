import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.bidding_service import parse_budget_yuan


class TestParseBudgetYuan:
    def test_basic(self):
        assert parse_budget_yuan("500万元") == 5_000_000
        assert parse_budget_yuan("1.5亿元") == 150_000_000
        assert parse_budget_yuan("100万元") == 1_000_000

    def test_range_takes_max(self):
        assert parse_budget_yuan("100-200万元") == 2_000_000
        assert parse_budget_yuan("500万-1000万元") == 10_000_000

    def test_formats(self):
        assert parse_budget_yuan("1,500,000元") == 1_500_000
        assert parse_budget_yuan("￥500万") == 5_000_000
        assert parse_budget_yuan("¥1.2亿") == 120_000_000

    def test_empty_and_invalid(self):
        assert parse_budget_yuan("") is None
        assert parse_budget_yuan(None) is None
        assert parse_budget_yuan("待定") is None
        assert parse_budget_yuan("面议") is None

    def test_bare_number(self):
        assert parse_budget_yuan("5000000") == 5_000_000
        assert parse_budget_yuan("15000000") == 15_000_000
