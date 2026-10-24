import asyncio

from fastapi import FastAPI

import main


def test_scheduler_disabled_skips_scheduler_and_startup_catchup(monkeypatch):
    from services import embedding_config_service, runtime_config_service, startup_service

    monkeypatch.setattr(main.settings, "SCHEDULER_ENABLED", False)
    monkeypatch.setattr(main.settings, "STARTUP_CATCHUP_ENABLED", True)
    monkeypatch.setattr(main.settings, "REQUIREMENT_ABSORPTION_ON_STARTUP", False)
    bootstrap_calls = []
    monkeypatch.setattr(startup_service, "ensure_runtime_schema", lambda **kwargs: bootstrap_calls.append(kwargs))
    monkeypatch.setattr(runtime_config_service, "load", lambda: None)
    monkeypatch.setattr(embedding_config_service, "load", lambda: None)
    monkeypatch.setattr(main, "init_deep_searcher", lambda: None)
    monkeypatch.setattr(main, "init_crawler_tables", lambda: None)

    class UnexpectedScheduler:
        def __init__(self, **_):
            raise AssertionError("scheduler must stay disabled")

    monkeypatch.setattr(main, "BackgroundScheduler", UnexpectedScheduler)
    app = FastAPI()

    async def check():
        async with main.lifespan(app):
            assert app.state.scheduler is None
            assert bootstrap_calls == [{"absorb_requirements": False}]

    asyncio.run(check())
