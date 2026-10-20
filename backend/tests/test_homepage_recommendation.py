from routers import dashboard
from routers.dashboard import _homepage_recommendation, _one_sentence


def test_homepage_recommendation_is_reduced_to_one_sentence():
    assert _one_sentence("建议举措：先验证高价值项目。然后再扩展。") == "先验证高价值项目。"
    assert _one_sentence("") == ""


def test_homepage_recommendation_attempts_ai_once_per_day(monkeypatch):
    saved = {}
    calls = []

    class Cursor:
        def execute(self, sql, params=()):
            if sql.startswith("SELECT recommendation FROM homepage_daily_recommendations"):
                self.one = {"recommendation": saved[params[0]]} if params[0] in saved else None
            elif "FROM trending_business_eval" in sql:
                self.many = [{"repo_name": "acme/agent", "summary": "可验证", "recommendation": "先试点"}]
            elif "FROM aliyun_solutions" in sql or "FROM competitor_news" in sql:
                self.many = []
            elif sql.startswith("INSERT INTO homepage_daily_recommendations"):
                saved[params[0]] = params[1]

        def fetchone(self):
            return self.one

        def fetchall(self):
            return self.many

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def cursor(self):
            return Cursor()

    def fake_chat_complete(**_):
        calls.append(1)
        raise TimeoutError

    monkeypatch.setattr(dashboard, "get_db", Connection)
    monkeypatch.setattr(dashboard, "chat_complete", fake_chat_complete)

    assert _homepage_recommendation("2026-09-24")["source"] == "fallback"
    assert _homepage_recommendation("2026-09-24")["source"] == "stored"
    assert len(calls) == 1
