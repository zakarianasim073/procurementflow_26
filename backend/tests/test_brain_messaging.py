"""Tests for AgentBrain messaging, registration, and knowledge systems."""
from __future__ import annotations

import asyncio
from typing import Dict, Any

import pytest

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from app.agents.core.brain import AgentBrain, BrainMessage, MessageType
from app.agents.registry import AgentRegistry

from conftest import EchoAgent


# ── Brain Lifecycle Tests ───────────────────────────────────────────────

class TestBrainLifecycle:
    
    async def test_brain_starts_and_stops(self, brain):
        """Brain should be running after start() and not after stop()."""
        assert brain._running is True
        assert brain._processing_task is not None
        assert brain._idle_task is not None
        
        await brain.stop()
        assert brain._running is False
        assert brain._processing_task is None
        assert brain._idle_task is None
    
    async def test_brain_double_start_is_safe(self, brain):
        """Calling start() twice should be a no-op."""
        original_task = brain._processing_task
        await brain.start()
        assert brain._processing_task is original_task
        assert brain._running is True
    
    async def test_brain_stats_empty(self, brain):
        """Fresh brain should report zero agents.

        T-032: start() fires ensure_knowledge_loaded() as a background task so
        knowledge_cache_loaded becomes True shortly after start — the assertion
        checks for the boolean key presence rather than the specific value.
        """
        stats = brain.get_stats()
        assert stats["registered_agents"] == 0
        assert stats["active_handlers"] == 0
        assert stats["knowledge_entries"] == 0
        assert isinstance(stats["knowledge_cache_loaded"], bool)
        # T-032 stats fields
        assert "cache_has_redis" in stats
        assert "cache_degraded" in stats
        assert "cache_l1_size" in stats


# ── Agent Registration Tests ──────────────────────────────────────────

class TestAgentRegistration:
    
    async def test_register_agent(self, brain, echo_agent):
        """Agent should be registered and retrievable."""
        retrieved = brain.get_agent("test-agent-echo")
        assert retrieved is echo_agent
        
        cap = brain.get_capability("test-agent-echo")
        assert cap is not None
        assert cap.agent_name == "Echo Agent"
        assert cap.version == "0.0.1"
    
    async def test_list_agents(self, brain, echo_agent, square_agent):
        """list_agents should return all registered capabilities."""
        agents = brain.list_agents()
        assert len(agents) == 2
        ids = {a.agent_id for a in agents}
        assert ids == {"test-agent-echo", "test-agent-square"}
    
    async def test_find_agents_by_capability(self, brain, echo_agent):
        """find_agents_by_capability should match query types."""
        brain.register_agent(
            "test-capable", echo_agent,
            name="Capable", description="Has query types",
            can_query=["tender_lookup", "boq_analysis"],
        )
        matches = brain.find_agents_by_capability("tender_lookup")
        assert len(matches) == 1
        assert matches[0].agent_id == "test-capable"


# ── Registry ↔ Brain Delegation Tests ─────────────────────────────────

class TestRegistryBrainDelegation:
    
    async def test_registry_delegates_register_to_brain(self, registry, brain, echo_agent):
        """AgentRegistry.register should register into brain."""
        registry.register(echo_agent)
        assert brain.get_agent("test-agent-echo") is echo_agent
        assert len(brain.list_agents()) == 1
    
    async def test_registry_get_delegates_to_brain(self, registry, brain, echo_agent):
        """AgentRegistry.get should retrieve from brain."""
        brain.register_agent(echo_agent.agent_id, echo_agent, name=echo_agent.agent_name)
        retrieved = registry.get("test-agent-echo")
        assert retrieved is echo_agent
    
    async def test_registry_list_delegates_to_brain(self, registry, brain, echo_agent):
        """AgentRegistry.list_agents should return brain agents."""
        brain.register_agent(echo_agent.agent_id, echo_agent, name=echo_agent.agent_name)
        agents = registry.list_agents()
        assert len(agents) == 1
        assert agents[0]["agent_id"] == "test-agent-echo"
    
    async def test_registry_count_delegates_to_brain(self, registry, brain, echo_agent, square_agent):
        """AgentRegistry.count should reflect brain agent count."""
        brain.register_agent(echo_agent.agent_id, echo_agent, name=echo_agent.agent_name)
        brain.register_agent(square_agent.agent_id, square_agent, name=square_agent.agent_name)
        assert registry.count == 2
    
    async def test_registry_without_brain_uses_internal_dict(self):
        """Registry without brain should fall back to internal dict."""
        AgentRegistry._instance = None
        r = AgentRegistry()
        agent = EchoAgent()
        r.register(agent)
        assert r.get("test-agent-echo") is agent
        assert r.count == 1
        AgentRegistry._instance = None


