import json

from services import daily_board_insight_service as service


def test_source_links_require_http_host():
    assert service._source_url("https://example.com/real")
    assert not service._source_url("javascript:alert(1)")
    assert not service._source_url("https://")


def test_solution_evidence_orders_aliyun_before_huawei(monkeypatch):
    queries = []

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return self
        def execute(self, sql, params): queries.append((sql, params))
        def fetchall(self): return []

    monkeypatch.setattr(service, "get_db", Connection)
    assert service._legacy_rows("solutions", "2026-10-20") == []
    sql, params = queries[0]
    assert "WHEN 'Alibaba Cloud' THEN 0 WHEN 'Huawei Cloud' THEN 1" in sql
    assert "last_changed_date BETWEEN %s AND %s" in sql
    assert params == ("2026-10-14", "2026-10-20")


def test_app_board_uses_publication_date_only_and_keeps_observation_separate(monkeypatch):
    queries = []
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return self
        def execute(self, sql, params): queries.append((sql, params))
        def fetchall(self): return []

    monkeypatch.setattr(service, "get_db", Connection)
    service._legacy_rows("apps", "2026-10-20")
    sql, _ = queries[0]
    assert "published_at IS NOT NULL" in sql
    assert "source_fetched_at" not in sql


def test_scheduled_insight_waits_for_active_source_refreshes(monkeypatch):
    states = iter((True, False))
    from services import task_service
    monkeypatch.setattr(task_service, "required_source_tasks", lambda: ("github_daily", "daily_crawl", "competitor_daily"))

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return self
        def execute(self, *_): pass
        def fetchone(self): return {"present": next(states)}
        def fetchall(self): return [{"task_key": key, "status": "success"} for key in ("github_daily", "daily_crawl", "competitor_daily")]

    monkeypatch.setattr(service, "get_db", Connection)
    monkeypatch.setattr(service.time, "sleep", lambda _: None)
    service._wait_for_source_refreshes()


def test_scheduled_insight_refuses_missing_or_failed_source_runs(monkeypatch):
    from services import task_service
    monkeypatch.setattr(task_service, "required_source_tasks", lambda: ("github_daily", "daily_crawl", "competitor_daily"))
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return self
        def execute(self, *_): pass
        def fetchone(self): return {"present": False}
        def fetchall(self): return [{"task_key": "github_daily", "status": "failed"}]

    monkeypatch.setattr(service, "get_db", Connection)
    try:
        service._wait_for_source_refreshes()
    except RuntimeError as exc:
        assert "github_daily" in str(exc)
        assert "daily_crawl" in str(exc)
    else:
        raise AssertionError("incomplete source run set must not generate board insights")


def test_daily_insight_uses_every_unique_source_and_caches(monkeypatch):
    monkeypatch.setattr(service, "_rows", lambda board, day: [
        {"title": "项目一", "summary": "云部署", "url": "https://github.com/example/one", "today_stars": "6,164 stars this month"},
        {"title": "项目一", "summary": "云部署", "url": "https://github.com/example/one", "today_stars": "6,164 stars this month"},
        {"title": "项目二", "summary": "商业应用", "url": "https://github.com/example/two"},
    ])
    saved = {}
    calls = []

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return self
        def execute(self, sql, params):
            if sql.startswith("INSERT"):
                saved["analysis"] = params[3]
                saved["fingerprint"] = params[2]
        def fetchone(self): return saved or None

    monkeypatch.setattr(service, "get_db", Connection)
    response = {"judgment": "项目方向集中在云部署。", "focus_id": 1,
                "focus_reason": "项目一近期热度突出且与云部署相关。", "focus_analysis": "项目一围绕云部署能力提供了具体实现，可观察后续采用情况。",
                "focus_impact": "可能带动云端部署与托管服务需求。", "focus_caveat": "真实采用率仍需核实。"}
    monkeypatch.setattr(service.ai_service, "chat_complete", lambda **kwargs: calls.append(kwargs) or json.dumps(response, ensure_ascii=False))
    first = service.insight("github")
    second = service.insight("github")
    assert first["count"] == 2
    assert len(first["sources"]) == 2
    assert "项目一" in calls[0]["user_prompt"] and "项目二" in calls[0]["user_prompt"]
    assert "非单日新增" in calls[0]["user_prompt"]
    assert second["summary"] == first["summary"]
    assert first["summary"]["focus"]["title"] == "项目一"
    assert first["summary"]["focus"]["url"] == "https://github.com/example/one"
    assert len(calls) == 1


def test_structured_response_strips_markdown_and_selects_real_focus():
    rows = [{"title": "真实项目", "url": "https://example.com/real", "event_id": 55}]
    raw = json.dumps({"judgment": "**今日变化**", "focus_id": 1,
                      "focus_reason": "## 近期热度集中于该项目", "focus_analysis": "项目新增云端部署能力并提供了相关实现。",
                      "focus_impact": "可能形成新的云端托管需求。", "focus_caveat": "采用情况待核实。"})
    result = service._structured(raw, rows)
    assert result["judgment"] == "今日变化。"
    assert result["focus"]["title"] == "真实项目"
    assert result["focus"]["event_id"] == 55
    assert result["focus"]["why"] == "近期热度集中于该项目"


