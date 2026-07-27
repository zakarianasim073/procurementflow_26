from __future__ import annotations

import asyncio
from typing import Any, Dict

import pytest

from app.agents.core.base import AgentResult, AgentStatus, BaseAgent


class RuntimeEchoAgent(BaseAgent):
    agent_id = "test-runtime-echo"
    agent_name = "Runtime Echo"
    timeout_seconds = 1

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        return AgentResult(status=AgentStatus.SUCCESS, output={"context": context})


class SlowAgent(RuntimeEchoAgent):
    agent_id = "test-runtime-slow"
    agent_name = "Runtime Slow"
    timeout_seconds = 0.01

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        await asyncio.sleep(1)
        return AgentResult(status=AgentStatus.SUCCESS)


@pytest.mark.asyncio
async def test_agent_run_merges_context_kwargs_and_sets_trace(monkeypatch):
    stored = []

    async def fake_store(self, result, session=None):
        stored.append(result)

    monkeypatch.setattr(BaseAgent, "store_result", fake_store)
    agent = RuntimeEchoAgent()

    result = await agent.run({"request_id": "req-1", "tender_id": "1302995"}, message="ok")

    assert result.status == AgentStatus.SUCCESS
    assert result.request_id == "req-1"
    assert result.tender_id == "1302995"
    assert result.output["context"]["message"] == "ok"
    assert result.output["context"]["_agent_id"] == agent.agent_id
    assert stored and stored[0] is result


@pytest.mark.asyncio
async def test_agent_run_timeout_records_failure_and_opens_circuit(monkeypatch):
    async def fake_store(self, result, session=None):
        return None

    monkeypatch.setattr(BaseAgent, "store_result", fake_store)
    agent = SlowAgent()

    for _ in range(agent._max_consecutive_failures):
        result = await agent.run({})
        assert result.status == AgentStatus.FAILED
        assert "Timeout after" in result.error

    result = await agent.run({})
    assert result.status == AgentStatus.FAILED
    assert "circuit breaker open" in result.error


@pytest.mark.asyncio
async def test_brain_helpers_are_safe_without_brain():
    agent = RuntimeEchoAgent()

    assert await agent.share_knowledge("test", tender_id="unknown", data={}) is None
    assert await agent.query_brain("test", tender_id="unknown") == []
    assert await agent.ask_agent("missing", "ping", {}) is None
