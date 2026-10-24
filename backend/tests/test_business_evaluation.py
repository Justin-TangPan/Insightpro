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


def test_chinese_brief_translation_retries_once_with_explicit_prompt(monkeypatch):
    prompts = []
    requests = []
    responses = iter(("English response", "这是中文项目简介。", "PASS"))

    def fake_chat_complete(**kwargs):
        prompts.append(kwargs["system_prompt"])
        requests.append(kwargs)
        return next(responses)

    monkeypatch.setattr("services.ai_service.chat_complete", fake_chat_complete)

    assert evaluation_service._translate_chinese_brief("Project description") == "这是中文项目简介。"
    assert len(prompts) == 3
    assert "Simplified Chinese" in prompts[1]
    assert "faithfully preserves" in prompts[2]
    assert "untrusted" in prompts[0]
    assert '"source": "Project description"' in requests[0]["user_prompt"]
    assert '"translation": "这是中文项目简介。"' in requests[2]["user_prompt"]


def test_chinese_brief_translation_stops_after_two_non_chinese_responses(monkeypatch):
    calls = []
    monkeypatch.setattr("services.ai_service.chat_complete", lambda **kwargs: (calls.append(kwargs) or "English only"))

    assert evaluation_service._translate_chinese_brief("Project description") is None
    assert len(calls) == 2


def test_chinese_brief_translation_rejects_failed_semantic_review(monkeypatch):
    responses = iter(("这是与原文无关的中文句子。", "FAIL"))
    monkeypatch.setattr("services.ai_service.chat_complete", lambda **_: next(responses))

    assert evaluation_service._translate_chinese_brief("Project description") is None


def test_chinese_brief_translation_rejects_mixed_language_and_refusal_text():
    assert not evaluation_service._valid_chinese_translation("English response 中文")
    assert not evaluation_service._valid_chinese_translation("抱歉，无法翻译这段内容。")
    assert evaluation_service._valid_chinese_translation("这是一个用于自动化工作流的开源项目。")


def test_invalid_chinese_brief_is_not_written(monkeypatch):
    statements = []

    class Cursor:
        def execute(self, sql, _params=()): statements.append(sql)
        def fetchall(self): return [{"repo_name": "org/repo", "summary": "English source summary", "source": "English source summary with enough characters"}]

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return Cursor()

    monkeypatch.setattr(evaluation_service, "get_db", Connection)
    monkeypatch.setattr(evaluation_service, "_translate_chinese_brief", lambda _source: None)

    result = evaluation_service.translate_project_summaries(limit=1)

    assert result == {"status": "partial_success", "count": 0, "requested": 1}
    assert not any("UPDATE trending_business_eval SET summary_zh" in sql for sql in statements)


def test_existing_chinese_source_is_reused_without_ai(monkeypatch):
    statements = []
    chinese = "面向 Claude Code 的示例指南，提供从基础到高级 agent 的模板。"

    class Cursor:
        def execute(self, sql, params=()): statements.append((sql, params))
        def fetchall(self): return [{"repo_name": "org/repo", "summary": chinese, "source": chinese}]

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return Cursor()

    monkeypatch.setattr(evaluation_service, "get_db", Connection)
    monkeypatch.setattr("services.ai_service.chat_complete", lambda **_: (_ for _ in ()).throw(AssertionError("Chinese source must not call AI")))

    result = evaluation_service.translate_project_summaries(limit=1)

    assert result == {"status": "success", "count": 1, "requested": 1}
    update = next(params for sql, params in statements if "UPDATE trending_business_eval SET summary_zh" in sql)
    assert update[0] == chinese


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
    monkeypatch.setattr("services.repository_service.list_trending_repositories",
                        lambda *_: {"source": "v1_compatibility", "items": []})
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
    monkeypatch.setattr("services.prompt_service.published_prompt", lambda name: {
        "prompt_name": name, "version": 3, "system_prompt": "Managed repository prompt", "user_prompt_template": "Evidence:\n{projects}"})
    observed = {}
    monkeypatch.setattr(
        "services.ai_service.chat_complete",
        lambda **kwargs: (observed.update(kwargs) or '[{"repo_name":"acme/platform","summary":"value","d1":8,"d2":8,"d3":8,"d4":8,"total":8,"level":"A","recommendation":"ship","reasoning":"fit","technical_assessment":{"engineering_maturity":{"score":7,"reasoning":"有贡献者和发布记录","evidence_keys":["contributors_count","latest_release_tag"]},"innovation":{"score":6,"reasoning":"主题与说明显示新方向","evidence_keys":["topics","unknown_claim"]},"deployability":{"score":8,"reasoning":"有可复用许可证","evidence_keys":["license"]}}}]'),
    )

    result = __import__("asyncio").run(_evaluate_live_items([{
        "repo_name": "acme/platform", "repo_url": "https://github.com/acme/platform",
        "description": "Hosted platform", "language": "Go", "stars": "100",
        "pushed_at": "2026-10-22T10:00:00Z", "contributors_count": 17, "license": "MIT",
        "topics": ["agent", "mcp"], "latest_release": {"tag_name": "v1.2.0", "published_at": "2026-10-20"},
    }], 1))

    assert result[0]["evaluation_mode"] == "ai"
    assert result[0]["total"] == 8
    assert result[0]["prompt_name"] == "repository_business_eval"
    assert result[0]["prompt_version"] == 3
    assert observed["system_prompt"] == "Managed repository prompt"
    assert "acme/platform" in observed["user_prompt"]
    assert '"contributors_count": 17' in observed["user_prompt"]
    assert '"latest_release_tag": "v1.2.0"' in observed["user_prompt"]
    assert '"license": "MIT"' in observed["user_prompt"]
    technical = result[0]["technical_assessment"]
    assert technical["engineering_maturity"]["score"] == 7
    assert technical["engineering_maturity"]["evidence_keys"] == ["contributors_count", "latest_release_tag"]
    assert technical["innovation"]["evidence_keys"] == ["topics"]
    assert technical["deployability"]["score"] == 8


