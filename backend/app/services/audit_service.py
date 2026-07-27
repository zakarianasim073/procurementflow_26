"""Audit logging helpers for enterprise events and HTTP requests."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enterprise import AuditLog

logger = logging.getLogger(__name__)


def _canonical_payload(entry: AuditLog) -> Dict[str, Any]:
    return {
        "tenant_id": entry.tenant_id,
        "actor_id": entry.actor_id,
        "actor_type": entry.actor_type,
        "action": entry.action,
        "resource_type": entry.resource_type,
        "resource_id": entry.resource_id,
        "status": entry.status,
        "ip_address": entry.ip_address,
        "user_agent": entry.user_agent,
        "request_id": entry.request_id,
        "trace_id": entry.trace_id,
        "metadata": entry.metadata_json or {},
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


def compute_entry_hash(payload: Dict[str, Any], previous_hash: Optional[str]) -> str:
    canonical = json.dumps(
        {"previous_hash": previous_hash, "entry": payload},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AuditService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_event(
        self,
        *,
        action: str,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        actor_type: str = "user",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: str = "success",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        entry = AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            trace_id=trace_id,
            metadata_json=metadata or {},
            created_at=datetime.now(timezone.utc),
        )
        previous = await self.session.scalar(
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(1)
        )
        entry.previous_hash = previous.entry_hash if previous else None
        entry.entry_hash = compute_entry_hash(_canonical_payload(entry), entry.previous_hash)
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_events(
        self,
        *,
        tenant_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        stmt = select(AuditLog)
        if tenant_id:
            stmt = stmt.where(AuditLog.tenant_id == tenant_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        stmt = stmt.order_by(AuditLog.created_at.desc()).limit(max(1, min(limit, 500)))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def verify_chain(
        self,
        *,
        tenant_id: Optional[str] = None,
        limit: int = 5000,
    ) -> tuple[bool, Optional[str], int]:
        entries = await self._chain_entries(tenant_id=tenant_id, limit=limit)
        previous_hash = None
        for entry in entries:
            expected = compute_entry_hash(_canonical_payload(entry), previous_hash)
            if entry.previous_hash != previous_hash or entry.entry_hash != expected:
                return False, entry.id, len(entries)
            previous_hash = entry.entry_hash
        return True, None, len(entries)

    async def export_chain(
        self,
        *,
        tenant_id: Optional[str] = None,
        limit: int = 5000,
    ) -> Dict[str, Any]:
        entries = await self._chain_entries(tenant_id=tenant_id, limit=limit)
        intact, broken_at_id, _ = await self.verify_chain(
            tenant_id=tenant_id,
            limit=limit,
        )
        return {
            "chain_intact": intact,
            "broken_at_id": broken_at_id,
            "total": len(entries),
            "entries": [entry.to_dict() for entry in entries],
        }

    async def _chain_entries(
        self,
        *,
        tenant_id: Optional[str],
        limit: int,
    ) -> list[AuditLog]:
        stmt = select(AuditLog)
        if tenant_id:
            stmt = stmt.where(AuditLog.tenant_id == tenant_id)
        stmt = stmt.order_by(AuditLog.created_at.asc(), AuditLog.id.asc()).limit(
            max(1, min(limit, 5000))
        )
        return list((await self.session.execute(stmt)).scalars().all())


async def log_audit_event(session: AsyncSession, **kwargs: Any) -> Optional[AuditLog]:
    try:
        return await AuditService(session).log_event(**kwargs)
    except Exception as exc:
        logger.debug("Audit log write failed: %s", exc)
        return None
