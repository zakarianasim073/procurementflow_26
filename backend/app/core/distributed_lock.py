"""
Distributed Lock — Redis Redlock implementation for crawler coordination.

Prevents multiple workers from crawling the same tender or running the same
agent pipeline simultaneously.

Usage:
    from app.core.distributed_lock import distributed_lock

    async with distributed_lock.acquire("crawler:app-12345", ttl=60) as lock:
        if lock:
            # Only one process gets here
            await run_crawler()
        else:
            print("Another process is already crawling this tender")

Environment:
    REDIS_URL — redis://host:port/db
    REDLOCK_REPLICAS — number of independent Redis nodes for Redlock (default 1)
"""

import asyncio
import logging
import os
import random
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Lock:
    """Represents a held distributed lock."""
    resource: str
    value: str
    ttl_ms: int
    acquired_at: float

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.acquired_at) * 1000 > self.ttl_ms


class DistributedLock:
    """
    Redis-based distributed lock with Redlock algorithm support.

    Single-node mode (default): Uses a single Redis instance.
    Multi-node mode: Uses Redlock across N Redis replicas for stronger guarantees.
    """

    def __init__(self, redis_url: str = None, replicas: int = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.replicas = replicas or int(os.getenv("REDLOCK_REPLICAS", "1"))
        self._clients = []
        self._lock_prefix = "procureflow:lock:"
        self._default_ttl = 30  # seconds

    async def _get_clients(self):
        """Lazy-init Redis clients."""
        if not self._clients:
            try:
                from redis.asyncio import Redis
                # Single-node: one client
                # Multi-node: parse comma-separated URLs from REDLOCK_URLS
                urls = os.getenv("REDLOCK_URLS", self.redis_url).split(",")
                for url in urls[:self.replicas]:
                    self._clients.append(Redis.from_url(url.strip(), decode_responses=True))
                logger.info("DistributedLock initialized with %d Redis node(s)", len(self._clients))
            except Exception as e:
                logger.warning("DistributedLock Redis init failed: %s", e)
        return self._clients

    # ── Redlock acquire ────────────────────────────────────────────────────

    async def acquire(self, resource: str, ttl: int = None) -> Optional[Lock]:
        """
        Try to acquire a lock using the Redlock algorithm.

        Returns a Lock object on success, or None if the lock is held by another process.
        """
        ttl = ttl or self._default_ttl
        ttl_ms = int(ttl * 1000)
        value = f"{os.getpid()}-{time.time()}-{random.randint(0, 999999)}"
        lock_key = f"{self._lock_prefix}{resource}"

        clients = await self._get_clients()
        if not clients:
            logger.error("DistributedLock: no Redis clients available; lock acquisition denied")
            return None

        start_time = time.time()
        acquired = 0
        for client in clients:
            try:
                # Use NX (only set if not exists) with millisecond TTL
                ok = await client.set(lock_key, value, nx=True, px=ttl_ms)
                if ok:
                    acquired += 1
            except Exception as e:
                logger.debug("DistributedLock: node failed for %s: %s", resource, e)

        # Redlock: need majority
        elapsed_ms = (time.time() - start_time) * 1000
        majority = (len(clients) // 2) + 1

        if acquired >= majority and elapsed_ms < ttl_ms * 0.9:
            lock = Lock(resource=resource, value=value, ttl_ms=ttl_ms, acquired_at=time.time())
            logger.debug("DistributedLock acquired: %s", resource)
            return lock

        # Failed to acquire — release any partial locks
        for client in clients:
            try:
                await self._release_on_client(client, lock_key, value)
            except Exception:
                pass
        return None

    async def release(self, lock: Lock):
        """Release a previously acquired lock."""
        if not lock:
            return
        lock_key = f"{self._lock_prefix}{lock.resource}"
        clients = await self._get_clients()
        if not clients:
            return
        for client in clients:
            try:
                await self._release_on_client(client, lock_key, lock.value)
            except Exception as e:
                logger.debug("DistributedLock release error on node: %s", e)
        logger.debug("DistributedLock released: %s", lock.resource)

    async def _release_on_client(self, client, key: str, value: str):
        """Release lock on a single Redis node using Lua script (atomic check-and-delete)."""
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        await client.eval(script, 1, key, value)

    async def extend(self, lock: Lock, additional_ttl: int) -> bool:
        """Extend the TTL of a held lock."""
        if not lock or lock.is_expired:
            return False
        lock_key = f"{self._lock_prefix}{lock.resource}"
        clients = await self._get_clients()
        if not clients:
            lock.ttl_ms += additional_ttl * 1000
            lock.acquired_at = time.time()
            return True
        for client in clients:
            try:
                # Only extend if we still own the lock
                current = await client.get(lock_key)
                if current == lock.value:
                    await client.pexpire(lock_key, int(lock.ttl_ms + additional_ttl * 1000))
            except Exception:
                pass
        lock.ttl_ms += additional_ttl * 1000
        return True

    async def is_locked(self, resource: str) -> bool:
        """Check if a resource is currently locked."""
        lock_key = f"{self._lock_prefix}{resource}"
        clients = await self._get_clients()
        if not clients:
            return False
        for client in clients:
            try:
                val = await client.get(lock_key)
                if val:
                    return True
            except Exception:
                pass
        return False

    @asynccontextmanager
    async def context(self, resource: str, ttl: int = None, blocking: bool = False,
                       blocking_timeout: int = 30):
        """
        Async context manager for lock acquisition.

        Usage:
            async with distributed_lock.context("crawler:app-12345", ttl=60) as lock:
                if lock:
                    await run_crawler()
        """
        ttl = ttl or self._default_ttl
        lock = None
        deadline = time.time() + blocking_timeout if blocking else time.time()
        while True:
            lock = await self.acquire(resource, ttl)
            if lock or not blocking:
                break
            if time.time() > deadline:
                break
            await asyncio.sleep(0.5)
        try:
            yield lock
        finally:
            if lock:
                await self.release(lock)


# ── Singleton ───────────────────────────────────────────────────────────────

distributed_lock = DistributedLock()