def test_technical_dimensions_without_valid_evidence_are_not_scored():
    from services.hotspot_service import _technical_assessment

    result = _technical_assessment({
        "innovation": {"score": 9, "reasoning": "sounds new", "evidence_keys": ["stars"]},
        "engineering_maturity": {"score": 8, "reasoning": "popular", "evidence_keys": ["stars"]},
        "deployability": {"score": 7, "reasoning": "popular", "evidence_keys": ["stars"]},
    }, {"repo_name": "org/repo", "description": "Small tool", "stars": "10k"})

    assert result["innovation"]["score"] is None
    assert result["innovation"]["evidence_keys"] == []
    assert "证据不足" in result["innovation"]["reasoning"]
    assert result["engineering_maturity"]["score"] is None
    assert result["deployability"]["score"] is None


def test_v2_evaluation_persists_canonical_analysis_and_event_scores(monkeypatch):
    from services import repository_service
    writes = []
    row = {"entity_key": "github:acme/platform", "event_id": 73, "repo_name": "acme/platform",
           "repo_url": "https://github.com/acme/platform", "description": "Hosted platform", "language": "Go",
           "stars": "1.2k", "forks": "60", "today_stars": "240", "category": "daily", "scores": {}}
    monkeypatch.setattr(repository_service, "list_trending_repositories",
                        lambda *_: {"source": "event_store", "items": [row], "date": "2026-10-23"})
    class Cursor:
        def execute(self, sql, params=()):
            writes.append((sql, params))
            self.row = {"id": 91} if "RETURNING id" in sql else None
        def fetchall(self): return []
        def fetchone(self): return self.row
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(evaluation_service, "get_db", Connection)
    monkeypatch.setattr("services.prompt_service.published_prompt", lambda _: {"version": 1})
    monkeypatch.setattr(evaluation_service.settings, "CHAT_API_KEY", "test")
    async def evaluate(items, limit):
        return [{"repo_name": items[0]["repo_name"], "summary": "基于来源描述的方案判断", "d1": 8, "d2": 7,
                 "d3": 7, "d4": 8, "total": 7.5, "level": "Worth Doing", "recommendation": "验证部署",
                 "reasoning": "依据已采集描述", "evaluation_mode": "ai", "prompt_name": "repository_business_eval",
                 "prompt_version": 1}]
    monkeypatch.setattr("services.hotspot_service._evaluate_live_items", evaluate)
    monkeypatch.setattr("services.hotspot_service._store_live_evaluations", lambda *_: None)

    result = evaluation_service.evaluate_trending_business(1)

    assert result == {"status": "success", "count": 1, "date": "2026-10-23", "source": "event_store"}
    insert = next(params for sql, params in writes if "INSERT INTO intelligence_analysis" in sql)
    assert insert[0] == row["entity_key"] and insert[2:] == ("repository_business_eval", 1)
    event_update = next(params for sql, params in writes if "UPDATE intelligence_events SET scores" in sql)
    assert event_update[1] == row["event_id"]


