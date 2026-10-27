import json
import pytest

from datetime import date

from services.daily_ai_brief_service import _category, _clip, _fields, _judgments, _score, _structured, _title
from services import daily_ai_brief_service

SUMMARY = "官方公布了新版模型的能力变化与关键数据，说明了产品更新范围。" * 4
COMMENTARY = "这会影响企业模型选型和采购方式，并改变竞争格局与市场机会。" * 4


def _candidates():
    return [
        {"id": 1, "title": "某厂商发布新版模型", "category": "模型", "vendor": "某厂商",
         "source_name": "官方新闻", "source_url": "https://example.com/one",
         "published_at": "2026-10-27", "original_event_id": "evt-1", "rank": 9, "recent": True},
        {"id": 2, "title": "某厂商上线 Agent 平台", "category": "Agent", "vendor": "另一厂商",
         "source_name": "官方博客", "source_url": "https://example.com/two",
         "published_at": "2026-10-26", "original_event_id": None, "rank": 8, "recent": True},
    ]


def test_score_downranks_tutorials_and_keeps_commercial_changes():
    base = {"happened_at": "2026-10-27", "board": "apps", "date_basis": "published", "vendor": "OpenAI"}
    day = date(2026, 10, 27)
    assert _score({**base, "title": "Set Up an Always-On Monday Digest with QwenWork", "summary": "This article introduces how to create a digest."}, day) < 0
    assert _score({**base, "title": "云厂商方案更新：快速部署GPU推理服务", "summary": "提供部署步骤和资源配置。"}, day) < 0
    assert _score({**base, "title": "ChatGPT Ads expands to 26 countries", "summary": "超过10万广告主已使用该平台。"}, day) > 0


def test_title_rejects_marketing_words_and_trims_to_thirty():
    assert _title("重磅发布：完全彻底改变行业的史诗级模型") is None
    assert len(_title("这是一个非常客观平直的事实性标题文本用于验证三十字截断规则生效")) <= 30


def test_clip_ends_with_period_and_keeps_inference_out_of_summary():
    assert _clip("事实依据" * 20 + "。", 50, 120) is not None
    # 摘要禁止推测，点评允许评价性表述。
    assert _clip("预计将改变市场。" + SUMMARY, 50, 120, forbid_inference=True) is None
    assert _clip("预计将改变市场。" + SUMMARY, 50, 120) is not None
    assert _clip("只有一句简短事实。", 80, 120) is None
    assert len(_clip("事实依据" * 30, 50, 80)) <= 80


def test_fields_ignore_invalid_ids_and_attach_source_metadata():
    raw = {"items": [
        {"id": 1, "summary": SUMMARY, "commentary": COMMENTARY},
        {"id": 1, "summary": SUMMARY, "commentary": COMMENTARY},
        {"id": 9, "summary": SUMMARY, "commentary": COMMENTARY},
    ]}
    items = _fields(_candidates(), raw)
    assert [item["source_url"] for item in items] == ["https://example.com/one"]
    assert items[0]["source_name"] == "官方新闻"
    assert items[0]["original_event_id"] == "evt-1"
    assert items[0]["category"] == "模型"
    assert _fields([{**_candidates()[0], "title": "重磅发布：史诗级新模型"}], raw) == []


def test_headline_requires_richer_summary_than_quick_reads():
    headline = [{"id": 1, "summary": "官方公布了关键数据与产品变化。" * 12, "commentary": COMMENTARY}]
    items = _fields(_candidates(), {"items": headline}, "headline")
    assert len(items) == 1
    assert len(items[0]["summary"]) >= 100
    short = [{"id": 1, "summary": "官方公布了关键数据与产品变化。", "commentary": COMMENTARY}]
    assert _fields(_candidates(), {"items": short}, "headline") == []


def test_judgments_filter_invalid_and_cap_at_four():
    raw = {"recent_judgments": ([{"icon": "trend", "title": f"趋势变化方向{i}", "detail": "这是一段足够长的趋势判断说明。" * 5} for i in range(6)])
           + [{"icon": "trend", "title": "重磅炸裂判断", "detail": "这是一段足够长的趋势判断说明。" * 5},
              {"icon": "trend", "title": "OpenAI 发布新模型", "detail": "这是一段足够长的趋势判断说明。" * 5}]}
    judgments = _judgments(raw)
    assert len(judgments) == 4


