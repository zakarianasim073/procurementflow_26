"""W-007 — Brain message consumer per-message timeout.

Criterion 6: a message whose handler exceeds the processing timeout is logged
and dropped, while the consumer keeps running and processes subsequent
messages (does not crash or stall the bus).
"""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.agents.core.brain import AgentBrain, BrainMessage


class _MockSession:
    async def execute(self, *args, **kwargs):
        class _R:
            def fetchall(self):
                return []
        return _R()

    async def commit(self):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _mock_session_factory():
    class _Factory:
        async def __aenter__(self):
            return _MockSession()

        async def __aexit__(self, *exc):
            return False
    return _Factory()


@pytest.mark.asyncio
async def test_brain_message_exceeding_timeout_is_skipped(monkeypatch):
    # The brain bootstraps project memory on init; avoid that infra in tests.
    from app.services.project_memory import project_memory_service
    monkeypatch.setattr(project_memory_service, "bootstrap_project_context", lambda: None)

    brain = AgentBrain(db_session_factory=_mock_session_factory)
    brain._running = True

    started_slow = asyncio.Event()
    fast_done = asyncio.Event()

    async def slow_handler(msg: BrainMessage) -> dict:
        started_slow.set()
        await asyncio.sleep(5)  # far longer than the 0.2s test budget
        return {}

    async def fast_handler(msg: BrainMessage) -> dict:
        fast_done.set()
        return {}

    brain._message_handlers["slow-agent"] = slow_handler
    brain._message_handlers["fast-agent"] = fast_handler

    await brain._message_queue.put(BrainMessage(id="slow-1", recipient_id="slow-agent", body={}))
    await brain._message_queue.put(BrainMessage(id="fast-1", recipient_id="fast-agent", body={}))

    # Shorten the per-message budget for a fast test.
    brain.MESSAGE_PROCESSING_TIMEOUT_SECONDS = 0.2

    task = asyncio.create_task(brain._process_messages())
    try:
        # The slow handler must have started, and the fast one must still run
        # after the slow message was dropped — proving the consumer continued.
        await asyncio.wait_for(
            asyncio.gather(started_slow.wait(), fast_done.wait()),
            timeout=3.0,
        )
    finally:
        brain._running = False
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    assert started_slow.is_set()
    assert fast_done.is_set()