def test_publishing_new_prompt_version_refreshes_existing_repository_analysis(monkeypatch):
    from services import repository_service
    row = {"entity_key": "github:acme/platform", "event_id": 73, "repo_name": "acme/platform",
           "repo_url": "https://github.com/acme/platform", "description": "Hosted platform", "scores": {}}
    monkeypatch.setattr(repository_service, "list_trending_repositories",
                        lambda *_: {"source": "event_store", "items": [row], "date": "2026-10-23"})
    writes = []
    class Cursor:
        def execute(self, sql, params=()): self.sql = sql; writes.append((sql, params))
        def fetchall(self):
            return [{"source_key": row["entity_key"], "prompt_name": "repository_business_eval", "prompt_version": 1,
                     "analysis": '{"d1":7,"d2":7,"d3":7,"d4":7,"total":7,"evaluation_mode":"ai"}'}] if "SELECT source_key,analysis,prompt_name" in self.sql else []
        def fetchone(self): return {"id": 91}
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(evaluation_service, "get_db", Connection)
    monkeypatch.setattr("services.prompt_service.published_prompt", lambda _: {"version": 2})
    monkeypatch.setattr(evaluation_service.settings, "CHAT_API_KEY", "test")
    calls = []
    async def evaluate(items, limit):
        calls.append(items[0]["repo_name"])
        return [{"repo_name": items[0]["repo_name"], "d1": 7, "d2": 7, "d3": 7, "d4": 7, "total": 7,
                 "evaluation_mode": "ai", "prompt_name": "repository_business_eval", "prompt_version": 2,
                 "technical_assessment": {"innovation": {"score": None, "evidence_keys": []}}}]
    monkeypatch.setattr("services.hotspot_service._evaluate_live_items", evaluate)
    monkeypatch.setattr("services.hotspot_service._store_live_evaluations", lambda *_: None)

    result = evaluation_service.evaluate_trending_business(1)

    assert result["status"] == "success"
    assert calls == ["acme/platform"]
    assert any("INSERT INTO intelligence_analysis" in sql and params[-1] == 2 for sql, params in writes)


def test_failed_new_analysis_does_not_replace_a_previous_ai_result(monkeypatch):
    from services import repository_service
    row = {"entity_key": "github:acme/platform", "event_id": 73, "repo_name": "acme/platform",
           "repo_url": "https://github.com/acme/platform", "description": "Hosted platform", "scores": {}}
    monkeypatch.setattr(repository_service, "list_trending_repositories",
                        lambda *_: {"source": "event_store", "items": [row], "date": "2026-10-23"})
    writes = []
    class Cursor:
        def execute(self, sql, params=()): self.sql = sql; writes.append((sql, params))
        def fetchall(self):
            return [{"source_key": row["entity_key"], "prompt_name": "repository_business_eval", "prompt_version": 1,
                     "analysis": '{"d1":7,"d2":7,"d3":7,"d4":7,"total":7,"evaluation_mode":"ai","reasoning":"existing"}'}] if "SELECT source_key,analysis,prompt_name" in self.sql else []
        def fetchone(self): raise AssertionError("failed refresh must not write")
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(evaluation_service, "get_db", Connection)
    monkeypatch.setattr("services.prompt_service.published_prompt", lambda _: {"version": 2})
    monkeypatch.setattr(evaluation_service.settings, "CHAT_API_KEY", "test")
    async def failed_evaluate(items, limit):
        return [{"repo_name": row["repo_name"], "d1": 4, "d2": 4, "d3": 4, "d4": 4,
                 "total": 4, "evaluation_mode": "heuristic"}]
    monkeypatch.setattr("services.hotspot_service._evaluate_live_items", failed_evaluate)
    monkeypatch.setattr("services.hotspot_service._store_live_evaluations", lambda *_: None)

    result = evaluation_service.evaluate_trending_business(1)

    assert result["status"] == "success"
    assert not any("INSERT INTO intelligence_analysis" in sql for sql, _ in writes)


def test_v2_evaluation_read_prefers_event_scores_over_v1(monkeypatch):
    from services import repository_service
    row = {"entity_key": "github:acme/platform", "event_id": 73, "repo_name": "acme/platform",
           "repo_url": "https://github.com/acme/platform", "language": "Go", "stars": "1.2k", "scores": {
               "business_evaluation": {"summary": "V2 analysis", "d1": 8, "d2": 7, "d3": 7, "d4": 8,
                                       "total": 7.5, "evaluation_mode": "ai"}}}
    monkeypatch.setattr(repository_service, "list_trending_repositories",
                        lambda *_: {"source": "event_store", "items": [row], "date": "2026-10-23"})
    class Cursor:
        def execute(self, *_): pass
        def fetchall(self): return []
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(evaluation_service, "get_db", Connection)

    result = evaluation_service.list_repository_business_evaluations("2026-10-23")

    assert result["items"][0]["summary"] == "V2 analysis"
    assert result["items"][0]["event_id"] == 73