# ── Inter-Agent Messaging Tests ─────────────────────────────────────────

class TestInterAgentMessaging:
    
    async def test_ask_agent_delivers_message(self, brain, echo_agent, square_agent):
        """ask_agent should send a request and receive a response."""
        result = await echo_agent.ask_agent(
            recipient_id="test-agent-square",
            subject="square_test",
            body={"number": 7},
        )
        assert result is not None
        assert isinstance(result, dict)
        assert result.get("result") == 49
    
    async def test_ask_agent_unknown_recipient_returns_error(self, brain, echo_agent):
        """ask_agent to unknown agent should return error."""
        result = await echo_agent.ask_agent(
            recipient_id="nonexistent-agent",
            subject="test",
            body={},
        )
        assert result is not None
        assert "error" in result
    
    async def test_ask_agent_without_brain_raises(self):
        """ask_agent without brain should raise RuntimeError."""
        agent = EchoAgent(brain=None)
        with pytest.raises(RuntimeError, match="no AgentBrain connected"):
            await agent.ask_agent("test-agent-square", "test", {})
    
    async def test_share_knowledge_without_brain_raises(self):
        """share_knowledge without brain should raise RuntimeError."""
        agent = EchoAgent(brain=None)
        with pytest.raises(RuntimeError, match="no AgentBrain connected"):
            await agent.share_knowledge("test_entry", data={"key": "value"})
    
    async def test_query_brain_without_brain_raises(self):
        """query_brain without brain should raise RuntimeError."""
        agent = EchoAgent(brain=None)
        with pytest.raises(RuntimeError, match="no AgentBrain connected"):
            await agent.query_brain("test_entry")


# ── Knowledge Store Tests ───────────────────────────────────────────────

class TestKnowledgeStore:
    
    async def test_store_and_query_knowledge(self, brain, echo_agent):
        """store_knowledge should create retrievable entries."""
        entry_id = await brain.store_knowledge(
            agent_id="test-agent-echo",
            entry_type="boq_text",
            tender_id="TENDER-123",
            data={"items": [{"code": "40-200-00", "qty": 100}]},
            summary="Test BOQ",
            tags=["test", "boq"],
        )
        assert entry_id is not None
        assert len(entry_id) > 0
        
        # Query by entry_type
        results = await brain.query_knowledge(entry_type="boq_text")
        assert len(results) >= 1
    
    async def test_agent_share_knowledge(self, brain, echo_agent):
        """Agent.share_knowledge should delegate to brain."""
        echo_agent.brain = brain
        entry_id = await echo_agent.share_knowledge(
            entry_type="tds_text",
            tender_id="TENDER-456",
            data={"criteria": {"experience": 5}},
            summary="Test TDS",
        )
        assert entry_id is not None
    
    async def test_knowledge_cache_loaded(self, brain):
        """ensure_knowledge_loaded should set cache flag."""
        await brain.ensure_knowledge_loaded(limit=10)
        assert brain._knowledge_cache_loaded is True


# ── Pipeline Tests ──────────────────────────────────────────────────────

