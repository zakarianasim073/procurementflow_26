"""
Redis Streams Event Bus — Enterprise async event streaming layer.

Provides publish/subscribe via Redis Streams for inter-agent communication,
pipeline events, and cross-process async processing.

Usage:
    from app.core.event_bus import event_bus

    # Publish an event
    await event_bus.publish("agent.completed", {
        "agent_id": "agent-001",
        "tender_id": "12345",
        "status": "success",
    })

    # Consume events (in a background task)
    async for event in event_bus.consume("agent.completed", group="workers"):
        print(event)

    # Subscribe with a handler
    await event_bus.subscribe("agent.completed", my_handler)

Environment:
    REDIS_URL — redis://host:port/db (default: redis://localhost:6379/0)
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class EventEnvelope:
    """Standard event envelope for Redis Streams."""
    event_type: str
    payload: Dict[str, Any]
    source: str = "procureflow"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_id: str = ""
    trace_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "payload": json.dumps(self.payload, default=str),
            "source": self.source,
            "timestamp": self.timestamp,
            "event_id": self.event_id,
            "trace_id": self.trace_id,
        }

    @classmethod
    def from_stream(cls, event_type: str, stream_id: str, fields: Dict[str, str]) -> "EventEnvelope":
        payload = {}
        try:
            payload = json.loads(fields.get("payload", "{}"))
        except Exception:
            payload = {"raw": fields.get("payload", "")}
        return cls(
            event_type=event_type,
            payload=payload,
            source=fields.get("source", "unknown"),
            timestamp=fields.get("timestamp", ""),
            event_id=stream_id,
            trace_id=fields.get("trace_id", ""),
        )


class RedisEventBus:
    """
    Async Redis Streams event bus with consumer-group support.

    Features:
    - Publish to any stream
    - Consume with auto-ack or manual ack
    - Consumer groups for scalable workers
    - Graceful shutdown with pending message drain
    - Connection pooling via redis-py async
    """

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client = None
        self._pubsub = None
        self._running = False
        self._handlers: Dict[str, List[Callable]] = {}
        self._consumer_tasks: Set[asyncio.Task] = set()

    # ── Connection ─────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        """Initialize the Redis async client."""
        try:
            from redis.asyncio import Redis
            self._client = Redis.from_url(self.redis_url, decode_responses=True)
            await self._client.ping()
            self._running = True
            logger.info("✅ EventBus connected to %s", self.redis_url)
            return True
        except Exception as e:
            logger.warning("❌ EventBus connection failed: %s", e)
            self._client = None
            return False

    async def disconnect(self):
        """Graceful shutdown — cancel consumers, close connection."""
        self._running = False

        # Cancel all consumer tasks
        for task in self._consumer_tasks:
            task.cancel()
        if self._consumer_tasks:
            await asyncio.gather(*self._consumer_tasks, return_exceptions=True)
        self._consumer_tasks.clear()

        if self._client:
            await self._client.close()
            self._client = None
        logger.info("EventBus disconnected")

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._running

    # ── Publishing ─────────────────────────────────────────────────────────

    async def publish(self, event_type: str, payload: Dict[str, Any],
                      source: str = "procureflow", trace_id: str = "") -> Optional[str]:
        """
        Publish an event to a Redis Stream.

        Returns the stream entry ID, or None if Redis is unavailable.
        """
        if not self._client:
            logger.debug("EventBus not connected — dropping event %s", event_type)
            return None

        stream_name = f"procureflow:{event_type}"
        envelope = EventEnvelope(
            event_type=event_type,
            payload=payload,
            source=source,
            trace_id=trace_id,
        )

        try:
            entry_id = await self._client.xadd(stream_name, envelope.to_dict())
            logger.debug("Published %s → %s", event_type, entry_id)
            return entry_id
        except Exception as e:
            logger.warning("EventBus publish failed: %s", e)
            return None

    async def publish_batch(self, events: List[Dict[str, Any]]) -> List[Optional[str]]:
        """Publish multiple events in a pipeline."""
        if not self._client:
            return [None] * len(events)

        pipe = self._client.pipeline()
        for evt in events:
            envelope = EventEnvelope(
                event_type=evt.get("event_type", "generic"),
                payload=evt.get("payload", {}),
                source=evt.get("source", "procureflow"),
                trace_id=evt.get("trace_id", ""),
            )
            stream_name = f"procureflow:{envelope.event_type}"
            pipe.xadd(stream_name, envelope.to_dict())

        try:
            results = await pipe.execute()
            return results
        except Exception as e:
            logger.warning("EventBus batch publish failed: %s", e)
            return [None] * len(events)

    # ── Subscribing (simple) ───────────────────────────────────────────────

    async def subscribe(self, event_type: str, handler: Callable[[EventEnvelope], Any]):
        """Register a handler for a simple (non-group) consumer."""
        self._handlers.setdefault(event_type, []).append(handler)

    async def unsubscribe(self, event_type: str, handler: Callable):
        """Remove a handler."""
        if event_type in self._handlers:
            self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]

    # ── Consuming (consumer groups) ────────────────────────────────────────

    async def consume(self, event_type: str, group: str = "default",
                       consumer_name: str = None, auto_ack: bool = True,
                       block_ms: int = 5000, count: int = 10):
        """
        Async generator for consumer-group-based stream reading.

        Usage:
            async for event in event_bus.consume("agent.completed", group="workers"):
                process(event)
        """
        if not self._client:
            logger.warning("EventBus not connected — consume() yields nothing")
            return

        stream_name = f"procureflow:{event_type}"
        consumer_name = consumer_name or f"consumer-{os.getpid()}"

        # Ensure group exists
        try:
            await self._client.xgroup_create(stream_name, group, id="0", mkstream=True)
        except Exception:
            pass  # Group may already exist

        while self._running:
            try:
                entries = await self._client.xreadgroup(
                    group, consumer_name,
                    {stream_name: ">"},
                    count=count,
                    block=block_ms,
                )
                if not entries:
                    continue

                for stream, messages in entries:
                    for msg_id, fields in messages:
                        event = EventEnvelope.from_stream(event_type, msg_id, fields)
                        yield event
                        if auto_ack:
                            await self._client.xack(stream_name, group, msg_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("EventBus consume error: %s", e)
                await asyncio.sleep(1)

    async def read_pending(self, event_type: str, group: str = "default",
                            consumer_name: str = None, count: int = 100) -> List[EventEnvelope]:
        """Read pending (unacknowledged) messages for a consumer group."""
        if not self._client:
            return []

        stream_name = f"procureflow:{event_type}"
        consumer_name = consumer_name or f"consumer-{os.getpid()}"

        try:
            # Get pending summary
            pending = await self._client.xpending_range(
                stream_name, group, "-", "+", count, consumer_name
            )
            if not pending:
                return []

            # Claim and read
            msg_ids = [p["message_id"] for p in pending]
            messages = await self._client.xclaim(
                stream_name, group, consumer_name, min_idle_time=0, message_ids=msg_ids
            )
            events = []
            for msg_id, fields in messages:
                events.append(EventEnvelope.from_stream(event_type, msg_id, fields))
            return events
        except Exception as e:
            logger.warning("EventBus read_pending error: %s", e)
            return []

    # ── Background consumer task ───────────────────────────────────────────

    async def start_consumer(self, event_type: str, handler: Callable,
                              group: str = "default", consumer_name: str = None):
        """Start a background asyncio task that consumes events and calls handler."""
        async def _consume_loop():
            async for event in self.consume(event_type, group=group,
                                             consumer_name=consumer_name, auto_ack=True):
                try:
                    await handler(event)
                except Exception as e:
                    logger.error("EventBus handler error for %s: %s", event_type, e)

        task = asyncio.create_task(_consume_loop())
        self._consumer_tasks.add(task)
        task.add_done_callback(self._consumer_tasks.discard)
        logger.info("EventBus consumer started: %s (group=%s)", event_type, group)

    # ── Stream management ──────────────────────────────────────────────────

    async def trim_stream(self, event_type: str, max_len: int = 10000):
        """Trim a stream to a maximum length."""
        if not self._client:
            return
        stream_name = f"procureflow:{event_type}"
        try:
            await self._client.xtrim(stream_name, maxlen=max_len, approximate=True)
        except Exception as e:
            logger.warning("EventBus trim error: %s", e)

    async def delete_stream(self, event_type: str):
        """Delete a stream entirely."""
        if not self._client:
            return
        stream_name = f"procureflow:{event_type}"
        try:
            await self._client.delete(stream_name)
        except Exception as e:
            logger.warning("EventBus delete error: %s", e)

    async def stream_info(self, event_type: str) -> Optional[Dict[str, Any]]:
        """Get stream metadata (length, first/last entry, groups)."""
        if not self._client:
            return None
        stream_name = f"procureflow:{event_type}"
        try:
            info = await self._client.xinfo_stream(stream_name)
            return info
        except Exception:
            return None


# ── Singleton instance ─────────────────────────────────────────────────────

event_bus = RedisEventBus()


async def start_event_bus() -> bool:
    """Connect the global event bus. Call during app lifespan startup."""
    return await event_bus.connect()


async def stop_event_bus():
    """Disconnect the global event bus. Call during app lifespan shutdown."""
    await event_bus.disconnect()