def test_category_maps_infra_model_agent_commercial():
    assert _category("发布新模型能力升级", "") == "模型"
    assert _category("上线 Agent 平台", "") == "Agent"
    assert _category("建设智算数据中心并采购GPU", "") == "AI Infra"
    assert _category("调整订阅定价策略", "") == "商业化"


def test_recent_items_allow_prior_days_but_reject_older_and_observed_news():
    candidates = [{**item, "date_basis": "published"} for item in _candidates()]
    raw = {"recent_judgments": [],
           "headline": {"id": 2, "summary": SUMMARY, "commentary": COMMENTARY},
           "quick_reads": [{"id": 1, "summary": SUMMARY, "commentary": COMMENTARY}]}
    result = _structured(json.dumps(raw), candidates, date(2026, 10, 27))
    assert result["headline"]["source_url"] == "https://example.com/two"
    assert [item["source_url"] for item in result["quick_reads"]] == ["https://example.com/one"]
    candidates[1]["published_at"] = "2026-10-19"
    result = _structured(json.dumps(raw), candidates, date(2026, 10, 27))
    assert result["headline"] is None
    assert [item["source_url"] for item in result["quick_reads"]] == ["https://example.com/one"]
    candidates[1]["published_at"] = "2026-10-26"
    candidates[1]["date_basis"] = "observed"
    assert _structured(json.dumps(raw), candidates, date(2026, 10, 27))["headline"] is None
    candidates[0]["published_at"] = "2026-10-19"
    assert _structured(json.dumps(raw), candidates, date(2026, 10, 27))["headline"] is None


def test_short_quick_read_is_not_promoted_to_headline():
    candidates = [{**item, "date_basis": "published"} for item in _candidates()]
    raw = {"headline": None, "quick_reads": [{"id": 1, "summary": SUMMARY, "commentary": COMMENTARY}]}
    result = _structured(json.dumps(raw), candidates, date(2026, 10, 27))
    assert result["headline"] is None
    assert len(result["quick_reads"]) == 1


def test_regenerate_creates_new_version_even_when_candidates_are_unchanged(monkeypatch):
    class Cursor:
        def execute(self, *_): pass
        def fetchall(self): return []
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()
    saved = []
    candidate = {**_candidates()[0], "summary": SUMMARY}
    monkeypatch.setattr(daily_ai_brief_service, "_today", lambda: date(2026, 10, 27))
    monkeypatch.setattr(daily_ai_brief_service, "_readiness", lambda *_: None)
    monkeypatch.setattr(daily_ai_brief_service, "_candidates", lambda *_: [candidate])
    monkeypatch.setattr(daily_ai_brief_service, "_next_version", lambda *_: 2)
    monkeypatch.setattr(daily_ai_brief_service, "get_db", Connection)
    monkeypatch.setattr(daily_ai_brief_service, "_generate", lambda *_: {"recent_judgments": [], "headline": None, "quick_reads": []})
    monkeypatch.setattr(daily_ai_brief_service, "_persist", lambda *args: saved.append(args))
    result = daily_ai_brief_service.regenerate(task_run_id=9)
    assert result["version"] == 2 and not result.get("cached")
    assert saved[0][1] == 2 and saved[0][-1] == 9


def test_no_recent_release_never_turns_old_story_into_headline(monkeypatch):
    older = {**_candidates()[1], "published_at": "2026-10-19", "date_basis": "published", "summary": SUMMARY}
    monkeypatch.setattr(daily_ai_brief_service.ai_service, "chat_complete", lambda **_: (_ for _ in ()).throw(RuntimeError("gateway unavailable")))
    content = daily_ai_brief_service._generate([older], date(2026, 10, 27))
    assert content["headline"] is None and content["quick_reads"] == []
    assert content["recent_judgments"] == []