class TestPipelineExecution:
    
    async def test_run_pipeline_single_agent(self, registry, brain, echo_agent):
        """Pipeline with one agent should execute successfully."""
        registry.register(echo_agent)
        results = await registry.run_pipeline(
            ["test-agent-echo"],
            {"message": "hello"},
        )
        assert "test-agent-echo" in results
        assert results["test-agent-echo"].status == AgentStatus.SUCCESS
        assert results["test-agent-echo"].output["echo"] == "hello"
    
    async def test_run_pipeline_with_dependencies(self, registry, brain, echo_agent, square_agent):
        """Pipeline with dependency chain should resolve correctly."""
        # Make echo depend on square
        echo_agent.dependencies = ["test-agent-square"]
        
        registry.register(square_agent)
        registry.register(echo_agent)
        
        results = await registry.run_pipeline(
            ["test-agent-square", "test-agent-echo"],
            {"number": 5, "message": "world"},
        )
        
        assert results["test-agent-square"].status == AgentStatus.SUCCESS
        assert results["test-agent-square"].output["result"] == 25
        assert results["test-agent-echo"].status == AgentStatus.SUCCESS
        assert results["test-agent-echo"].output["echo"] == "world"
    
    async def test_run_pipeline_failure_stops(self, registry, brain, square_agent, fail_agent):
        """Pipeline should stop on failure when stop_on_failure=True."""
        fail_agent.dependencies = ["test-agent-square"]
        
        registry.register(square_agent)
        registry.register(fail_agent)
        
        results = await registry.run_pipeline(
            ["test-agent-square", "test-agent-fail"],
            {"number": 3},
            stop_on_failure=True,
        )
        
        assert results["test-agent-square"].status == AgentStatus.SUCCESS
        assert results["test-agent-fail"].status == AgentStatus.FAILED
    
    async def test_run_pipeline_failure_continues(self, registry, brain, square_agent, fail_agent):
        """Pipeline should continue on failure when stop_on_failure=False."""
        registry.register(square_agent)
        registry.register(fail_agent)
        
        results = await registry.run_pipeline(
            ["test-agent-square", "test-agent-fail"],
            {"number": 3},
            stop_on_failure=False,
        )
        
        assert results["test-agent-square"].status == AgentStatus.SUCCESS
        assert results["test-agent-fail"].status == AgentStatus.FAILED


# ── Message Bus Tests ───────────────────────────────────────────────────

class TestMessageBus:
    
    async def test_send_message_queues(self, brain):
        """send_message should add to queue."""
        msg = BrainMessage(
            sender_id="test-sender",
            recipient_id="test-recipient",
            message_type=MessageType.REQUEST,
            subject="test",
            body={"key": "value"},
        )
        result = await brain.send_message(msg)
        assert result is True
        assert brain._message_queue.qsize() == 1
    
    async def test_broadcast(self, brain, echo_agent, square_agent):
        """broadcast should send to all agents except sender."""
        delivered = await brain.broadcast(
            sender_id="system",
            subject="alert",
            body={"level": "info"},
        )
        assert len(delivered) == 2
        assert "test-agent-echo" in delivered
        assert "test-agent-square" in delivered
    
    async def test_request_with_response(self, brain, echo_agent, square_agent):
        """request should call handler and return response."""
        result = await brain.request(
            sender_id="test-agent-echo",
            recipient_id="test-agent-square",
            subject="compute",
            body={"number": 4},
        )
        assert result is not None
        assert isinstance(result, dict)
        assert result.get("result") == 16


# ── Workflow Orchestration Tests ──────────────────────────────────────

class TestWorkflowOrchestration:
    
    async def test_run_workflow(self, brain, echo_agent, square_agent):
        """run_workflow should execute steps in order."""
        workflow = [
            {"agent_id": "test-agent-echo", "input": {"message": "step1"}},
            {"agent_id": "test-agent-square", "input": {"number": 3}},
        ]
        results = await brain.run_workflow(workflow)
        
        assert "test-agent-echo" in results
        assert "test-agent-square" in results
        assert results["test-agent-echo"].output["echo"] == "step1"
        assert results["test-agent-square"].output["result"] == 9
    
    async def test_run_workflow_with_dependency(self, brain, echo_agent, square_agent):
        """run_workflow should check dependencies."""
        workflow = [
            {"agent_id": "test-agent-echo", "input": {"message": "first"}},
            {"agent_id": "test-agent-square", "input": {"number": 2}, "depends_on": ["test-agent-echo"]},
        ]
        results = await brain.run_workflow(workflow)
        
        assert "test-agent-echo" in results
        assert "test-agent-square" in results
        assert results["test-agent-square"].output["result"] == 4


# ── System Memory Tests ─────────────────────────────────────────────────

class TestSystemMemory:
    
    async def test_system_memory(self, brain, echo_agent):
        """get_system_memory should return brain stats."""
        memory = await brain.get_system_memory()
        assert memory["agent_count"] == 1
        assert memory["uptime"] == "active"
        assert len(memory["agents"]) == 1
        assert memory["agents"][0]["id"] == "test-agent-echo"
