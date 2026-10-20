import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from services import embedded_agent_service as core
from routers.agent import _heartbeat_chunks


def test_decisions_are_user_session_request_scoped_and_single_use():
    writes = []
    async def drain():
        return None
    stream = SimpleNamespace(write=writes.append, drain=drain)
    core.active_turns[("alice", "session")] = {"pending": {"request_id": "question"}, "process": SimpleNamespace(stdin=stream)}
    async def run():
        for user, session, request in [("bob", "session", "question"), ("alice", "other", "question"), ("alice", "session", "other")]:
            with pytest.raises(HTTPException):
                await core.resolve(user, session, request, "PostgreSQL")
        await core.resolve("alice", "session", "question", "PostgreSQL")
        with pytest.raises(HTTPException):
            await core.resolve("alice", "session", "question", "MySQL")
    try:
        asyncio.run(run())
        assert len(writes) == 1 and b"PostgreSQL" in writes[0]
    finally:
        core.active_turns.clear()


def test_closing_heartbeat_cancels_pending_worker_generator():
    closed = []
    async def source():
        try:
            await asyncio.sleep(10)
            yield {}
        finally:
            closed.append(True)
    async def run():
        stream = _heartbeat_chunks(source(), interval=0.01)
        assert await stream.__anext__() is None
        await stream.aclose()
    asyncio.run(run())
    assert closed == [True]


def test_stop_terminates_and_releases_only_its_live_turn():
    class Process:
        returncode = None

        def __init__(self):
            self.terminated = False

        def terminate(self):
            self.terminated = True
            self.returncode = 0

        async def wait(self):
            return self.returncode

    process = Process()
    turn = {"process": process}
    core.active_turns[("alice", "session")] = turn
    try:
        assert asyncio.run(core.stop("alice", "session"))
        assert process.terminated
        assert ("alice", "session") not in core.active_turns
    finally:
        core.active_turns.clear()
