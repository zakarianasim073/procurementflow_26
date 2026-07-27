"""W-009 (ADR-001): cache invalidation by entry_type and/or tender_id.

Validates acceptance criterion 6 — targeted invalidation removes only the
entries that match, preserving everything else.
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
        "data": {"payload": {}},
        "summary": "s",
        "tags": [],
    }


@pytest.fixture
async def populated():
    store = RedisKnowledgeStore(redis_client=_MemoryBackend())
    await store.set("a", _entry("a", "tender_document", "T1"), "tender_document", "T1")
    await store.set("b", _entry("b", "boq_text", "T1"), "boq_text", "T1")
    await store.set("c", _entry("c", "tender_document", "T2"), "tender_document", "T2")
    return store


async def test_invalidate_by_type_and_tender(populated):
    await populated.invalidate(entry_type="tender_document", tender_id="T1")
    assert await populated.get("a", "tender_document", "T1") is None
    assert await populated.get("b", "boq_text", "T1") is not None
    assert await populated.get("c", "tender_document", "T2") is not None


async def test_invalidate_by_type_only(populated):
    await populated.invalidate(entry_type="boq_text")
    assert await populated.get("a", "tender_document", "T1") is not None
    assert await populated.get("b", "boq_text", "T1") is None


async def test_invalidate_by_tender_only(populated):
    await populated.invalidate(tender_id="T1")
    assert await populated.get("a", "tender_document", "T1") is None
    assert await populated.get("b", "boq_text", "T1") is None
    assert await populated.get("c", "tender_document", "T2") is not None


async def test_invalidate_all(populated):
    await populated.invalidate()
    for eid, etype, tid in [
        ("a", "tender_document", "T1"),
        ("b", "boq_text", "T1"),
        ("c", "tender_document", "T2"),
    ]:
        assert await populated.get(eid, etype, tid) is None


async def test_invalidate_removes_from_query(populated):
    await populated.invalidate(entry_type="tender_document", tender_id="T1")
    remaining = await populated.query(entry_type="tender_document")
    assert {e["entry_id"] for e in remaining} == {"c"}
