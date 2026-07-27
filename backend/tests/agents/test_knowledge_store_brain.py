"""W-009 (ADR-001): AgentBrain wiring of the Redis-backed knowledge store.

Validates that:
  * query_knowledge serves entries from the Redis-backed cache (criterion 1),
  * when the cache is empty/failed it falls back to PostgreSQL (criterion 3),
  * invalidate_knowledge delegates to the store (criterion 6).
"""
from __future__ import annotations

import asyncio

import pytest

from app.agents.core.brain import (
    AgentBrain,
    RedisKnowledgeStore,
    _FailingBackend,
    _MemoryBackend,
)
from app.services.project_memory import project_memory_service


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _MockSession:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, *a, **k):
        return _Result(self._rows)

    async def commit(self):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _session_factory(rows):
    """Return a zero-arg factory (compatible with AgentBrain.db()) yielding a
    session that returns the given rows for any execute()."""
    class _Factory:
        async def __aenter__(self):
            return _MockSession(rows)

        async def __aexit__(self, *exc):
            return False

    return _Factory


def _pg_row(entry_id, entry_type, tender_id, created="2024-01-01"):
    return (
        entry_id,
        entry_type,
        tender_id,
        {"payload": {"k": entry_id}, "summary": "s", "tags": [], "source": "agent-x"},
        created,
    )


def _entry_dict(entry_id, entry_type="tender_document", tender_id="T1"):
    return {
        "entry_id": entry_id,
        "entry_type": entry_type,
        "tender_id": tender_id,
        "data": {},
        "summary": "s",
        "tags": [],
        "agent_id": "agent-x",
    }


async def _noop_upsert(**kwargs):
    return None


@pytest.fixture
def patched_brain(monkeypatch):
    monkeypatch.setattr(project_memory_service, "bootstrap_project_context", lambda: None)
    monkeypatch.setattr(project_memory_service, "upsert_async", _noop_upsert)
    yield


@pytest.mark.asyncio
async def test_brain_query_serves_redis_cache(monkeypatch, patched_brain):
    brain = AgentBrain(db_session_factory=_session_factory([]))  # PG warm empty
    brain._knowledge_cache_loaded = False
    brain._knowledge_store = RedisKnowledgeStore(redis_client=_MemoryBackend())
    await brain._knowledge_store.set(
        "e1", _entry_dict("e1", "tender_document", "T1"), "tender_document", "T1"
    )

    results = await brain.query_knowledge(entry_type="tender_document", tender_id="T1")
    assert any(e["entry_id"] == "e1" for e in results)


@pytest.mark.asyncio
async def test_brain_query_falls_back_to_postgres(monkeypatch, patched_brain):
    brain = AgentBrain(
        db_session_factory=_session_factory([_pg_row("p1", "tender_document", "T1")])
    )
    brain._knowledge_cache_loaded = False
    # Degraded store → cache empty → must read PostgreSQL.
    brain._knowledge_store = RedisKnowledgeStore(redis_client=_FailingBackend())

    results = await brain.query_knowledge(entry_type="tender_document", tender_id="T1")
    assert any(e["entry_id"] == "p1" for e in results)


@pytest.mark.asyncio
async def test_brain_invalidate_delegates_to_store(monkeypatch, patched_brain):
    store = RedisKnowledgeStore(redis_client=_MemoryBackend())
    await store.set(
        "e1", _entry_dict("e1", "tender_document", "T1"), "tender_document", "T1"
    )
    brain = AgentBrain(db_session_factory=_session_factory([]))
    brain._knowledge_store = store

    await brain.invalidate_knowledge(entry_type="tender_document", tender_id="T1")
    assert await store.get("e1", "tender_document", "T1") is None
