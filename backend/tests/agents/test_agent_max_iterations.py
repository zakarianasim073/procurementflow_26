"""W-007 — Agent max_iterations guard.

Criterion 4 / 8: an agent configured with `max_iterations=1` returns
AgentStatus.FAILED with error "Agent exceeded max_iterations". An agent is
allowed exactly `max_iterations` executions, then the next run fails.
"""
from __future__ import annotations

from typing import Any, Dict

import pytest

from app.agents.core.base import AgentResult, AgentStatus, BaseAgent


class _NoopStore:
    @staticmethod
    async def fake_store(self, result, session=None):
        return None


class OneIterationAgent(BaseAgent):
    agent_id = "test-maxiter-1"
    agent_name = "One Iteration"
    max_iterations = 1

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        return AgentResult(status=AgentStatus.SUCCESS, output={"ok": True})


class TwoIterationAgent(BaseAgent):
    agent_id = "test-maxiter-2"
    agent_name = "Two Iteration"
    max_iterations = 2

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        return AgentResult(status=AgentStatus.SUCCESS, output={"ok": True})


@pytest.mark.asyncio
async def test_agent_with_1_iteration_consistently_fails(monkeypatch):
    monkeypatch.setattr(BaseAgent, "store_result", _NoopStore.fake_store)
    agent = OneIterationAgent()

    result = await agent.run({})

    assert result.status == AgentStatus.FAILED
    assert "Agent exceeded max_iterations" in result.error


@pytest.mark.asyncio
async def test_agent_allows_up_to_max_iterations_then_fails(monkeypatch):
    monkeypatch.setattr(BaseAgent, "store_result", _NoopStore.fake_store)
    agent = TwoIterationAgent()

    first = await agent.run({})
    assert first.status == AgentStatus.SUCCESS

    second = await agent.run({})
    assert second.status == AgentStatus.FAILED
    assert "Agent exceeded max_iterations" in second.error
