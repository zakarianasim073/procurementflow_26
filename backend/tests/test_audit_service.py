"""ENT-03: tamper-evident, append-only audit trail tests."""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy import text

from app.models.enterprise import AuditLog
from app.services.audit_service import (
    AuditService,
    compute_entry_hash,
    _canonical_payload,
)


def _tenant() -> str:
    return f"tenant-{uuid.uuid4().hex[:12]}"


@pytest.mark.asyncio
async def test_log_event_builds_valid_chain(db_session):
    tenant = _tenant()
    svc = AuditService(db_session)
    # Each audit event is its own committed unit (mirrors production), so the
    # hash chain's previous link is durably visible to the next write.
    for i in range(3):
        await svc.log_event(action=f"act_{i}", tenant_id=tenant, resource_id=str(i))
        await db_session.commit()

    intact, broken_id, total = await svc.verify_chain(tenant_id=tenant)
    assert intact is True
    assert broken_id is None
    assert total == 3


@pytest.mark.asyncio
async def test_entry_hash_is_deterministic():
    e = AuditLog(
        tenant_id="t1",
        action="login",
        resource_type="user",
        resource_id="u1",
        status="success",
        metadata_json={"ip": "1.2.3.4"},
    )
    h1 = compute_entry_hash(_canonical_payload(e), None)
    h2 = compute_entry_hash(_canonical_payload(e), None)
    assert h1 == h2
    assert len(h1) == 64


@pytest.mark.asyncio
async def test_audit_update_is_forbidden(db_session):
    svc = AuditService(db_session)
    entry = await svc.log_event(action="create", tenant_id=_tenant(), resource_id="r1")

    with pytest.raises(Exception) as exc:
        await db_session.execute(
            text("UPDATE audit_logs SET status = :s WHERE id = :i"),
            {"s": "tampered", "i": entry.id},
        )
    assert "append-only" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_audit_delete_is_forbidden(db_session):
    svc = AuditService(db_session)
    entry = await svc.log_event(action="create", tenant_id=_tenant(), resource_id="r1")

    with pytest.raises(Exception) as exc:
        await db_session.execute(
            text("DELETE FROM audit_logs WHERE id = :i"),
            {"i": entry.id},
        )
    assert "append-only" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_verify_chain_detects_tampering(db_session):
    tenant = _tenant()
    # Genesis row whose stored entry_hash does NOT match the computed hash.
    # (A single row removes ordering ambiguity: the genesis entry must always
    #  be the first link verified and is guaranteed to be flagged as broken.)
    e1 = AuditLog(tenant_id=tenant, action="a1", previous_hash=None, entry_hash="deadbeef")
    db_session.add(e1)
    await db_session.flush()

    svc = AuditService(db_session)
    intact, broken_id, total = await svc.verify_chain(tenant_id=tenant)
    assert intact is False
    assert broken_id == e1.id
    assert total == 1


@pytest.mark.asyncio
async def test_export_chain_includes_hashes_and_integrity(db_session):
    tenant = _tenant()
    svc = AuditService(db_session)
    for i in range(3):
        await svc.log_event(action=f"act_{i}", tenant_id=tenant, resource_id=str(i))
        await db_session.commit()

    export = await svc.export_chain(tenant_id=tenant)
    assert export["chain_intact"] is True
    assert export["total"] == 3
    assert len(export["entries"]) == 3
    # The export alone must let an auditor verify linkage offline.
    assert export["entries"][0]["previous_hash"] is None
    for i, e in enumerate(export["entries"]):
        assert len(e["entry_hash"]) == 64
        if i > 0:
            assert e["previous_hash"] == export["entries"][i - 1]["entry_hash"]


@pytest.mark.asyncio
async def test_export_chain_reports_tampering(db_session):
    tenant = _tenant()
    e1 = AuditLog(tenant_id=tenant, action="a1", previous_hash=None, entry_hash="deadbeef")
    db_session.add(e1)
    await db_session.flush()

    svc = AuditService(db_session)
    export = await svc.export_chain(tenant_id=tenant)
    assert export["chain_intact"] is False
    assert export["broken_at_id"] == e1.id
    assert export["entries"][0]["entry_hash"] == "deadbeef"


@pytest.mark.asyncio
async def test_audit_export_endpoint(db_session):
    import httpx
    from fastapi import FastAPI
    from app.db.base import get_async_session as base_get_async_session
    from app.core.security import get_current_user as base_get_current_user
    from app.api.v2.enterprise import router as ent_router

    tenant = "tenant-export-ep"
    svc = AuditService(db_session)
    await svc.log_event(action="exported", tenant_id=tenant, resource_id="r1")
    await db_session.commit()

    # Fresh app with no auth middleware so we exercise the endpoint handler
    # directly (the middleware path is covered elsewhere); override deps.
    app = FastAPI()
    app.include_router(ent_router)

    async def _session_override():
        yield db_session

    async def _user_override():
        return {"tenant_id": tenant, "id": "user-exp"}

    app.dependency_overrides[base_get_async_session] = _session_override
    app.dependency_overrides[base_get_current_user] = _user_override

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/enterprise/audit-logs/export")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        assert body["chain_intact"] is True
        assert body["total"] == 1
        assert body["entries"][0]["entry_hash"]