def test_structured_rejects_unknown_or_empty_focus():
    rows = [{"title": "真实项目", "url": "https://example.com/real"}]
    raw = json.dumps({"judgment": "今日产品能力出现重要更新", "focus_id": 2,
                      "focus_reason": "近期值得关注", "focus_analysis": "产品更新了部署能力。",
                      "focus_impact": "可能影响云服务需求。"})
    try:
        service._structured(raw, rows)
    except ValueError as exc:
        assert "incomplete" in str(exc)
    else:
        raise AssertionError("unknown focus source must be rejected")


def test_community_fallback_only_summarizes_source_evidence():
    rows = [
        {"title": "AI Agent 工具调用", "url": "https://example.com/agent", "source": "CSDN", "topic_category": "Agent 与框架"},
        {"title": "另一个智能体话题", "url": "https://example.com/agent-2", "source": "知乎", "topic_category": "Agent 与框架"},
        {"title": "模型推理更新", "url": "https://example.com/model", "source": "腾讯云社区", "topic_category": "模型与技术"},
    ]
    summary = service._community_fallback(rows)
    assert summary["analysis_mode"] == "source_only"
    assert "Agent 与框架、模型与技术" in summary["judgment"]
    assert summary["focus"]["title"] == "AI Agent 工具调用"
    assert summary["focus"]["url"] == rows[0]["url"]
    assert "发布日期未逐条核实" in summary["focus"]["caveat"]


def test_community_insight_returns_source_summary_when_ai_json_is_invalid(monkeypatch):
    rows = [{"title": "AI Agent 工具调用", "summary": "安全与校验", "url": "https://example.com/agent",
             "source": "CSDN", "topic_category": "Agent 与框架"}]
    monkeypatch.setattr(service, "_rows", lambda board, day: rows)
    saved = {}

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return self
        def execute(self, sql, params):
            if sql.startswith("INSERT"):
                saved["analysis"] = json.loads(params[3])
        def fetchone(self): return None

    monkeypatch.setattr(service, "get_db", Connection)
    monkeypatch.setattr(service.ai_service, "chat_complete", lambda **_: "not valid json")

    result = service.insight("community")
    assert result["summary"]["analysis_mode"] == "source_only"
    assert result["summary"]["focus"]["title"] == "AI Agent 工具调用"
    assert saved["analysis"] == result["summary"]


def test_old_cached_summary_is_regenerated(monkeypatch):
    rows = [{"title": "真实项目", "summary": "云部署能力更新", "url": "https://example.com/real"}]
    monkeypatch.setattr(service, "_rows", lambda board, day: rows)
    monkeypatch.setattr(service, "sha256", lambda _: type("Digest", (), {"hexdigest": lambda self: "same"})())
    saved = {"fingerprint": "same", "analysis": json.dumps({
        "judgment": "旧分析", "changes": ["旧变化"], "opportunities": ["云端机会"],
        "risks": ["模型风险需要评估"], "representatives": []})}
    calls = []

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return self
        def execute(self, sql, params):
            if sql.startswith("INSERT"):
                saved.update(fingerprint=params[2], analysis=params[3])
        def fetchone(self): return saved

    response = {"judgment": "项目开始提供云端推理能力", "focus_id": 1,
                "focus_reason": "新增推理部署值得跟进。", "focus_analysis": "项目新增云端推理部署，提供了明确的能力更新。",
                "focus_impact": "云厂商可能获得模型托管与推理服务机会。", "focus_caveat": "实际业务表现仍需验证。"}
    monkeypatch.setattr(service, "get_db", Connection)
    monkeypatch.setattr(service.ai_service, "chat_complete", lambda **kwargs: calls.append(kwargs) or json.dumps(response, ensure_ascii=False))

    result = service.insight("apps")
    assert len(calls) == 1
    assert result["summary"]["focus"]["impact"] == response["focus_impact"]


def test_daily_board_prefers_v2_event_and_keeps_unmatched_v1_evidence(monkeypatch):
    class Cursor:
        query = ""
        def execute(self, query, *_): self.query = query
        def fetchall(self):
            if "FROM intelligence_events event" in self.query:
                return [{"event_id": 55, "title": "V2 event", "url": "https://example.com/shared",
                         "summary": "V2 evidence", "source": "Official", "vendor": "Vendor"}]
            return []
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()

    monkeypatch.setattr(service, "get_db", Connection)
    monkeypatch.setattr(service, "_legacy_rows", lambda *_: [
        {"title": "Legacy duplicate", "url": "https://example.com/shared", "summary": "old"},
        {"title": "Legacy-only", "url": "https://example.com/legacy", "summary": "old source"},
    ])

    rows = service._rows("apps", "2026-10-20")

    assert [row["title"] for row in rows] == ["V2 event", "Legacy-only"]
    assert rows[0]["event_id"] == 55
