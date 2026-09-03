from crawlers import _is_quality_item
from routers.hotspots import _heuristic_score_project
from services import startup_service
from services import aliyun_solution_service
from services.aliyun_solution_service import _change_summary, _classify_change, _fallback_summary, _parse_menu_tree, _summarize
from services.huawei_solution_service import _parse_catalog
from services.system_health_service import evaluate_readiness
from deep_searcher_integration import context_to_str


def test_quality_gate_rejects_mojibake_and_relative_links():
    assert not _is_quality_item({"title": "ä¸\xadè¯\x81500", "url": "https://www.cls.cn/telegraph"})
    assert not _is_quality_item({"title": "有效的政府采购公告", "url": "./detail/1"})


def test_quality_gate_accepts_traceable_news():
    assert _is_quality_item({"title": "国务院发布最新数字经济行动方案", "url": "https://www.gov.cn/example"})


def test_context_formatter_keeps_source_and_limit():
    result = context_to_str([{"collection": "solutions", "text": "技术方案" * 10}], max_chars=12)
    assert result.startswith("--- solution")
    assert result.endswith("[内容已截断]")


def test_aliyun_solution_parser_and_summary_contract():
    payload = {"data": [{
        "title": "AI", "visible": True, "children": [{
            "title": "模型服务", "visible": True, "children": [{
                "id": 1, "parentId": 2, "title": "示例解决方案", "visible": True,
                "type": "SOLUTION_DETAIL", "abcId": 123,
                "url": "https://www.aliyun.com/solution/tech-solution/example",
            }],
        }],
    }]}
    items = _parse_menu_tree(payload)
    assert items == [{
        "title": "示例解决方案",
        "url": "https://cn.aliyun.com/solution/tech-solution/example",
        "category": "AI / 模型服务",
        "primary_category": "AI",
        "secondary_category": "模型服务",
        "menu_order": 0,
        "source_type": "SOLUTION_DETAIL",
        "node_id": 123,
        "source_description": "",
        "menu_data": {"id": 1, "parentId": 2, "type": "SOLUTION_DETAIL", "tags": []},
    }]
    summary = _fallback_summary("示例解决方案", "帮助企业快速部署智能体并自动完成复杂业务任务与流程协作。")
    assert 20 <= len(summary) <= 30
    assert 20 <= len(_fallback_summary("数据合规", "")) <= 30


def test_solution_summaries_are_batched_instead_of_globally_downgraded(monkeypatch):
    from services import ai_service
    from services.aliyun_solution_service import settings as solution_settings

    calls = []
    monkeypatch.setattr(solution_settings, "CHAT_API_KEY", "configured")
    monkeypatch.setattr(ai_service, "chat_complete", lambda **kwargs: calls.append(kwargs["user_prompt"]) or "[]")
    items = [{"url": f"https://example.com/{index}", "title": f"方案{index}", "source_description": "帮助企业构建稳定可靠的云上业务系统"} for index in range(41)]

    summaries = _summarize(items)

    assert len(calls) == 3
    assert len(summaries) == 41


def test_aliyun_baseline_is_ordinary_and_real_new_item_is_recent():
    baseline = {"first_seen_date": "2026-08-21", "last_changed_date": "2026-08-21", "is_baseline": True}
    new_item = {"first_seen_date": "2026-08-26", "last_changed_date": "2026-08-26", "is_baseline": False}
    assert _classify_change(baseline, "2026-08-20") == (False, "new")
    assert _classify_change(new_item, "2026-08-20") == (True, "new")


def test_solution_changes_name_the_changed_content_and_huawei_cards_parse():
    page = '&quot;cardItem&quot;:{&quot;label&quot;:&quot;云迁移&quot;,&quot;href&quot;:&quot;https://www.huaweicloud.com/solution/implementations/migration.html&quot;,&quot;caption&quot;:&quot;迁移方案&quot;,&quot;description&quot;:&quot;&lt;p&gt;旧说明&lt;/p&gt;&quot;}&quot;cardItem&quot;:{&quot;label&quot;:&quot;AI&quot;,&quot;href&quot;:&quot;https://www.huaweicloud.com/solution/implementations/example.html&quot;,&quot;caption&quot;:&quot;示例方案&quot;,&quot;description&quot;:&quot;&lt;p&gt;旧说明&lt;/p&gt;&quot;}'
    items = _parse_catalog(page)
    item = items[0]
    assert item["title"] == "示例方案"
    assert item["category"] == "AI / 解决方案实践"
    assert items[1]["category"] == "云迁移 / 解决方案实践"
    item["content_snapshot"] = {"title": "示例方案", "category": item["category"], "source_description": "新说明", "detail_text": ""}
    summary = _change_summary({"source_description": "旧说明"}, item)
    assert "方案简介：旧说明 → 新说明" in summary


