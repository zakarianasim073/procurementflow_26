"""W-009 (ADR-001): the knowledge cache is shared across worker replicas.

Two stores backed by the same backend instance simulate two processes/replicas.
A write on replica A must be readable on replica B (L1 isolated, but backend
is the shared source of truth). This validates acceptance criterion 5 and the
motivation for moving off per-process in-memory dicts.
"""
from __future__ import annotations

import pytest

from app.agents.core.brain import RedisKnowledgeStore, _MemoryBackend


def _entry(entry_id, entry_type="tender_document", tender_id="T1"):
    return {
        "entry_id": entry_id,
        "entry_type": entry_type,
        "tender_id": tender_id,
        "agent_id": "agent-x",
        "data": {"payload": {entry_id: True}},
        "summary": "s",
        "tags": [],
    }


async def test_write_on_one_replica_readable_on_another():
    shared = _MemoryBackend()
    replica_a = RedisKnowledgeStore(redis_client=shared)
    replica_b = RedisKnowledgeStore(redis_client=shared)

    await replica_a.set("e1", _entry("e1"), "tender_document", "T1")

    # B's L1 is empty, but it reads the shared backend.
    assert replica_b._l1 == {}
    got = await replica_b.get("e1", "tender_document", "T1")
    assert got is not None
    assert got["entry_id"] == "e1"


async def test_query_visible_across_replicas():
    shared = _MemoryBackend()
    replica_a = RedisKnowledgeStore(redis_client=shared)
    replica_b = RedisKnowledgeStore(redis_client=shared)

    await replica_a.set("a", _entry("a"), "tender_document", "T1")
    await replica_a.set("b", _entry("b", "boq_text", "T2"), "boq_text", "T2")

    results = await replica_b.query(entry_type="tender_document", tender_id="T1")
    assert {e["entry_id"] for e in results} == {"a"}


async def test_invalidation_propagates_across_replicas():
    shared = _MemoryBackend()
    replica_a = RedisKnowledgeStore(redis_client=shared)
    replica_b = RedisKnowledgeStore(redis_client=shared)

    await replica_a.set("e1", _entry("e1"), "tender_document", "T1")
    await replica_a.invalidate(entry_type="tender_document", tender_id="T1")

    # B observes the invalidation via the shared backend.
    assert await replica_b.get("e1", "tender_document", "T1") is None
