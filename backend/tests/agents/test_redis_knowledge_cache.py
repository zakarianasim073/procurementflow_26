"""T-032 (ENT-04b): Redis-shared brain knowledge cache.

Acceptance criteria:
  * Two API replicas sharing the same Redis backend see identical knowledge
    query results (cross-replica sharing).
  * Startup warm-up from PostgreSQL populates the store immediately after start().
  * L1 in-process layer evicts entries once their TTL expires.
  * get_stats() exposes Redis connectivity fields so ops can observe cache health.
  * Degraded path: Redis failure falls through to PostgreSQL without crashing.
"""
from __future__ import annotations

import asyncio
import time

import pytest

from app.agents.core.brain import (
    AgentBrain,
    RedisKnowledgeStore,
    _FailingBackend,
    _MemoryBackend,
)
from app.services.project_memory import project_memory_service


# ── helpers ────────────────────────────────────────────────────────────────────

def _entry(entry_id: str, entry_type: str = "tender_document", tender_id: str = "T1"):
    return {
        "entry_id": entry_id,
        "entry_type": entry_type,
        "tender_id": tender_id,
        "data": {"v": entry_id},
        "summary": "s",
        "tags": [],
        "agent_id": "agent-test",
    }


def _pg_row(entry_id, entry_type="tender_document", tender_id="T1"):
    return (
        entry_id,
        entry_type,
        tender_id,
        {
            "payload": {"v": entry_id},
            "summary": "s",
            "tags": [],
            "source": "agent-test",
        },
        "2024-01-01",
    )


