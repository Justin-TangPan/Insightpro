from services.hotspot_service import _canonical_evaluations, _localize_evaluations
from services.intelligence_format import application, competitor, solution
from services import aliyun_solution_service
from services import competitor_news_service


def test_historical_project_sightings_use_one_analysis():
    class Cursor:
        def execute(self, sql, params):
            assert "DISTINCT ON (repo_name)" in sql
            assert params[0] == ["team/tool", "team/tool"]

        def fetchall(self):
            return [{"id": 7, "repo_name": "team/tool", "summary": "同一份项目速读", "summary_zh": None,
                     "reasoning": "同一份 AI 分析", "d1": 8, "d2": 8, "d3": 8, "d4": 8, "total": 8}]

    rows = _canonical_evaluations(Cursor(), [{"repo_name": "team/tool", "summary": "第一天"},
                                             {"repo_name": "team/tool", "summary": "第二天"}])
    formatted = _localize_evaluations(rows, "zh")
    assert {row["intelligence"]["analysis_id"] for row in formatted} == {7}
    assert {row["intelligence"]["brief"] for row in formatted} == {"同一份项目速读"}


def test_intelligence_types_preserve_identity_source_and_missing_analysis():
    cloud = solution({"id": 4, "url": "https://vendor.example/solution", "title": "迁移方案",
                      "vendor": "Huawei Cloud", "summary": "Solution value: 降低迁移风险; Open-source projects: not confirmed in official materials; Huawei Cloud resources: ECS for compute"})
    assert cloud["key"] == cloud["source"]
    assert cloud["solution_value"] == "降低迁移风险"
    assert cloud["cloud_resources"] == "ECS for compute"
    assert solution({"url": "https://vendor.example/source", "title": "来源方案", "vendor": "Huawei Cloud",
                     "summary": "Solution value: 官方说明; Open-source projects: not confirmed in official materials; Huawei Cloud resources: not confirmed in official materials",
                     "analysis_mode": "source"})["analysis"] is None
    assert competitor({"vendor": "AWS", "title": "产品更新", "link": "https://example.com/news", "summary": "用途说明"})["analysis"] is None
    assert application({"url": "https://example.com/app", "title": "应用", "analysis": "AI 分析", "analysis_id": 9})["analysis_id"] == 9


def test_huawei_solution_summary_uses_huawei_resources(monkeypatch):
    monkeypatch.setattr(aliyun_solution_service.settings, "CHAT_API_KEY", "test")
    prompts = []

    def complete(**kwargs):
        prompts.append(kwargs["user_prompt"])
        return '[{"url":"https://example.com/huawei","summary":"Solution value: 降低迁移风险并简化部署流程; Open-source projects: not confirmed in official materials; Huawei Cloud resources: ECS provides compute for the migration workload"}]'

    monkeypatch.setattr(aliyun_solution_service.ai_service, "chat_complete", complete)
    summaries = aliyun_solution_service._summarize([{"url": "https://example.com/huawei", "title": "迁移方案",
                                                     "vendor": "Huawei Cloud", "source_description": "官方迁移方案",
                                                     "detail_text": "使用 ECS 提供计算资源"}])
    assert "Huawei Cloud resources: ECS" in summaries["https://example.com/huawei"]
    assert "使用 ECS 提供计算资源" in prompts[0]


def test_competitor_updates_on_same_page_keep_separate_analyses(monkeypatch):
    monkeypatch.setattr(competitor_news_service.settings, "CHAT_API_KEY", "test")
    stored = {}
    calls = []

    class Cursor:
        rowcount = 0

        def execute(self, sql, params):
            self.sql = sql
            self.params = params
            if sql.startswith("INSERT"):
                self.rowcount = int(params[0] not in stored)
                stored[params[0]] = params[1]

        def fetchall(self):
            return [{"source_key": key} for key in stored if key in self.params[0]]

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(competitor_news_service, "get_db", Connection)
    monkeypatch.setattr(competitor_news_service.ai_service, "chat_complete", lambda **kwargs: calls.append(kwargs) or
                        '[{"index":0,"analysis":"分析 A"},'
                        '{"index":1,"analysis":"分析 B"}]')
    items = [{"url": "https://example.com/releases", "title": "更新 A", "summary": "官方摘要"},
             {"url": "https://example.com/releases", "title": "更新 B", "summary": ""}]
    assert competitor_news_service._ensure_analyses(items) == 2
    assert competitor_news_service._ensure_analyses(items) == 0
    assert len(calls) == 1
    assert len(stored) == 2
