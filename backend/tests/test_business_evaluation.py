from services.evaluation_service import BUSINESS_EVAL_SYSTEM_PROMPT
from services.hotspot_service import _canonical_total, _evaluate_live_items, _heuristic_score_project, _localize_evaluations, _summarize_eval
from services import evaluation_service


def test_business_evaluation_uses_solution_practice_admission_rules():
    assert all(rule in BUSINESS_EVAL_SYSTEM_PROMPT for rule in ("Customer Pain & Urgency", "Scenario Fit & Customer Coverage", "Business Value & Cloud Consumption", "Standardized Delivery & Replication"))

    desktop = _heuristic_score_project({"repo_name": "acme/editor", "description": "AI desktop coding tool"})
    deployable = _heuristic_score_project({"repo_name": "acme/platform", "description": "Self-hosted enterprise workflow platform deployed with Docker and Helm"})

    assert desktop["total"] <= 3.9
    assert deployable["total"] >= 6


def test_evaluation_locale_switch_preserves_scores_and_translates_estimates():
    original = _heuristic_score_project({"repo_name": "acme/platform", "description": "Self-hosted server"})
    original["summary"] = "这是一条根据项目 README 生成的独立速读。"
    chinese = _localize_evaluations([original], "zh")[0]
    assert chinese["total"] == original["total"]
    assert chinese["summary"] == original["summary"]
    assert "客户痛点" in chinese["reasoning"]
    assert "客户痛点" in chinese["recommendation"]
    assert "AI 不可用" in _localize_evaluations([original], "en")[0]["reasoning"]
    assert sum(_summarize_eval([chinese]).values()) == 1


def test_evaluation_level_is_normalized_from_score():
    item = {"d1": 9, "d2": 8, "d3": 8, "d4": 8, "total": 33, "level": "A", "reasoning": "AI result"}
    assert _canonical_total(item) == 8.2
    assert _localize_evaluations([item], "zh")[0]["level"] == "强烈推荐"
    assert _localize_evaluations([item], "en")[0]["level"] == "Strongly Recommended"
    assert _summarize_eval([item])["strong"] == 1


def test_chinese_brief_is_read_without_ai_call(monkeypatch):
    monkeypatch.setattr("services.ai_service.chat_complete", lambda **_: (_ for _ in ()).throw(AssertionError("read path called AI")))
    item = {"repo_name": "acme/one", "summary": "English brief", "summary_zh": "中文项目速读", "recommendation": "Deploy", "reasoning": "Self-hosted", "level": "Worth Doing"}
    assert _localize_evaluations([item], "zh")[0]["summary"] == "中文项目速读"
    assert _localize_evaluations([item], "en")[0]["summary"] == "English brief"


def test_single_project_ai_evaluation_writes_a_valid_row(monkeypatch):
    row = {"repo_name": "acme/platform", "repo_url": "https://github.com/acme/platform", "description": "Hosted platform", "language": "Go", "stars": "100"}
    writes = []

    class Cursor:
        def execute(self, sql, params):
            if sql.startswith("INSERT"):
                assert sql.count("%s") == len(params) == 17
                writes.append(params)

        def fetchall(self):
            return [row]

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(evaluation_service, "get_db", Connection)
    monkeypatch.setattr(evaluation_service.settings, "CHAT_API_KEY", "test")
    async def fake_agent(items, limit):
        return [{"repo_name":"acme/platform","d1":8,"d2":8,"d3":8,"d4":8,"total":8,
                 "level":"Strongly Recommended","recommendation":"部署","reasoning":"自托管平台"}]

    monkeypatch.setattr("services.hotspot_service._evaluate_live_items", fake_agent)

    assert evaluation_service.evaluate_trending_business(1)["status"] == "success"
    assert writes[0][1] == "acme/platform"

    async def fake_fallback(items, limit):
        return [_heuristic_score_project(items[0])]

    monkeypatch.setattr("services.hotspot_service._evaluate_live_items", fake_fallback)
    assert evaluation_service.evaluate_trending_business(1)["status"] == "partial_success"


def test_live_evaluation_uses_dedicated_prompt(monkeypatch):
    async def run_inline(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr("services.hotspot_service.asyncio.to_thread", run_inline)
    monkeypatch.setattr(
        "services.ai_service.chat_complete",
        lambda **kwargs: '[{"repo_name":"acme/platform","summary":"value","d1":8,"d2":8,"d3":8,"d4":8,"total":8,"level":"A","recommendation":"ship","reasoning":"fit"}]',
    )

    result = __import__("asyncio").run(_evaluate_live_items([{
        "repo_name": "acme/platform", "repo_url": "https://github.com/acme/platform",
        "description": "Hosted platform", "language": "Go", "stars": "100",
    }], 1))

    assert result[0]["evaluation_mode"] == "ai"
    assert result[0]["total"] == 8