class _MockSession:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, *a, **k):
        class _R:
            def __init__(self, rows):
                self._rows = rows
            def fetchall(self):
                return self._rows
        return _R(self._rows)

    async def commit(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _db_factory(rows):
    class _Ctx:
        async def __aenter__(self):
            return _MockSession(rows)
        async def __aexit__(self, *exc):
            return False
    return _Ctx


async def _noop_upsert(**kw):
    return None


@pytest.fixture(autouse=True)
def _patch_project_memory(monkeypatch):
    monkeypatch.setattr(project_memory_service, "bootstrap_project_context", lambda: None)
    monkeypatch.setattr(project_memory_service, "upsert_async", _noop_upsert)
    monkeypatch.setattr(project_memory_service, "search_async", lambda *a, **k: [])


# ── T-032 criterion 1: cross-replica sharing ──────────────────────────────────

@pytest.mark.asyncio
async def test_two_replicas_share_cache():
    """Writes from replica A are immediately visible to replica B via shared backend."""
    shared_backend = _MemoryBackend()

    store_a = RedisKnowledgeStore(redis_client=shared_backend)
    store_b = RedisKnowledgeStore(redis_client=shared_backend)

    # Replica A writes an entry.
    await store_a.set("e1", _entry("e1"), "tender_document", "T1")

    # Replica B reads without any explicit sync.
    result = await store_b.get("e1", "tender_document", "T1")
    assert result is not None
    assert result["entry_id"] == "e1"


@pytest.mark.asyncio
async def test_replica_invalidation_propagates():
    """Invalidation from replica A removes entry from replica B's reads."""
    shared_backend = _MemoryBackend()

    store_a = RedisKnowledgeStore(redis_client=shared_backend)
    store_b = RedisKnowledgeStore(redis_client=shared_backend)

    await store_a.set("e2", _entry("e2"), "tender_document", "T2")
    # Verify B sees it before invalidation.
    assert await store_b.get("e2", "tender_document", "T2") is not None

    # A invalidates; B's L1 has a separate TTL path but a cache miss on next
    # Redis read still returns None for the deleted key.
    await store_a.invalidate("tender_document", "T2")
    # Store B's L1 might cache for up to l1_ttl ms. Skip L1 by creating a fresh
    # store_b instance (simulates a different replica that hasn't cached locally).
    store_b2 = RedisKnowledgeStore(redis_client=shared_backend)
    assert await store_b2.get("e2", "tender_document", "T2") is None


@pytest.mark.asyncio
async def test_replica_query_returns_all_entries_from_shared_backend():
    """query() on replica B returns entries written by replica A."""
    shared_backend = _MemoryBackend()

    store_a = RedisKnowledgeStore(redis_client=shared_backend)
    store_b = RedisKnowledgeStore(redis_client=shared_backend)

    for i in range(3):
        await store_a.set(f"e{i}", _entry(f"e{i}", tender_id="TX"), "tender_document", "TX")

    results = await store_b.query(entry_type="tender_document", tender_id="TX")
    assert len(results) == 3


# ── T-032 criterion 2: startup warm-up ────────────────────────────────────────

@pytest.mark.asyncio
async def test_startup_warmup_hydrates_from_postgres():
    """ensure_knowledge_loaded() populates the Redis store from PG rows."""
    rows = [_pg_row("pg1", "tender_document", "T3")]
    brain = AgentBrain(db_session_factory=_db_factory(rows))
    brain._knowledge_cache_loaded = False
    shared_backend = _MemoryBackend()
    brain._knowledge_store = RedisKnowledgeStore(redis_client=shared_backend)

    await brain.ensure_knowledge_loaded()

    # Entry pg1 is now in the shared backend.
    result = await brain._knowledge_store.get("pg1", "tender_document", "T3")
    assert result is not None
    assert result["entry_id"] == "pg1"


@pytest.mark.asyncio
async def test_ensure_knowledge_loaded_idempotent():
    """Second call to ensure_knowledge_loaded is a no-op (flag already set)."""
    call_count = {"n": 0}

    class _CountingSession(_MockSession):
        async def execute(self, *a, **k):
            call_count["n"] += 1
            return await super().execute(*a, **k)

    class _Ctx:
        async def __aenter__(self):
            return _CountingSession([_pg_row("p1")])
        async def __aexit__(self, *exc):
            return False

    brain = AgentBrain(db_session_factory=_Ctx)
    # First call populates cache.
    await brain.ensure_knowledge_loaded()
    first = call_count["n"]
    # Second call should be skipped entirely (flag is True).
    await brain.ensure_knowledge_loaded()
    assert call_count["n"] == first  # no extra DB queries


# ── T-032 criterion 3: L1 TTL eviction ────────────────────────────────────────

@pytest.mark.asyncio
async def test_l1_ttl_eviction():
    """An L1 entry with a sub-millisecond TTL is gone on the next read."""

    class _Settings:
        KNOWLEDGE_CACHE_L1_TTL_MS = 1  # 1 ms
        KNOWLEDGE_CACHE_L1_MAX = 2000
        KNOWLEDGE_CACHE_TTL_HOT = 3600
        KNOWLEDGE_CACHE_TTL_COLD = 86400

    store = RedisKnowledgeStore(redis_client=_MemoryBackend(), settings=_Settings())

    await store.set("e_ttl", _entry("e_ttl"), "tender_document", "TX")
    # Should be in L1 immediately.
    assert store._l1_get("e_ttl") is not None

    # Wait for L1 TTL to expire.
    time.sleep(0.005)

    # L1 lookup should return None now.
    assert store._l1_get("e_ttl") is None
    # But the Redis backend still has it (not expired there).
    result = await store.get("e_ttl", "tender_document", "TX")
    assert result is not None  # re-fetched from Redis, re-promoted to L1


# ── T-032 criterion 4: get_stats() exposes cache fields ───────────────────────

def test_get_stats_exposes_cache_backend(monkeypatch):
    """get_stats() includes cache_has_redis, cache_degraded, cache_l1_size."""
    monkeypatch.setattr(project_memory_service, "bootstrap_project_context", lambda: None)

    brain = AgentBrain(db_session_factory=_db_factory([]))
    # Replace with a Redis-backed store.
    brain._knowledge_store = RedisKnowledgeStore(redis_client=_MemoryBackend())

    stats = brain.get_stats()
    assert "cache_has_redis" in stats
    assert "cache_degraded" in stats
    assert "cache_l1_size" in stats
    assert stats["cache_has_redis"] is True
    assert stats["cache_degraded"] is False


def test_get_stats_no_redis_backend(monkeypatch):
    """get_stats() reports cache_has_redis=False when no Redis client."""
    monkeypatch.setattr(project_memory_service, "bootstrap_project_context", lambda: None)

    brain = AgentBrain(db_session_factory=_db_factory([]))
    brain._knowledge_store = RedisKnowledgeStore()  # no redis_client

    stats = brain.get_stats()
    assert stats["cache_has_redis"] is False


# ── T-032 criterion 5: degradation path ───────────────────────────────────────

@pytest.mark.asyncio
async def test_degraded_store_falls_back_to_postgres():
    """When Redis fails, query_knowledge returns entries from PostgreSQL."""
    rows = [_pg_row("pg_fallback", "tender_document", "T9")]
    brain = AgentBrain(db_session_factory=_db_factory(rows))
    brain._knowledge_cache_loaded = False
    brain._knowledge_store = RedisKnowledgeStore(redis_client=_FailingBackend())

    results = await brain.query_knowledge(entry_type="tender_document", tender_id="T9")
    assert any(e["entry_id"] == "pg_fallback" for e in results)


@pytest.mark.asyncio
async def test_get_info_reflects_degradation():
    """get_info() reports degraded=True after a Redis failure."""
    store = RedisKnowledgeStore(redis_client=_FailingBackend())
    # Trigger degradation.
    try:
        await store.set("x", _entry("x"), "tender_document", "T0")
    except Exception:
        pass
    info = store.get_info()
    assert info["has_redis"] is True
    assert info["degraded"] is True
