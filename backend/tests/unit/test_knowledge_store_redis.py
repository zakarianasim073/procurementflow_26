"""W-009 (ADR-001): Redis-backed knowledge store — correctness, TTLs, querying.

Uses the in-process `_MemoryBackend` as a Redis stand-in so no live Redis is
required; the same store code path (L1 + backend + index sets) is exercised.
"""
from __future__ import annotations

import asyncio

import pytest

from app.agents.core.brain import RedisKnowledgeStore, _MemoryBackend


def _entry(entry_id, entry_type, tender_id, agent_id="agent-x", tags=None):
    return {
        "entry_id": entry_id,
        "entry_type": entry_type,
        "tender_id": tender_id,
        "agent_id": agent_id,
        "source": agent_id,
        "data": {"payload": {"k": entry_id}},
        "summary": f"summary-{entry_id}",
        "tags": tags or [],
    }


@pytest.fixture
def store():
    return RedisKnowledgeStore(redis_client=_MemoryBackend())


async def test_set_and_get_roundtrip(store):
    await store.set("e1", _entry("e1", "tender_document", "T1"), "tender_document", "T1")
    got = await store.get("e1", "tender_document", "T1")
    assert got is not None
    assert got["entry_id"] == "e1"
    assert got["tender_id"] == "T1"


async def test_l1_serves_repeat_reads(store):
    await store.set("e1", _entry("e1", "tender_document", "T1"), "tender_document", "T1")
    assert (await store.get("e1", "tender_document", "T1")) is not None
    # Second read is served from L1 (no exception path, identical payload).
    assert (await store.get("e1", "tender_document", "T1"))["entry_id"] == "e1"


async def test_ttl_per_entry_type(store):
    assert store._ttl_for("boq_text") == store._ttl_hot
    assert store._ttl_for("tds_text") == store._ttl_hot
    assert store._ttl_for("win") == store._ttl_cold


async def test_ttl_expiry_is_respected(store, monkeypatch):
    # Force a negative TTL so both L1 and the backend entry expire immediately.
    monkeypatch.setattr(store, "_ttl_hot", -1)
    monkeypatch.setattr(store, "_l1_ttl", -1)
    await store.set("e1", _entry("e1", "tender_document", "T1"), "tender_document", "T1")
    assert await store.get("e1", "tender_document", "T1") is None


async def test_query_filters_by_type_and_tender(store):
    await store.set("a", _entry("a", "tender_document", "T1"), "tender_document", "T1")
    await store.set("b", _entry("b", "boq_text", "T1"), "boq_text", "T1")
    await store.set("c", _entry("c", "tender_document", "T2"), "tender_document", "T2")

    by_type = await store.query(entry_type="tender_document")
    assert {e["entry_id"] for e in by_type} == {"a", "c"}

    by_tender = await store.query(tender_id="T1")
    assert {e["entry_id"] for e in by_tender} == {"a", "b"}

    by_both = await store.query(entry_type="tender_document", tender_id="T1")
    assert {e["entry_id"] for e in by_both} == {"a"}


async def test_query_filters_by_agent_and_tags(store):
    await store.set("a", _entry("a", "tender_document", "T1", agent_id="agent-x"), "tender_document", "T1")
    await store.set("b", _entry("b", "tender_document", "T1", agent_id="agent-y"), "tender_document", "T1")
    await store.set("c", _entry("c", "tender_document", "T1", agent_id="agent-x", tags=["urgent"]), "tender_document", "T1")

    only_x = await store.query(entry_type="tender_document", agent_id="agent-x")
    assert {e["entry_id"] for e in only_x} == {"a", "c"}

    tagged = await store.query(entry_type="tender_document", tags=["urgent"])
    assert {e["entry_id"] for e in tagged} == {"c"}


async def test_size_reflects_l1(store):
    assert len(store) == 0
    await store.set("a", _entry("a", "tender_document", "T1"), "tender_document", "T1")
    assert len(store) == 1
