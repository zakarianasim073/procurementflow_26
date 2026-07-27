"""Data retention and archival service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import delete, insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enterprise import ArchivedRecord, DataRetentionPolicy


RETENTION_TARGETS: dict[str, dict[str, str]] = {
    "audit_log": {"table": "audit_logs", "timestamp": "created_at", "id": "id"},
    "webhook_delivery": {"table": "webhook_delivery_logs", "timestamp": "created_at", "id": "id"},
    "agent_result": {"table": "agent_results", "timestamp": "created_at", "id": "id"},
    "brain_message": {"table": "agent_brain_messages", "timestamp": "created_at", "id": "id"},
}


class RetentionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_policy(
        self,
        *,
        resource_type: str,
        retention_days: int,
        tenant_id: Optional[str] = None,
        archive_before_delete: bool = True,
        created_by: Optional[str] = None,
    ) -> DataRetentionPolicy:
        if resource_type not in RETENTION_TARGETS:
            raise ValueError(f"Unsupported retention resource_type: {resource_type}")
        if retention_days < 1:
            raise ValueError("retention_days must be >= 1")
        policy = DataRetentionPolicy(
            tenant_id=tenant_id,
            resource_type=resource_type,
            retention_days=retention_days,
            archive_before_delete=archive_before_delete,
            created_by=created_by,
        )
        self.session.add(policy)
        await self.session.flush()
        return policy

    async def list_policies(self, tenant_id: Optional[str] = None) -> list[DataRetentionPolicy]:
        stmt = select(DataRetentionPolicy).where(DataRetentionPolicy.is_active.is_(True))
        if tenant_id:
            stmt = stmt.where(DataRetentionPolicy.tenant_id == tenant_id)
        result = await self.session.execute(stmt.order_by(DataRetentionPolicy.created_at.desc()))
        return list(result.scalars().all())

    async def apply_policy(self, policy: DataRetentionPolicy, dry_run: bool = True, limit: int = 1000) -> Dict[str, Any]:
        target = RETENTION_TARGETS.get(policy.resource_type)
        if not target:
            raise ValueError(f"Unsupported retention resource_type: {policy.resource_type}")

        cutoff = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
        table = target["table"]
        timestamp_col = target["timestamp"]
        id_col = target["id"]
        tenant_filter = "AND tenant_id = :tenant_id" if policy.tenant_id else ""
        params = {"cutoff": cutoff, "tenant_id": policy.tenant_id, "limit": max(1, min(limit, 5000))}

        rows = (await self.session.execute(
            text(
                # sql-ok: identifiers from RETENTION_TARGETS allowlist; values bound
                f"""
                SELECT to_jsonb(t.*) AS record
                FROM {table} t
                WHERE {timestamp_col} < :cutoff
                {tenant_filter}
                ORDER BY {timestamp_col}
                LIMIT :limit
                """
            ),
            params,
        )).mappings().all()

        if dry_run or not rows:
            return {"resource_type": policy.resource_type, "matched": len(rows), "archived": 0, "deleted": 0, "dry_run": dry_run}

        source_ids = []
        if policy.archive_before_delete:
            for row in rows:
                record = row["record"] or {}
                source_id = str(record.get(id_col, ""))
                source_ids.append(source_id)
                await self.session.execute(
                    insert(ArchivedRecord).values(
                        tenant_id=record.get("tenant_id") or policy.tenant_id,
                        source_table=table,
                        source_id=source_id,
                        resource_type=policy.resource_type,
                        record_data=record,
                        delete_after=None,
                    )
                )
        else:
            source_ids = [str((row["record"] or {}).get(id_col, "")) for row in rows]

        if source_ids:
            await self.session.execute(
                # sql-ok: identifiers from RETENTION_TARGETS allowlist; values bound
                text(f"DELETE FROM {table} WHERE {id_col} = ANY(:ids)"),
                {"ids": source_ids},
            )

        return {
            "resource_type": policy.resource_type,
            "matched": len(rows),
            "archived": len(rows) if policy.archive_before_delete else 0,
            "deleted": len(source_ids),
            "dry_run": False,
        }

    async def run(self, *, tenant_id: Optional[str] = None, dry_run: bool = True, limit_per_policy: int = 1000) -> Dict[str, Any]:
        policies = await self.list_policies(tenant_id=tenant_id)
        results = [await self.apply_policy(policy, dry_run=dry_run, limit=limit_per_policy) for policy in policies]
        return {
            "policies": len(policies),
            "results": results,
            "dry_run": dry_run,
        }
