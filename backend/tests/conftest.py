"""ProcureFlow test suite — fixtures and shared utilities."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import pytest_asyncio
import sqlalchemy as sa

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Establish deterministic settings before importing app.core.config. Explicit
# service URLs supplied by the isolated test runner remain authoritative.
os.environ["ENVIRONMENT"] = "test"
os.environ["ALLOWED_ORIGINS"] = '["http://testserver","http://localhost"]'
os.environ["PROCUREFLOW_START_AGENTS_ON_STARTUP"] = "0"
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:phase36_test@postgres:5432/procureflow_test",
)
os.environ.setdefault("REDIS_URL", "redis://:phase36_test@redis:6379/0")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("ANTHROPIC_API_KEY", "")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.celery_app import celery_app

celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)

# Exclude test_circuit_breaker.py from auto-discovery — its FailingAgent/
# RecoveringAgent test agents raise RuntimeError("boom") on every 5ms loop.
# Run manually: pytest tests/test_circuit_breaker.py
collect_ignore = ["test_circuit_breaker.py"]

from app.agents.core.brain import AgentBrain
from app.agents.core.base import BaseAgent, AgentResult, AgentStatus
from app.agents.registry import AgentRegistry


class MockAsyncSession:
    """In-memory async session for testing."""
    
    def __init__(self):
        self._data: List[Any] = []
    
    async def execute(self, query, params=None):
        class Result:
            def fetchall(self):
                return []
            def scalar_one_or_none(self):
                return None
            def scalars(self):
                class Scalars:
                    def first(self):
                        return None
                    def all(self):
                        return []
                return Scalars()
        return Result()
    
    async def commit(self):
        pass
    
    async def flush(self):
        pass
    
    async def rollback(self):
        pass
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass
    
    def add(self, obj):
        self._data.append(obj)


def mock_session_factory():
    """Return a factory that yields MockAsyncSession instances."""
    class Factory:
        async def __aenter__(self):
            return MockAsyncSession()
        async def __aexit__(self, *args):
            pass
    return Factory()


class EchoAgent(BaseAgent):
    """Test agent that echoes its input."""
    agent_id = "test-agent-echo"
    agent_name = "Echo Agent"
    description = "Echoes input for testing"
    version = "0.0.1"
    
    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            output={"echo": context.get("message", "")},
        )


class SquareAgent(BaseAgent):
    """Test agent that squares a number."""
    agent_id = "test-agent-square"
    agent_name = "Square Agent"
    description = "Squares numbers for testing"
    version = "0.0.1"
    
    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        n = context.get("number", 0)
        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            status=AgentStatus.SUCCESS,
            output={"result": n * n},
        )


class FailAgent(BaseAgent):
    """Test agent that always fails."""
    agent_id = "test-agent-fail"
    agent_name = "Fail Agent"
    description = "Always fails for testing"
    version = "0.0.1"
    
    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        raise RuntimeError("Intentional test failure")


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def event_loop():
    """Provide a fresh event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def client():
    """Session-scoped TestClient — single instance shared across all test files."""
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as tc:
        yield tc


@pytest_asyncio.fixture
async def brain():
    """Create a started AgentBrain with a mock DB session."""
    b = AgentBrain(db_session_factory=mock_session_factory)
    await b.start()
    yield b
    await b.stop()


@pytest_asyncio.fixture
async def registry(brain):
    """Create an AgentRegistry wired to the brain."""
    # Clear singleton state between tests
    AgentRegistry._instance = None
    r = AgentRegistry(brain=brain)
    yield r
    AgentRegistry._instance = None


@pytest_asyncio.fixture
async def echo_agent(brain):
    """Create an EchoAgent wired to the brain."""
    agent = EchoAgent(brain=brain)
    brain.register_agent(
        agent.agent_id, agent,
        name=agent.agent_name,
        description=agent.description,
        version=agent.version,
    )
    yield agent


@pytest_asyncio.fixture
async def square_agent(brain):
    """Create a SquareAgent wired to the brain."""
    agent = SquareAgent(brain=brain)
    brain.register_agent(
        agent.agent_id, agent,
        name=agent.agent_name,
        description=agent.description,
        version=agent.version,
    )
    yield agent


@pytest_asyncio.fixture
async def fail_agent(brain):
    """Create a FailAgent wired to the brain."""
    agent = FailAgent(brain=brain)
    brain.register_agent(
        agent.agent_id, agent,
        name=agent.agent_name,
        description=agent.description,
        version=agent.version,
    )
    yield agent


@pytest_asyncio.fixture
async def subscription_plan(db_session):
    """Minimal SubscriptionPlan row required by ClientSubscription FK."""
    import uuid as _uuid
    from app.models.subscription import SubscriptionPlan
    plan = SubscriptionPlan(
        id=str(_uuid.uuid4()),
        name="test-free",
        monthly_tender_limit=100,
        monthly_price_bdt=0,
        features={},
        is_active=True,
    )
    db_session.add(plan)
    await db_session.flush()
    return plan


@pytest_asyncio.fixture
async def db_session():
    """Real, transaction-isolated async DB session for integration tests.

    The session joins the connection's transaction via savepoints
    (``join_transaction_mode="create_savepoint"``), so the service's own
    ``session.commit()`` only releases a savepoint and the outer transaction is
    rolled back on teardown — no rows leak between tests. Requires the
    application's migrations to be applied (alembic upgrade head).
    """
    engine = create_async_engine(settings.DATABASE_URL, future=True, pool_pre_ping=True)
    connection = await engine.connect()
    await connection.begin()
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()
        await connection.rollback()
        await connection.close()
        await engine.dispose()
