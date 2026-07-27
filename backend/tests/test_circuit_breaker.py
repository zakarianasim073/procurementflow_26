"""Circuit breaker tests for BaseAgent.

Verifies the three-state circuit breaker: closed → open → half-open → closed.
"""
from __future__ import annotations

import asyncio
import time
import pytest
from app.agents.core.base import BaseAgent, AgentResult, AgentStatus


class FailingAgent(BaseAgent):
    """Agent that always fails."""
    agent_id = "test-failing"
    agent_name = "Failing Agent"

    async def execute(self, context):
        raise RuntimeError("boom")


class RecoveringAgent(BaseAgent):
    """Agent that fails N times then succeeds."""
    agent_id = "test-recovering"
    agent_name = "Recovering Agent"
    _fail_count = 0
    _fail_until = 2

    async def execute(self, context):
        self._fail_count += 1
        if self._fail_count <= self._fail_until:
            raise RuntimeError(f"fail #{self._fail_count}")
        return AgentResult(status=AgentStatus.SUCCESS, output={"recovered": True})


class SuccessAgent(BaseAgent):
    """Agent that always succeeds."""
    agent_id = "test-success"
    agent_name = "Success Agent"

    async def execute(self, context):
        return AgentResult(status=AgentStatus.SUCCESS, output={"ok": True})


class TestCircuitBreakerClosed:
    """Tests for the closed (normal) state."""

    def test_starts_closed(self):
        agent = SuccessAgent()
        assert agent.circuit_breaker_state == "closed"
        assert agent._consecutive_failures == 0

    def test_success_keeps_closed(self):
        agent = SuccessAgent()
        asyncio.get_event_loop().run_until_complete(agent.run({}))
        assert agent.circuit_breaker_state == "closed"

    def test_single_failure_stays_closed(self):
        agent = FailingAgent()
        agent._max_consecutive_failures = 3
        asyncio.get_event_loop().run_until_complete(agent.run({}))
        assert agent.circuit_breaker_state == "closed"
        assert agent._consecutive_failures == 1


class TestCircuitBreakerOpen:
    """Tests for the open (tripped) state."""

    def test_opens_after_max_failures(self):
        agent = FailingAgent()
        agent._max_consecutive_failures = 3
        for _ in range(3):
            asyncio.get_event_loop().run_until_complete(agent.run({}))
        assert agent.circuit_breaker_state == "open"
        assert agent._consecutive_failures == 3

    def test_open_circuit_rejects_execution(self):
        agent = FailingAgent()
        agent._max_consecutive_failures = 2
        for _ in range(2):
            asyncio.get_event_loop().run_until_complete(agent.run({}))
        # Next call should be rejected
        result = asyncio.get_event_loop().run_until_complete(agent.run({}))
        assert result.status == AgentStatus.FAILED
        assert "circuit breaker open" in result.error.lower()

    def test_success_resets_failure_count(self):
        agent = RecoveringAgent()
        agent._max_consecutive_failures = 10
        # Fail twice
        for _ in range(2):
            asyncio.get_event_loop().run_until_complete(agent.run({}))
        assert agent._consecutive_failures == 2
        # Succeed — should reset
        asyncio.get_event_loop().run_until_complete(agent.run({}))
        assert agent._consecutive_failures == 0
        assert agent.circuit_breaker_state == "closed"


class TestCircuitBreakerHalfOpen:
    """Tests for the half-open (recovery) state."""

    def test_enters_half_open_after_cooldown(self):
        agent = FailingAgent()
        agent._max_consecutive_failures = 2
        agent._circuit_cooldown_seconds = 1  # 1 second cooldown
        for _ in range(2):
            asyncio.get_event_loop().run_until_complete(agent.run({}))
        assert agent.circuit_breaker_state == "open"
        # Wait for cooldown
        time.sleep(1.1)
        assert agent.circuit_breaker_state == "half-open"

    def test_half_open_allows_trial_execution(self):
        agent = RecoveringAgent()
        agent._max_consecutive_failures = 2
        agent._circuit_cooldown_seconds = 1
        agent._fail_until = 2  # Fail first 2 times
        for _ in range(2):
            asyncio.get_event_loop().run_until_complete(agent.run({}))
        assert agent.circuit_breaker_state == "open"
        time.sleep(1.1)
        assert agent.circuit_breaker_state == "half-open"
        # Trial execution should succeed (agent has recovered)
        result = asyncio.get_event_loop().run_until_complete(agent.run({}))
        assert result.status == AgentStatus.SUCCESS
        assert agent.circuit_breaker_state == "closed"

    def test_half_open_failure_restarts_cooldown(self):
        agent = FailingAgent()
        agent._max_consecutive_failures = 2
        agent._circuit_cooldown_seconds = 1
        for _ in range(2):
            asyncio.get_event_loop().run_until_complete(agent.run({}))
        time.sleep(1.1)
        assert agent.circuit_breaker_state == "half-open"
        # Trial execution fails — should restart cooldown
        asyncio.get_event_loop().run_until_complete(agent.run({}))
        assert agent.circuit_breaker_state == "open"
        assert agent._circuit_open_since is not None

    def test_remaining_seconds_during_open(self):
        agent = FailingAgent()
        agent._max_consecutive_failures = 1
        agent._circuit_cooldown_seconds = 10
        asyncio.get_event_loop().run_until_complete(agent.run({}))
        # Should show remaining seconds in error
        result = asyncio.get_event_loop().run_until_complete(agent.run({}))
        assert result.status == AgentStatus.FAILED
        assert "retry in" in result.error.lower()


class TestCircuitBreakerManualReset:
    """Tests for manual reset."""

    def test_manual_reset(self):
        agent = FailingAgent()
        agent._max_consecutive_failures = 2
        for _ in range(2):
            asyncio.get_event_loop().run_until_complete(agent.run({}))
        assert agent.circuit_breaker_state == "open"
        agent.reset_circuit_breaker()
        assert agent.circuit_breaker_state == "closed"
        assert agent._consecutive_failures == 0

    def test_manual_reset_clears_open_since(self):
        agent = FailingAgent()
        agent._max_consecutive_failures = 1
        asyncio.get_event_loop().run_until_complete(agent.run({}))
        assert agent._circuit_open_since is not None
        agent.reset_circuit_breaker()
        assert agent._circuit_open_since is None


class TestCircuitBreakerAPI:
    """Tests for the circuit breaker API endpoints."""

    @pytest.fixture(autouse=True)
    def setup_client(self, client):
        self.client = client

    @pytest.fixture
    def auth_headers(self):
        from app.core.security import create_token
        token = create_token("test-admin")
        return {"Authorization": f"Bearer {token}"}

    def test_circuit_breaker_status_endpoint(self, auth_headers):
        r = self.client.get("/api/circuit-breaker/status", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "agents" in body
        assert isinstance(body["agents"], list)

    def test_circuit_breaker_reset_all(self, auth_headers):
        r = self.client.post("/api/circuit-breaker/reset", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "reset" in body
        assert isinstance(body["reset"], list)

    def test_circuit_breaker_reset_specific_agent(self, auth_headers):
        r = self.client.post("/api/circuit-breaker/reset", params={"agent_id": "agent-027-orchestrator"}, headers=auth_headers)
        assert r.status_code in (200, 404)

    def test_circuit_breaker_reset_nonexistent_agent(self, auth_headers):
        r = self.client.post("/api/circuit-breaker/reset", params={"agent_id": "nonexistent"}, headers=auth_headers)
        assert r.status_code == 404