def test_huawei_parser_normalizes_combined_category_and_polluted_url():
    page = '&quot;cardItem&quot;:{&quot;label&quot;:&quot;运维监控,AI&quot;,&quot;href&quot;:&quot;https://www.huaweicloud.com/solution/implementations/yolo.html运维监控&quot;,&quot;caption&quot;:&quot;YOLO&quot;,&quot;description&quot;:&quot;视觉训练&quot;}'
    item = _parse_catalog(page)[0]
    assert item["category"] == "AI / 解决方案实践"
    assert item["url"] == "https://www.huaweicloud.com/solution/implementations/yolo.html"


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


def test_solution_catalog_catchup_requires_both_vendors(monkeypatch):
    calls = []
    monkeypatch.setattr(startup_service, "solution_catalogs_fresh_today", lambda: False)
    assert startup_service._run_solution_catalogs_if_stale(lambda: calls.append("refresh"))
    monkeypatch.setattr(startup_service, "solution_catalogs_fresh_today", lambda: True)
    assert not startup_service._run_solution_catalogs_if_stale(lambda: calls.append("again"))
    assert calls == ["refresh"]


def test_catalog_refresh_keeps_healthy_vendor_when_the_other_fails(monkeypatch):
    monkeypatch.setattr(aliyun_solution_service, "refresh_aliyun_solutions", lambda: {"status": "success", "total": 2, "new": 1, "updated": 0, "removed": 0})
    import sys
    from types import SimpleNamespace
    monkeypatch.setitem(sys.modules, "services.huawei_solution_service", SimpleNamespace(refresh_huawei_solutions=lambda: (_ for _ in ()).throw(RuntimeError("source down"))))
    result = aliyun_solution_service.refresh_solution_catalogs()
    assert result["status"] == "partial"
    assert result["total"] == 2
    assert result["vendors"]["华为云"]["status"] == "failed"

def test_readiness_requires_fresh_nonempty_technical_data():
    healthy = evaluate_readiness(
        {"status": "fresh", "datasets": []},
        {"business_date": "2026-07-13", "trending_count": 17, "evaluation_count": 10, "aliyun_solution_count": 10, "huawei_solution_count": 10},
    )
    assert healthy["status"] == "healthy"
    assert healthy["checks"]["database"] is True
    assert healthy["failed_checks"] == []

    empty_evaluation = evaluate_readiness(
        {"status": "fresh", "datasets": []},
        {"business_date": "2026-07-13", "trending_count": 17, "evaluation_count": 0, "aliyun_solution_count": 10, "huawei_solution_count": 10},
    )
    assert empty_evaluation["status"] == "unhealthy"
    assert "technical_evaluation_nonempty" in empty_evaluation["failed_checks"]


def test_readiness_rejects_stale_data_even_when_rows_exist():
    report = evaluate_readiness(
        {"status": "stale", "datasets": []},
        {"business_date": "2026-07-13", "trending_count": 17, "evaluation_count": 10, "aliyun_solution_count": 10, "huawei_solution_count": 10},
    )
    assert report["status"] == "unhealthy"
    assert "freshness" in report["failed_checks"]


def test_readiness_rejects_missing_vendor_catalog():
    report = evaluate_readiness(
        {"status": "fresh", "datasets": []},
        {"business_date": "2026-07-13", "trending_count": 17, "evaluation_count": 10, "aliyun_solution_count": 10, "huawei_solution_count": 0},
    )
    assert report["status"] == "unhealthy"
    assert "huawei_solutions_nonempty" in report["failed_checks"]
