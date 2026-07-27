"""
Data Retention Policy Framework

Configurable per-table retention policies with automatic cleanup.
Supports both scheduled (cron) and on-demand retention enforcement.

Usage:
    from app.core.data_retention import retention_manager

    # Register a policy
    retention_manager.register_policy(
        table_name="webhook_delivery_logs",
        retention_days=30,
        time_column="created_at",
        batch_size=1000,
    )

    # Run cleanup
    deleted = await retention_manager.enforce_all(session)

Environment:
    DATA_RETENTION_ENABLED — "true" to enable automatic cleanup
    DATA_RETENTION_BATCH_SIZE — rows deleted per batch (default 1000)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    """Definition of a data retention policy for a single table."""
    table_name: str
    retention_days: int
    time_column: str = "created_at"
    batch_size: int = 1000
    schema: str = "public"
    where_clause: Optional[str] = None  # Additional SQL filter (e.g. "status = 'archived'")
    enabled: bool = True
    last_run: Optional[datetime] = field(default=None)
    last_deleted: int = 0

    @property
    def cutoff_date(self) -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=self.retention_days)


class DataRetentionManager:
    """
    Central registry and executor for data retention policies.

    Policies are registered at startup; enforce_all() is called periodically
    (via cron or Celery beat) to delete old rows in batches.
    """

    def __init__(self):
        self._policies: Dict[str, RetentionPolicy] = {}
        self._default_batch_size = int(
            os.getenv("DATA_RETENTION_BATCH_SIZE", "1000")
        )

    def register_policy(self, policy: RetentionPolicy) -> RetentionPolicy:
        """Register or overwrite a retention policy."""
        self._policies[policy.table_name] = policy
        logger.info(
            "Retention policy registered: %s (%d days, batch=%d)",
            policy.table_name,
            policy.retention_days,
            policy.batch_size,
        )
        return policy

    def register_default_policies(self):
        """Register sensible defaults for the ProcureFlow schema."""
        defaults = [
            RetentionPolicy("webhook_delivery_logs", 30, batch_size=1000),
            RetentionPolicy("agent_results", 90, time_column="created_at", batch_size=500),
            RetentionPolicy("knowledge_entries", 365, time_column="created_at", batch_size=500),
            RetentionPolicy("opening_reports", 730, time_column="created_at", batch_size=200),  # 2 years
            RetentionPolicy("procurement_tenders", 1825, time_column="created_at", batch_size=100),  # 5 years
        ]
        for p in defaults:
            self.register_policy(p)
        return defaults

    def get_policy(self, table_name: str) -> Optional[RetentionPolicy]:
        return self._policies.get(table_name)

    def list_policies(self) -> List[RetentionPolicy]:
        return list(self._policies.values())

    def remove_policy(self, table_name: str) -> bool:
        if table_name in self._policies:
            del self._policies[table_name]
            return True
        return False

    # ── Enforcement ────────────────────────────────────────────────────────

    async def enforce(self, session: AsyncSession, table_name: str) -> int:
        """Enforce a single policy. Returns rows deleted."""
        policy = self._policies.get(table_name)
        if not policy or not policy.enabled:
            return 0

        cutoff = policy.cutoff_date
        full_table = f'"{policy.schema}"."{policy.table_name}"' if policy.schema != "public" else f'"{policy.table_name}"'

        where_parts = [f'"{policy.time_column}" < :cutoff']
        if policy.where_clause:
            where_parts.append(f"({policy.where_clause})")
        where_sql = " AND ".join(where_parts)

        # Use a CTE to delete in batches, avoiding long-running transactions
        total_deleted = 0
        batch_size = policy.batch_size

        while True:
            # sql-ok: identifiers from code-registered policies; cutoff/batch_size bound
            stmt = text(f"""
                DELETE FROM {full_table}
                WHERE ctid IN (
                    SELECT ctid FROM {full_table}
                    WHERE {where_sql}
                    ORDER BY "{policy.time_column}"
                    LIMIT :batch_size
                )
            """)
            try:
                result = await session.execute(stmt, {"cutoff": cutoff, "batch_size": batch_size})
                await session.commit()
                deleted = result.rowcount
                total_deleted += deleted
                if deleted < batch_size:
                    break
                logger.debug(
                    "Retention: deleted %d rows from %s (total %d)",
                    deleted,
                    table_name,
                    total_deleted,
                )
            except Exception as e:
                logger.error("Retention enforcement failed for %s: %s", table_name, e)
                await session.rollback()
                break

        policy.last_run = datetime.now(timezone.utc)
        policy.last_deleted = total_deleted
        logger.info(
            "Retention enforced: %s — deleted %d rows older than %s",
            table_name,
            total_deleted,
            cutoff,
        )
        return total_deleted

    async def enforce_all(self, session: AsyncSession) -> Dict[str, int]:
        """Enforce all registered policies. Returns a map of table_name → deleted count."""
        results = {}
        for table_name in self._policies:
            try:
                count = await self.enforce(session, table_name)
                results[table_name] = count
            except Exception as e:
                logger.error("Retention failed for %s: %s", table_name, e)
                results[table_name] = -1
        return results

    async def estimate_rows(self, session: AsyncSession, table_name: str) -> int:
        """Estimate how many rows would be deleted by a policy (dry run)."""
        policy = self._policies.get(table_name)
        if not policy:
            return 0

        cutoff = policy.cutoff_date
        full_table = f'"{policy.schema}"."{policy.table_name}"' if policy.schema != "public" else f'"{policy.table_name}"'
        where_parts = [f'"{policy.time_column}" < :cutoff']
        if policy.where_clause:
            where_parts.append(f"({policy.where_clause})")
        where_sql = " AND ".join(where_parts)

        stmt = text(f"SELECT COUNT(*) FROM {full_table} WHERE {where_sql}")  # sql-ok: identifiers from code-registered policies; cutoff bound
        result = await session.execute(stmt, {"cutoff": cutoff})
        return result.scalar() or 0


# ── Singleton ─────────────────────────────────────────────────────────────

import os  # noqa: E402

retention_manager = DataRetentionManager()
