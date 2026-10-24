import asyncio
from types import SimpleNamespace
from starlette.background import BackgroundTasks

from routers import intelligence_v2
from services.task_service import source_task_key


def test_rss_source_uses_the_shared_discovery_schedule():
    assert source_task_key({"adapter": "rss_feed", "schedule": {}}) == "discovery_sentinel_daily"


def test_source_enable_accepts_request_cache_community_adapter(monkeypatch):
    source = {"source_key": "community_zhihu", "adapter": "community_zhihu", "enabled": False, "schedule": {}}
    monkeypatch.setattr(intelligence_v2, "list_sources", lambda: [source])
    monkeypatch.setattr(intelligence_v2, "set_source_enabled", lambda key, enabled, actor: {"source_key": key, "enabled": enabled})
    result = asyncio.run(intelligence_v2.update_source_state(
        "community_zhihu", intelligence_v2.SourceState(enabled=True), admin=SimpleNamespace(id="admin")))
    assert result == {"source_key": "community_zhihu", "enabled": True}


def test_manual_community_run_queues_source_scoped_refresh_without_running_it(monkeypatch):
    source = {"source_key": "community_zhihu", "adapter": "community_zhihu", "enabled": True, "schedule": {}}
    monkeypatch.setattr(intelligence_v2, "list_sources", lambda: [source])
    tasks = BackgroundTasks()
    result = asyncio.run(intelligence_v2.run_source("community_zhihu", tasks))
    assert result == {"status": "accepted", "source_key": "community_zhihu", "mode": "request_cache_source_refresh"}
    assert tasks.tasks[0].func.__name__ == "refresh_community_source"
    assert tasks.tasks[0].args == ("community_zhihu",)
