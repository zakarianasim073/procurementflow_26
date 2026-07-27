"""Runtime locking and cache helpers for service-layer heavy operations."""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None
_redis_unavailable_until = 0.0
REDIS_FAILURE_BACKOFF_SECONDS = 30


@dataclass
class RuntimeLockToken:
    name: str
    acquired: bool
    lock: Any = None

    async def release(self) -> None:
        if self.lock is None or not self.acquired:
            return
        try:
            await self.lock.release()
        except Exception as exc:
            logger.debug("Redis lock release failed for %s: %s", self.name, exc)
        finally:
            self.acquired = False


async def get_redis() -> Optional[redis.Redis]:
    global _redis_client, _redis_unavailable_until
    import os
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        return None
    if time.monotonic() < _redis_unavailable_until:
        return None
    if _redis_client is None:
        _redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=0.25,
            socket_timeout=0.25,
        )
    try:
        await _redis_client.ping()
        return _redis_client
    except Exception as exc:
        _redis_unavailable_until = time.monotonic() + REDIS_FAILURE_BACKOFF_SECONDS
        logger.debug("Redis unavailable, continuing without runtime guard: %s", exc)
        return None


@asynccontextmanager
async def distributed_lock(name: str, ttl: int = 900) -> AsyncIterator[bool]:
    token = await acquire_distributed_lock(name, ttl=ttl)
    try:
        yield token.acquired
    finally:
        await token.release()


async def acquire_distributed_lock(name: str, ttl: int = 900) -> RuntimeLockToken:
    client = await get_redis()
    if client is None:
        return RuntimeLockToken(name=name, acquired=True, lock=None)

    lock = client.lock(f"procureflow:lock:{name}", timeout=ttl, blocking_timeout=1)
    acquired = await lock.acquire()
    return RuntimeLockToken(name=name, acquired=bool(acquired), lock=lock)


async def cache_get(key: str) -> Any:
    client = await get_redis()
    if client is None:
        return None
    try:
        raw = await client.get(f"procureflow:cache:{key}")
    except Exception as exc:
        logger.debug("Redis cache get failed for %s: %s", key, exc)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    client = await get_redis()
    if client is None:
        return
    try:
        await client.set(f"procureflow:cache:{key}", json.dumps(value, default=str), ex=ttl)
    except Exception as exc:
        logger.debug("Redis cache set failed for %s: %s", key, exc)
