"""W-007 — IntelligencePipeline per-stage timeout enforcement.

Criterion 5: a pipeline stage that exceeds its `timeout` is skipped (logged,
not failed) and the pipeline continues to subsequent stages.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict

import pytest

from app.agents.core.base import AgentResult, AgentStatus, BaseAgent
from app.agents.core.pipeline import IntelligencePipeline, PipelineStage


class _NoopStore:
    @staticmethod
    async def fake_store(self, result, session=None):
        return None


class StalledAgent(BaseAgent):
    """Agent whose execute() runs far longer than the stage timeout."""

    agent_id = "test-pipeline-stall"
    agent_name = "Pipeline Stall"
    timeout_seconds = 120  # own budget is generous; stage budget is the binding one

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        await asyncio.sleep(10)
        return AgentResult(status=AgentStatus.SUCCESS)


class FastAgent(BaseAgent):
    agent_id = "test-pipeline-fast"
    agent_name = "Pipeline Fast"

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        return AgentResult(status=AgentStatus.SUCCESS, output={"done": True})


class FakeBrain:
    """Duck-typed brain: returns the registered agent and records broadcasts."""

    def __init__(self, agent: BaseAgent):
        self._agent = agent
        self.broadcasts: list = []

    def get_agent(self, agent_id: str) -> BaseAgent:
        return self._agent

    async def broadcast(self, **kwargs: Any) -> None:
        self.broadcasts.append(kwargs)


@pytest.mark.asyncio
async def test_pipeline_stage_timeout_is_skipped_gracefully(monkeypatch):
    monkeypatch.setattr(BaseAgent, "store_result", _NoopStore.fake_store)

    brain = FakeBrain(StalledAgent())
    pipeline = IntelligencePipeline(brain)
    pipeline.PIPELINE = [PipelineStage(agent_id="test-pipeline-stall", timeout=0.05)]

    result = await pipeline.run({"tender_id": "1302995"})

    stage = result["test-pipeline-stall"]
    assert stage["status"] == "skipped"
    assert "timed out" in stage["error"].lower()
    assert "pipeline_complete" in result


@pytest.mark.asyncio
async def test_pipeline_continues_after_skipped_stage(monkeypatch):
    monkeypatch.setattr(BaseAgent, "store_result", _NoopStore.fake_store)

    brain = FakeBrain(StalledAgent())
    pipeline = IntelligencePipeline(brain)
    # Slow stage first, then a fast stage that must still run.
    pipeline.PIPELINE = [
        PipelineStage(agent_id="test-pipeline-stall", timeout=0.05),
        PipelineStage(agent_id="test-pipeline-fast", timeout=5),
    ]
    # The fast stage is served by a different agent — swap get_agent to route ids.
    brain._agents = {
        "test-pipeline-stall": StalledAgent(),
        "test-pipeline-fast": FastAgent(),
    }

    def get_agent(agent_id: str):
        return brain._agents[agent_id]

    brain.get_agent = get_agent  # type: ignore[assignment]

    result = await pipeline.run({"tender_id": "1302995"})

    assert result["test-pipeline-stall"]["status"] == "skipped"
    assert result["test-pipeline-fast"]["status"] == "success"
