"""W-007 — Agent execution timeout enforcement.

Criterion 3 / 7: an agent whose `execute()` exceeds `timeout_seconds`
returns AgentStatus.FAILED with error "Agent timed out after Ns".
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict

import pytest

from app.agents.core.base import AgentResult, AgentStatus, BaseAgent


class _NoopStore:
    @staticmethod
    async def fake_store(self, result, session=None):
        return None


class MillisecondTimeoutAgent(BaseAgent):
    agent_id = "test-timeout-ms"
    agent_name = "MS Timeout"
    timeout_seconds = 0.001  # 1ms — will always exceed

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        await asyncio.sleep(5)
        return AgentResult(status=AgentStatus.SUCCESS)


@pytest.mark.asyncio
async def test_agent_with_1ms_timeout_returns_failed(monkeypatch):
    monkeypatch.setattr(BaseAgent, "store_result", _NoopStore.fake_store)
    agent = MillisecondTimeoutAgent()

    result = await agent.run({})

    assert result.status == AgentStatus.FAILED
    assert "Agent timed out after" in result.error


@pytest.mark.asyncio
async def test_agent_timeout_records_failure_and_opens_circuit(monkeypatch):
    monkeypatch.setattr(BaseAgent, "store_result", _NoopStore.fake_store)
    agent = MillisecondTimeoutAgent()

    for _ in range(agent._max_consecutive_failures):
        result = await agent.run({})
        assert result.status == AgentStatus.FAILED
        assert "Agent timed out after" in result.error

    result = await agent.run({})
    assert result.status == AgentStatus.FAILED
    assert "circuit breaker open" in result.error
