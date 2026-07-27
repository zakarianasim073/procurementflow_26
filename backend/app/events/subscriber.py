"""Event subscriber — consumer groups + idempotency (X-003).

At-least-once transport means duplicates WILL arrive; the processed-set guard
(SADD event_id) guarantees zero duplicate agent runs — the X-003 acceptance.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Awaitable, Callable

from pydantic import BaseModel

logger = logging.getLogger(__name__)

GROUP = "procureflow"
MAX_RETRIES = 3


class IncomingEvent(BaseModel):
    """Mirror of the contract envelope (frozen wire shape)."""

    event_id: str
    event_type: str
    event_version: str = "v1"
    timestamp: str = ""
    aggregate_id: str = ""
    tenant_id: str = ""
    correlation_id: str = ""
    payload: dict = {}


Handler = Callable[[IncomingEvent], Awaitable[None]]


class EventSubscriber:
    def __init__(self, redis: Any = None, group: str = GROUP, name: str = "worker-1") -> None:
        self._redis = redis
        self._group = group
        self._name = name
        self._handlers: dict[str, Handler] = {}
        self._retries: dict[str, int] = {}

    def register(self, event_type: str, handler: Handler) -> None:
        self._handlers[event_type] = handler

    async def _get_redis(self) -> Any:
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True
            )
        return self._redis

    def _processed_key(self) -> str:
        return f"events:processed:{self._group}"

    async def poll(self, count: int = 20) -> int:
        """One pass over all registered streams: pending first, then new."""
        redis = await self._get_redis()
        handled = 0
        for event_type, handler in self._handlers.items():
            stream = f"events:{event_type}"
            try:
                await redis.xgroup_create(stream, self._group, id="0", mkstream=True)
            except Exception as exc:
                if "BUSYGROUP" not in str(exc):
                    raise
            for start in ("0", ">"):
                batches = await redis.xreadgroup(
                    self._group, self._name, {stream: start}, count=count
                )
                for _s, messages in batches or []:
                    for msg_id, fields in messages:
                        handled += await self._process(redis, stream, event_type, msg_id, fields, handler)
        return handled

    async def _process(self, redis, stream, event_type, msg_id, fields, handler) -> int:
        event = IncomingEvent.model_validate_json(fields["data"])

        # Idempotency wall: first delivery wins, duplicates ack-and-skip.
        if not await redis.sadd(self._processed_key(), event.event_id):
            await redis.xack(stream, self._group, msg_id)
            logger.info("duplicate delivery skipped: %s", event.event_id)
            return 0

        try:
            await handler(event)
        except Exception as exc:
            await redis.srem(self._processed_key(), event.event_id)  # allow retry
            attempts = self._retries.get(msg_id, 0) + 1
            self._retries[msg_id] = attempts
            if attempts >= MAX_RETRIES:
                await redis.xadd(f"dlq:{event_type}:{self._group}",
                                 {"data": fields["data"], "error": str(exc)[:500]})
                await redis.xack(stream, self._group, msg_id)
                self._retries.pop(msg_id, None)
                logger.error("%s -> consumer DLQ after %d attempts: %s", event.event_id, attempts, exc)
            return 0
        await redis.xack(stream, self._group, msg_id)
        self._retries.pop(msg_id, None)
        return 1
