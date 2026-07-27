from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Dict, Optional

from ..database.connection import get_db_pool
from ..framework.logger import get_logger

log = get_logger("crawler.heartbeat")


class WorkerHeartbeat:
    """Periodically reports crawler worker liveness to the database."""

    def __init__(self, worker_id: str = "crawler-default", interval: int = 30):
        self.worker_id = worker_id
        self.interval = interval
        self._task: Optional[asyncio.Task] = None
        self._status = "idle"
        self._metadata: Dict[str, str] = {}
        self._started_at = time.time()

    async def start(self):
        await self._ensure_table()
        self._task = asyncio.create_task(self._loop())
        log.info("heartbeat_started", worker_id=self.worker_id, interval=self.interval)

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._report("stopped")
        log.info("heartbeat_stopped", worker_id=self.worker_id)

    async def set_status(self, status: str, **metadata):
        self._status = status
        self._metadata.update({k: str(v) for k, v in metadata.items()})
        await self._report(status)

    async def _loop(self):
        while True:
            try:
                await self._report(self._status)
            except Exception as e:
                log.warning("heartbeat_write_failed", error=str(e))
            await asyncio.sleep(self.interval)

    async def _ensure_table(self):
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS crawl_heartbeats (
                    worker_id VARCHAR(100) PRIMARY KEY,
                    status VARCHAR(50) NOT NULL DEFAULT 'idle',
                    last_beat TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    metadata JSONB,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

    async def _report(self, status: str):
        pool = await get_db_pool()
        import json
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO crawl_heartbeats (worker_id, status, last_beat, started_at, metadata, updated_at)
                VALUES ($1, $2, NOW(), $3, $4::jsonb, NOW())
                ON CONFLICT (worker_id) DO UPDATE
                    SET status = EXCLUDED.status,
                        last_beat = NOW(),
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                """,
                self.worker_id, status, datetime.utcfromtimestamp(self._started_at),
                json.dumps(self._metadata),
            )


async def get_active_workers(timeout_seconds: int = 120) -> list:
    """Return workers that reported a heartbeat within the timeout window."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT worker_id, status, last_beat, metadata FROM crawl_heartbeats "
            "WHERE last_beat > NOW() - ($1 || ' seconds')::interval",
            str(timeout_seconds),
        )
        return [dict(r) for r in rows]
