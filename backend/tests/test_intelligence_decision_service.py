"""Fully-automatic intelligence decision: AI decides publish vs drop."""
from __future__ import annotations

import json

import pytest

from services import ai_service as ai_module
from services import intelligence_decision_service as decision_service
from services import prompt_service


def _fake_event(**overrides):
    base = {"id": 1, "status": "pending_review", "business_scopes": ["solutions"],
            "title": "测试方案", "event_type": "solution_catalog_change",
            "content_version": 1, "scores": {}, "entity_key": "solution:x",
            "event_key": "solution-change:x", "last_seen_at": None}
    base.update(overrides)
    return base


def _install_ai(monkeypatch, decision="publish"):
    def chat_complete(**kwargs):
        return json.dumps({"decision": decision, "rationale": "证据充分",
                           "what_happened": "发生了什么", "why_important": "为什么重要",
                           "technical_impact": "技术影响", "business_impact": "商业影响",
                           "confidence": 88, "importance": 90}, ensure_ascii=False)

    monkeypatch.setattr(ai_module, "chat_complete", chat_complete)
    monkeypatch.setattr(ai_module, "extract_json", lambda raw: json.loads(raw))
    monkeypatch.setattr(prompt_service, "published_prompt", lambda name: None)


def _install_db(monkeypatch, event):
    seen = {}

    class Cursor:
        def execute(self, sql, params=None):
            if "analysis_status='processing'" in sql:
                seen["processing"] = params
            if "UPDATE intelligence_events SET" in sql and "processing" not in sql:
                seen["update"] = params
            if "INSERT INTO intelligence_audit" in sql:
                seen["audit"] = params

        def fetchone(self):
            return {"content_version": event["content_version"]}

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def cursor(self):
            return Cursor()

    seen["conn"] = Conn
    monkeypatch.setattr(decision_service, "get_db", lambda: Conn())
    return seen


def test_decision_publish_sets_active_and_audits(monkeypatch):
    event = _fake_event()
    monkeypatch.setattr(decision_service, "_restricted_event", lambda event_id: event)
    monkeypatch.setattr(decision_service, "_evidence_facts",
                        lambda event: [{"id": 10, "source_name": "阿里云", "title": "t",
                                        "canonical_url": "https://x", "published_at": None, "observed_at": None}])
    _install_ai(monkeypatch, decision="publish")
    seen = _install_db(monkeypatch, event)

    result = decision_service.decide_event(1)
    assert result["decision"] == "publish"
    assert result["status"] == "active"
    assert "audit" in seen


def _evidence_sample():
    return [{"id": 10, "source_name": "阿里云", "title": "测试方案",
             "canonical_url": "https://example.com/x", "published_at": None, "observed_at": None}]


def test_decision_drop_sets_ignored(monkeypatch):
    event = _fake_event()
    monkeypatch.setattr(decision_service, "_restricted_event", lambda event_id: event)
    monkeypatch.setattr(decision_service, "_evidence_facts", lambda event: _evidence_sample())
    _install_ai(monkeypatch, decision="drop")
    _install_db(monkeypatch, event)

    result = decision_service.decide_event(1)
    assert result["decision"] == "drop"
    assert result["status"] == "ignored"


def test_invalid_decision_raises(monkeypatch):
    event = _fake_event()
    monkeypatch.setattr(decision_service, "_restricted_event", lambda event_id: event)
    monkeypatch.setattr(decision_service, "_evidence_facts", lambda event: _evidence_sample())
    _install_ai(monkeypatch, decision="maybe")
    _install_db(monkeypatch, event)
    with pytest.raises(ValueError):
        decision_service.decide_event(1)


def test_non_undecided_event_rejected(monkeypatch):
    class Cursor:
        def execute(self, sql, params=None):
            pass

        def fetchone(self):
            return _fake_event(status="active")

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(decision_service, "get_db", lambda: Conn())
    with pytest.raises(ValueError):
        decision_service._restricted_event(1)