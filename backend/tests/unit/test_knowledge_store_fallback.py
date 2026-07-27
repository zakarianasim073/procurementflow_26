"""W-009 (ADR-001): knowledge store degrades gracefully when Redis is down.

The store must never raise on a Redis failure — `get` returns None and
`query` returns an empty list so the caller (query_knowledge) falls through to
PostgreSQL. This validates acceptance criterion 4.
"""
from __future__ import annotations

import pytest

from app.agents.core.brain import RedisKnowledgeStore, _FailingBackend, _MemoryBackend


def _entry(entry_id, entry_type="tender_document", tender_id="T1"):
    return {
        "entry_id": entry_id,
        "entry_type": entry_type,
        "tender_id": tender_id,
        "agent_id": "agent-x",
        "data": {"payload": {}},
        "summary": "s",
        "tags": [],
    }


@pytest.fixture
def degraded_store():
    return RedisKnowledgeStore(redis_client=_FailingBackend())


async def test_set_does_not_raise_on_redis_outage(degraded_store):
    # Write is swallowed; store marks itself degraded.
    await degraded_store.set("e1", _entry("e1"), "tender_document", "T1")
    assert degraded_store._degraded is True


async def test_get_returns_none_on_redis_outage(degraded_store):
    await degraded_store.set("e1", _entry("e1"), "tender_document", "T1")
    assert await degraded_store.get("e1", "tender_document", "T1") is None


async def test_query_returns_empty_on_redis_outage(degraded_store):
    await degraded_store.set("e1", _entry("e1"), "tender_document", "T1")
    assert await degraded_store.query(entry_type="tender_document") == []


async def test_local_backend_still_caches_without_redis():
    # No Redis client at all -> in-process backend keeps caching working for a
    # single replica (just not cross-replica shared).
    store = RedisKnowledgeStore(redis_client=None)
    await store.set("e1", _entry("e1"), "tender_document", "T1")
    got = await store.get("e1", "tender_document", "T1")
    assert got is not None
    assert await store.query(entry_type="tender_document") == [got]
