"""
Agent Brain — Inter-Agent Communication Hub.
Agents can:
  - Send/receive messages to/from other agents
  - Share knowledge via the Knowledge Lake
  - Query other agents for data
  - Broadcast to all agents
  - Store and retrieve facts

Architecture:
  AgentBrain (central hub) 
    → Message Queue (in-memory + DB persisted)
    → Agent Registry (who can do what)
    → Knowledge Store (what we know)
    → Query Router (which agent handles which query)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from collections import defaultdict, OrderedDict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.core.watchdog import get_watchdog
from app.db import (
    AgentBrainMessage, AgentResult, AgentJob, AgentLog,
    KnowledgeEntry, get_session,
)
from app.services.project_memory import project_memory_service

logger = logging.getLogger(__name__)


# ── Message Types ────────────────────────────────────────────────────────

class MessageType(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    KNOWLEDGE_SHARE = "knowledge_share"
    QUERY = "query"
    STATUS_CHECK = "status_check"
    WORKFLOW_TRIGGER = "workflow_trigger"
    ERROR = "error"


# ── W-009: Redis-backed knowledge store ────────────────────────────────────
# Replaces the per-process in-memory LRU dict with a store that is backed by
# Redis (shared across API replicas) and falls back to PostgreSQL when Redis is
# unavailable. A small in-process L1 (tiny TTL) absorbs immediate re-reads.
#
# The store depends only on a duck-typed async backend exposing:
#   get(key) -> Optional[str]
#   setex(key, ttl, value)
#   delete(key)
#   sadd(key, member) / srem(key, member) / smembers(key) -> list[str]
#   scan_iter(match) -> async iterable[str]
# `redis.asyncio.Redis` satisfies this; `_MemoryBackend` is the in-process
# fallback (used when Redis is not configured) and the test double.


class _MemoryBackend:
    """In-process Redis stand-in: dict + per-key TTL + set indexes."""

    def __init__(self):
        self._data: Dict[str, Any] = {}  # key -> (value, expiry_ts|None)
        self._sets: Dict[str, Set[str]] = {}

    async def get(self, key: str) -> Optional[str]:
        item = self._data.get(key)
        if item is None:
            return None
        value, expiry = item
        if expiry is not None and time.time() > expiry:
            self._data.pop(key, None)
            return None
        return value

    async def setex(self, key: str, ttl: int, value: str) -> None:
        expiry = time.time() + ttl if ttl else None
        self._data[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def sadd(self, key: str, member: str) -> None:
        self._sets.setdefault(key, set()).add(member)

    async def srem(self, key: str, member: str) -> None:
        s = self._sets.get(key)
        if s:
            s.discard(member)

    async def smembers(self, key: str) -> List[str]:
        return list(self._sets.get(key, set()))

    async def scan_iter(self, match: str):
        import re

        import fnmatch

        rx = re.compile("^" + fnmatch.translate(match) + "$")
        for k in list(self._data.keys()):
            if rx.match(k):
                yield k


class _FailingBackend:
    """Simulates a Redis outage: every call raises so the store degrades."""

    async def get(self, key: str):
        raise RuntimeError("redis unavailable")

    async def setex(self, key: str, ttl: int, value: str):
        raise RuntimeError("redis unavailable")

    async def delete(self, key: str):
        raise RuntimeError("redis unavailable")

    async def sadd(self, key: str, member: str):
        raise RuntimeError("redis unavailable")

    async def srem(self, key: str, member: str):
        raise RuntimeError("redis unavailable")

    async def smembers(self, key: str):
        raise RuntimeError("redis unavailable")

    async def scan_iter(self, match: str):
        raise RuntimeError("redis unavailable")
        yield  # pragma: no cover - makes this an async generator


class RedisKnowledgeStore:
    """Redis-backed knowledge cache with an L1 in-process layer.

    - `get` checks L1 (tiny TTL) then Redis, then returns None (caller falls to PG).
    - `set` writes L1 + Redis (SETEX with per-entry-type TTL) + index sets.
    - `query` gathers candidates from Redis index sets / SCAN, filters, returns them.
    - `invalidate(entry_type, tender_id)` DELs matching keys + clears index sets.
    Degrades to PostgreSQL-only automatically when the backend raises.
    """

    HOT_ENTRY_TYPES = ("tender_document", "boq_text", "tds_text")
    DEFAULT_TTL_HOT = 3600
    DEFAULT_TTL_COLD = 86400
    DEFAULT_L1_TTL_SECONDS = 0.01
    DEFAULT_L1_MAX = 2000

    def __init__(self, redis_client: Any = None, settings: Any = None):
        # If no Redis client is provided we keep an in-process backend so a
        # single replica still benefits from caching (no cross-replica sharing).
        self._backend = redis_client if redis_client is not None else _MemoryBackend()
        self._has_redis = redis_client is not None
        self._l1: "OrderedDict[str, Any]" = OrderedDict()
        self._l1_ttl = (
            float(getattr(settings, "KNOWLEDGE_CACHE_L1_TTL_MS", self.DEFAULT_L1_TTL_SECONDS * 1000)) / 1000.0
        )
        self._l1_max = int(getattr(settings, "KNOWLEDGE_CACHE_L1_MAX", self.DEFAULT_L1_MAX))
        self._ttl_hot = int(getattr(settings, "KNOWLEDGE_CACHE_TTL_HOT", self.DEFAULT_TTL_HOT))
        self._ttl_cold = int(getattr(settings, "KNOWLEDGE_CACHE_TTL_COLD", self.DEFAULT_TTL_COLD))
        self._degraded = False

    # ── key / ttl helpers ──────────────────────────────────────────────────
    @staticmethod
    def _key(entry_type: str, tender_id: Optional[str], entry_id: str) -> str:
        return f"kb:{entry_type}:{tender_id or 'global'}:{entry_id}"

    def _ttl_for(self, entry_type: str) -> int:
        return self._ttl_hot if entry_type in self.HOT_ENTRY_TYPES else self._ttl_cold

    @staticmethod
    def _pattern(entry_type: Optional[str], tender_id: Optional[str]) -> str:
        if entry_type and tender_id:
            return f"kb:{entry_type}:{tender_id}:*"
        if entry_type:
            return f"kb:{entry_type}:*"
        if tender_id:
            return f"kb:*:{tender_id}:*"
        return "kb:*"

    def _record(self, hit: bool, backend: str) -> None:
        try:
            from app.services.telemetry import get_metrics

            m = get_metrics()
            if m is not None:
                m.record_knowledge_cache(hit, backend)
        except Exception:
            pass

    # ── L1 layer ───────────────────────────────────────────────────────────
    def _l1_get(self, entry_id: str) -> Optional[Dict[str, Any]]:
        item = self._l1.get(entry_id)
        if item is None:
            return None
        entry, expiry = item
        if expiry is not None and time.time() > expiry:
            self._l1.pop(entry_id, None)
            return None
        self._l1.move_to_end(entry_id)
        return entry

    def _l1_set(self, entry_id: str, entry: Dict[str, Any]) -> None:
        self._l1.pop(entry_id, None)
        self._l1[entry_id] = (entry, time.time() + self._l1_ttl)
        while len(self._l1) > self._l1_max:
            self._l1.popitem(last=False)

    def _l1_invalidate(self, entry_type: Optional[str], tender_id: Optional[str]) -> None:
        if not entry_type and not tender_id:
            self._l1.clear()
            return
        for key in list(self._l1.keys()):
            entry = self._l1[key][0]
            if entry_type and entry.get("entry_type") != entry_type:
                continue
            if tender_id and entry.get("tender_id") != tender_id:
                continue
            self._l1.pop(key, None)

    def _l1_query(
        self,
        entry_type: Optional[str],
        tender_id: Optional[str],
        agent_id: Optional[str],
        tags: Optional[List[str]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for entry, _expiry in list(self._l1.values()):
            if self._matches(entry, entry_type, tender_id, agent_id, tags):
                out.append(entry)
                if len(out) >= limit:
                    break
        return out

    # ── public API ─────────────────────────────────────────────────────────
    async def set(
        self,
        entry_id: str,
        entry: Dict[str, Any],
        entry_type: str,
        tender_id: Optional[str],
    ) -> None:
        self._l1_set(entry_id, entry)
        if not self._has_redis or self._degraded:
            return
        try:
            key = self._key(entry_type, tender_id, entry_id)
            payload = json.dumps(entry, default=str)
            await self._backend.setex(key, self._ttl_for(entry_type), payload)
            await self._backend.sadd(f"kb:type:{entry_type}", key)
            if tender_id:
                await self._backend.sadd(f"kb:tender:{tender_id}", key)
        except Exception as exc:
            logger.warning("Knowledge cache Redis write failed (degrading to PG): %s", exc)
            self._degraded = True

    async def get(
        self,
        entry_id: str,
        entry_type: str,
        tender_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if self._degraded:
            # Cache considered unreliable once Redis has failed; caller falls
            # back to PostgreSQL. Skip L1 so we don't serve possibly-stale data.
            self._record(False, "postgres")
            return None
        cached = self._l1_get(entry_id)
        if cached is not None:
            self._record(True, "l1")
            return cached
        if not self._has_redis:
            # Single-replica in-process mode: no backend, L1 is the only cache.
            return None
        try:
            key = self._key(entry_type, tender_id, entry_id)
            val = await self._backend.get(key)
            if val is not None:
                entry = json.loads(val)
                self._l1_set(entry_id, entry)
                self._record(True, "redis")
                return entry
        except Exception as exc:
            logger.warning("Knowledge cache Redis read failed (degrading to PG): %s", exc)
            self._degraded = True
        self._record(False, "postgres")
        return None

    @staticmethod
    def _matches(
        entry: Dict[str, Any],
        entry_type: Optional[str],
        tender_id: Optional[str],
        agent_id: Optional[str],
        tags: Optional[List[str]],
    ) -> bool:
        if entry_type and entry.get("entry_type") != entry_type:
            return False
        if tender_id and entry.get("tender_id") != tender_id:
            return False
        if agent_id:
            src = entry.get("agent_id") or entry.get("source")
            if src != agent_id:
                return False
        if tags:
            row_tags = entry.get("tags", []) or []
            if not all(t in row_tags for t in tags):
                return False
        return True

    async def query(
        self,
        entry_type: Optional[str] = None,
        tender_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        if self._degraded:
            return []
        if not self._has_redis:
            # Single-replica in-process mode: serve what L1 holds.
            return self._l1_query(entry_type, tender_id, agent_id, tags, limit)
        try:
            keys: Set[str] = set()
            if entry_type:
                keys |= set(await self._backend.smembers(f"kb:type:{entry_type}"))
            if tender_id:
                keys |= set(await self._backend.smembers(f"kb:tender:{tender_id}"))
            if not keys:
                async for k in self._backend.scan_iter(self._pattern(entry_type, tender_id)):
                    keys.add(k)
            entries: List[Dict[str, Any]] = []
            for key in keys:
                val = await self._backend.get(key)
                if val is None:
                    continue
                entry = json.loads(val)
                if self._matches(entry, entry_type, tender_id, agent_id, tags):
                    entries.append(entry)
                    if len(entries) >= limit:
                        break
            if entries:
                self._record(True, "redis")
            return entries
        except Exception as exc:
            logger.warning("Knowledge cache Redis query failed (degrading to PG): %s", exc)
            self._degraded = True
            return []

    async def invalidate(
        self,
        entry_type: Optional[str] = None,
        tender_id: Optional[str] = None,
    ) -> None:
        self._l1_invalidate(entry_type, tender_id)
        if not self._has_redis or self._degraded:
            return
        try:
            async for key in self._backend.scan_iter(self._pattern(entry_type, tender_id)):
                await self._backend.delete(key)
            if entry_type:
                await self._backend.delete(f"kb:type:{entry_type}")
            if tender_id:
                await self._backend.delete(f"kb:tender:{tender_id}")
        except Exception as exc:
            logger.warning("Knowledge cache Redis invalidate failed: %s", exc)
            self._degraded = True

    def __len__(self) -> int:
        return len(self._l1)

    def get_info(self) -> Dict[str, Any]:
        """Return cache backend metadata for health/stats reporting."""
        return {
            "has_redis": self._has_redis,
            "degraded": self._degraded,
            "l1_size": len(self._l1),
            "l1_max": self._l1_max,
            "ttl_hot": self._ttl_hot,
            "ttl_cold": self._ttl_cold,
        }


@dataclass
class BrainMessage:
    """Standard message format for Agent Brain communication."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    recipient_id: str = ""  # empty = broadcast
    message_type: str = MessageType.REQUEST
    subject: str = ""
    body: Dict[str, Any] = field(default_factory=dict)
    thread_id: str = ""
    response_to: str = ""
    priority: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "BrainMessage":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AgentCapability:
    """What an agent can do."""
    agent_id: str
    agent_name: str
    description: str
    input_types: List[str] = field(default_factory=list)  # What data it needs
    output_types: List[str] = field(default_factory=list)  # What data it produces
    can_query: List[str] = field(default_factory=list)  # Query types it can answer
    version: str = "1.0.0"
    is_available: bool = True


class AgentBrain:
    """
    Central nervous system for the multi-agent procurement intelligence platform.
    
    Features:
    - Agent Registry: Knows all agents and their capabilities
    - Message Bus: Async pub/sub message passing
    - Knowledge Store: Shared facts that agents can read/write
    - Query Router: Routes questions to the right agent
    - Workflow Triggers: Chain agent executions
    - Status Monitoring: Check agent health
    """
    
    _MAX_KNOWLEDGE_ENTRIES = 2000

    # W-007: a single message must be processed within this window; otherwise
    # the consumer drops it (logs + marks failed) so one slow handler cannot
    # stall the entire message bus.
    MESSAGE_PROCESSING_TIMEOUT_SECONDS = int(os.getenv("AGENT_MESSAGE_TIMEOUT_SECONDS", "60"))

    def __init__(self, db_session_factory=None):
        self._agents: Dict[str, AgentCapability] = {}
        self._agent_instances: Dict[str, Any] = {}
        self._subscriptions: Dict[str, List[str]] = defaultdict(list)  # agent_id → [subscribed message types]
        self._message_handlers: Dict[str, Callable] = {}
        # W-009: Redis-backed knowledge cache (L1 + Redis, PG fallback).
        from app.core.config import settings as _brain_settings

        _redis_client = None
        try:
            if _brain_settings.KNOWLEDGE_CACHE_ENABLED and _brain_settings.REDIS_URL:
                import redis.asyncio as _aioredis

                _redis_client = _aioredis.Redis.from_url(_brain_settings.REDIS_URL, decode_responses=True)
        except Exception as exc:
            logger.warning("Knowledge cache Redis client unavailable (local cache only): %s", exc)
            _redis_client = None
        self._knowledge_store = RedisKnowledgeStore(redis_client=_redis_client, settings=_brain_settings)
        self._knowledge_cache_loaded = False
        
        self.db = db_session_factory or get_session
        self._running = False
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task = None
        self._event_consumer_task = None
        self._event_bus_connected = False
        self._event_origin_id = f"brain-{uuid.uuid4().hex}"
        self._idle_task = None
        self._project_memory = project_memory_service
        self._project_memory.bootstrap_project_context()
        
        logger.info("🧠 Agent Brain initialized")
    
    # ── Agent Registry ──────────────────────────────────────────────────
    
    def register_agent(self, agent_id: str, instance: Any, 
                       name: str = "", description: str = "",
                       input_types: List[str] = None,
                       output_types: List[str] = None,
                       can_query: List[str] = None,
                       version: str = "1.0.0"):
        """Register an agent with the brain."""
        self._agent_instances[agent_id] = instance
        
        cap = AgentCapability(
            agent_id=agent_id,
            agent_name=name or getattr(instance, "agent_name", agent_id),
            description=description or getattr(instance, "description", ""),
            input_types=input_types or [],
            output_types=output_types or [],
            can_query=can_query or [],
            version=version or getattr(instance, "version", "1.0.0"),
        )
        self._agents[agent_id] = cap
        logger.info(f"  ✓ Agent registered: {cap.agent_name} ({agent_id}) v{cap.version}")
        
        # Auto-register default message handler for inter-agent communication
        async def _default_handler(msg):
            try:
                context = dict(msg.body) if msg.body else {}
                context["_message"] = msg
                context["tender_id"] = context.get("tender_id", "")
                result = await instance.run(context)
                if hasattr(result, 'output'):
                    return result.output if isinstance(result.output, dict) else {"result": str(result.output)}
                if isinstance(result, dict):
                    return result
                return {"result": str(result)}
            except Exception as e:
                logger.error(f"Default handler error for {agent_id}: {e}")
                return {"error": str(e)}
        
        self._message_handlers[agent_id] = _default_handler
        return cap
    
    def register_agents(self, *agents: Any):
        """Register multiple agents at once."""
        for agent in agents:
            agent_id = getattr(agent, "agent_id", None) or getattr(agent, "__class__").__name__
            self.register_agent(agent_id, agent)
    
    def get_agent(self, agent_id: str) -> Optional[Any]:
        """Get agent instance by ID."""
        return self._agent_instances.get(agent_id)
    
    def get_capability(self, agent_id: str) -> Optional[AgentCapability]:
        """Get agent capability info."""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> List[AgentCapability]:
        """List all registered agents."""
        return list(self._agents.values())
    
    def find_agents_by_capability(self, query_type: str) -> List[AgentCapability]:
        """Find agents that can handle a specific query type."""
        return [
            a for a in self._agents.values()
            if query_type in a.can_query
        ]
    
    # ── Message Bus ─────────────────────────────────────────────────────
    
    async def _persist_message(self, message: BrainMessage) -> None:
        """Persist a message without implying delivery semantics."""
        self._validate_message(message)
        try:
            async with self.db() as session:
                # Ensure body is JSON-serializable
                import json as _json
                body_safe = message.body
                if not isinstance(body_safe, (dict, list, str, int, float, bool, type(None))):
                    body_safe = str(body_safe)
                elif isinstance(body_safe, dict):
                    try:
                        _json.dumps(body_safe)
                    except (TypeError, ValueError):
                        body_safe = {k: (str(v) if not isinstance(v, (dict, list, str, int, float, bool, type(None))) else v) for k, v in body_safe.items()}
                        # Try again with deeper serialization
                        try:
                            _json.dumps(body_safe)
                        except (TypeError, ValueError):
                            body_safe = _json.loads(_json.dumps(body_safe, default=str))
                db_msg = AgentBrainMessage(
                    id=message.id,
                    sender_id=message.sender_id,
                    recipient_id=message.recipient_id,
                    message_type=message.message_type.value if hasattr(message.message_type, "value") else str(message.message_type),
                    subject=message.subject,
                    body=body_safe,
                    thread_id=message.thread_id or message.id,
                    response_to=message.response_to,
                    status="sent",
                )
                session.add(db_msg)
                await session.commit()
        except Exception as e:
            logger.warning(f"Could not persist message to DB: {e}")

    async def send_message(self, message: BrainMessage) -> bool:
        """Send a message through the brain. Async with DB persistence."""
        self._validate_message(message)
        await self._persist_message(message)
        await self._publish_message_event(message, event_action="send")
        
        # Queue for delivery
        await self._message_queue.put(message)
        return True

    async def _publish_message_event(self, message: BrainMessage, event_action: str = "send") -> None:
        """Publish a durable Redis Stream event when the event bus is available."""
        if not self._event_bus_connected:
            return
        try:
            from app.core.event_bus import event_bus

            await event_bus.publish(
                "brain.message",
                {
                    "action": event_action,
                    "origin_id": self._event_origin_id,
                    "message": message.to_dict(),
                },
                source=message.sender_id or "agent-brain",
                trace_id=message.thread_id or message.id,
            )
        except Exception as exc:
            logger.debug("Could not publish brain message event %s: %s", message.id, exc)

    async def _consume_message_events(self) -> None:
        """Replay Redis Stream brain messages into this process queue."""
        try:
            from app.core.event_bus import event_bus

            async for event in event_bus.consume(
                "brain.message",
                group="agent-brain",
                consumer_name=f"brain-{uuid.uuid4().hex[:8]}",
                auto_ack=True,
                count=10,
            ):
                payload = event.payload or {}
                if payload.get("origin_id") == self._event_origin_id:
                    continue
                if payload.get("action") != "send":
                    continue
                raw_message = payload.get("message") or {}
                try:
                    msg = BrainMessage.from_dict(raw_message)
                    self._validate_message(msg)
                except Exception as exc:
                    logger.warning("Dropping invalid brain message event %s: %s", event.event_id, exc)
                    continue
                await self._message_queue.put(msg)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Brain Redis event consumer stopped: %s", exc)

    def _validate_message(self, message: BrainMessage) -> None:
        if not isinstance(message.sender_id, str) or not message.sender_id.strip():
            raise ValueError("BrainMessage.sender_id is required")
        if not isinstance(message.recipient_id, str):
            raise ValueError("BrainMessage.recipient_id must be a string")
        msg_type = message.message_type.value if hasattr(message.message_type, "value") else str(message.message_type)
        valid_types = {item.value for item in MessageType}
        if msg_type not in valid_types:
            raise ValueError(f"Unknown BrainMessage.message_type: {msg_type}")
        if not isinstance(message.body, dict):
            raise ValueError("BrainMessage.body must be a JSON object")
        if len(message.subject or "") > 255:
            raise ValueError("BrainMessage.subject must be 255 characters or fewer")

    async def _mark_message_status(self, message_id: str, status: str) -> None:
        try:
            async with self.db() as session:
                await session.execute(
                    text("UPDATE agent_brain_messages SET status = :status WHERE id = :id"),
                    {"status": status, "id": message_id},
                )
                await session.commit()
        except Exception as exc:
            logger.debug("Could not mark brain message %s as %s: %s", message_id, status, exc)

    async def _replay_pending_messages(self, limit: int = 100) -> None:
        """Queue persisted messages that were sent before a previous process stopped."""
        try:
            async with self.db() as session:
                result = await session.execute(
                    select(AgentBrainMessage)
                    .where(AgentBrainMessage.status.in_(["sent", "queued"]))
                    .order_by(AgentBrainMessage.created_at.asc())
                    .limit(limit)
                )
                rows = result.scalars().all()
        except Exception as exc:
            logger.debug("Could not replay pending brain messages: %s", exc)
            return

        for row in rows:
            body = row.body if isinstance(row.body, dict) else {}
            msg = BrainMessage(
                id=row.id,
                sender_id=row.sender_id,
                recipient_id=row.recipient_id or "",
                message_type=row.message_type,
                subject=row.subject or "",
                body=body,
                thread_id=row.thread_id or row.id,
                response_to=row.response_to or "",
            )
            try:
                self._validate_message(msg)
            except ValueError:
                await self._mark_message_status(row.id, "failed")
                continue
            await self._message_queue.put(msg)
    
    async def broadcast(self, sender_id: str, subject: str, body: Dict, 
                        exclude: List[str] = None) -> List[str]:
        """Broadcast a message to all agents."""
        msg = BrainMessage(
            sender_id=sender_id,
            recipient_id="*",  # broadcast
            message_type=MessageType.BROADCAST,
            subject=subject,
            body=body,
        )
        msg.body = {
            **(body or {}),
            "_broadcast_exclude": list(exclude or []),
        }
        delivered = [
            agent_id
            for agent_id in self._agent_instances
            if agent_id != sender_id and agent_id not in (exclude or [])
        ]
        await self.send_message(msg)
        return delivered
    
    async def request(self, sender_id: str, recipient_id: str, 
                      subject: str, body: Dict, timeout: float = 30.0) -> Optional[Dict]:
        """Send a request to a specific agent and wait for response."""
        thread_id = str(uuid.uuid4())
        msg = BrainMessage(
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=MessageType.REQUEST,
            subject=subject,
            body=body,
            thread_id=thread_id,
        )
        await self._persist_message(msg)
        await self._publish_message_event(msg, event_action="request")
        
        # If the agent has a handler, call it and return result
        if recipient_id in self._message_handlers:
            try:
                response = await asyncio.wait_for(
                    self._message_handlers[recipient_id](msg),
                    timeout=timeout
                )
                # Send response back to sender
                resp_msg = BrainMessage(
                    sender_id=recipient_id,
                    recipient_id=sender_id,
                    message_type=MessageType.RESPONSE,
                    subject=f"RE: {subject}",
                    body=response if isinstance(response, dict) else {"result": response},
                    thread_id=thread_id,
                    response_to=msg.id,
                )
                await self._persist_message(resp_msg)
                await self._publish_message_event(resp_msg, event_action="response")
                await self._mark_message_status(msg.id, "delivered")
                return response
            except asyncio.TimeoutError:
                logger.warning(f"Request to {recipient_id} timed out after {timeout}s")
                await self._mark_message_status(msg.id, "failed")
                return {"error": "timeout", "message": f"Agent {recipient_id} did not respond in {timeout}s"}
            except Exception as e:
                logger.error(f"Error handling request by {recipient_id}: {e}")
                await self._mark_message_status(msg.id, "failed")
                return {"error": str(e)}
        else:
            logger.warning(f"No handler registered for {recipient_id}")
            await self._mark_message_status(msg.id, "failed")
            return {"error": f"No handler for {recipient_id}"}
    
    def on_message(self, agent_id: str):
        """Decorator to register a message handler for an agent."""
        def decorator(func):
            self._message_handlers[agent_id] = func
            return func
        return decorator
    
    def subscribe(self, agent_id: str, message_types: List[str]):
        """Subscribe an agent to specific message types."""
        self._subscriptions[agent_id].extend(message_types)
    
    # ── Knowledge Store ─────────────────────────────────────────────────
    
    async def store_knowledge(self, agent_id: str, entry_type: str, 
                               tender_id: str, data: Dict,
                               summary: str = "", tags: List[str] = None) -> str:
        """Store a knowledge entry shared by an agent."""
        entry_id = str(uuid.uuid4())
        normalized_tender_id = tender_id or None
        serialized_data = data if isinstance(data, dict) else {"value": data}
        memory_text = "\n".join(
            part for part in [
                summary or "",
                json.dumps(serialized_data, ensure_ascii=False, default=str),
            ] if part
        )
        
        # Persist to DB using the live schema that exists in this repo's database.
        try:
            checksum = hashlib.sha256(memory_text.encode("utf-8")).hexdigest()
            async with self.db() as session:
                await session.execute(
                    text(
                        """
                        INSERT INTO knowledge_entries
                            (id, entry_type, tender_id, data, checksum, created_at, updated_at)
                        VALUES
                            (:id, :entry_type, :tender_id, :data, :checksum, NOW(), NOW())
                        """
                    ),
                    {
                        "id": entry_id,
                        "entry_type": entry_type,
                        "tender_id": normalized_tender_id,
                        "data": json.dumps(
                            {
                                "payload": serialized_data,
                                "summary": summary,
                                "source": agent_id,
                                "tags": tags or [],
                                "embedding_id": entry_id,
                                "embedding_model": self._project_memory.model_name,
                            },
                            ensure_ascii=False,
                            default=str,
                        ),
                        "checksum": checksum,
                    },
                )
                await session.commit()
        except Exception as e:
            logger.warning(f"Could not store knowledge in DB: {e}")
        
        # Cache (Redis-backed; degrades to PG on Redis failure)
        await self._knowledge_store.set(
            entry_id,
            {
                "entry_id": entry_id,
                "agent_id": agent_id,
                "entry_type": entry_type,
                "tender_id": normalized_tender_id,
                "data": data,
                "summary": summary,
                "tags": tags or [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            entry_type,
            normalized_tender_id,
        )
        await self._project_memory.upsert_async(
            entry_id=entry_id,
            text=memory_text,
            metadata={
                "entry_type": entry_type,
                "agent_id": agent_id,
                "tender_id": normalized_tender_id,
                "summary": summary or json.dumps(serialized_data, ensure_ascii=False, default=str)[:500],
                "tags": tags or [],
            },
        )

        logger.info(f"  📚 Agent {agent_id} shared {entry_type} knowledge for {normalized_tender_id or 'global'}")
        return entry_id

    async def _hydrate_knowledge_row(self, row: Any) -> Optional[Dict[str, Any]]:
        entry_id = row[0]
        row_data = row[3]
        if isinstance(row_data, str):
            try:
                row_data = json.loads(row_data)
            except Exception:
                row_data = {"payload": row_data}
        if not isinstance(row_data, dict):
            row_data = {"payload": row_data}

        entry = {
            "entry_id": entry_id,
            "entry_type": row[1],
            "tender_id": row[2],
            "data": row_data.get("payload", row_data),
            "summary": row_data.get("summary", ""),
            "tags": row_data.get("tags", []),
            "source": row_data.get("source"),
            "agent_id": row_data.get("source"),
            "created_at": str(row[4]),
        }
        await self._knowledge_store.set(entry_id, entry, entry["entry_type"], entry["tender_id"])
        return entry

    async def ensure_knowledge_loaded(self, limit: int = 1000, force: bool = False) -> None:
        if self._knowledge_cache_loaded and not force:
            return
        try:
            async with self.db() as session:
                result = await session.execute(
                    text(
                        """
                        SELECT id, entry_type, tender_id, data, created_at
                        FROM knowledge_entries
                        ORDER BY created_at DESC NULLS LAST, updated_at DESC NULLS LAST
                        LIMIT :limit
                        """
                    ),
                    {"limit": limit},
                )
                rows = result.fetchall()
                for row in rows:
                    entry = await self._hydrate_knowledge_row(row)
                    if not entry:
                        continue
                    memory_text = "\n".join(
                        part for part in [
                            entry.get("summary", ""),
                            json.dumps(entry.get("data", {}), ensure_ascii=False, default=str),
                        ] if part
                    )
                    await self._project_memory.upsert_async(
                        entry_id=entry["entry_id"],
                        text=memory_text,
                        metadata={
                            "entry_type": entry.get("entry_type"),
                            "agent_id": entry.get("source"),
                            "tender_id": entry.get("tender_id"),
                            "summary": entry.get("summary", ""),
                            "tags": entry.get("tags", []),
                        },
                    )
            self._knowledge_cache_loaded = True
        except Exception as e:
            logger.warning(f"Could not warm brain knowledge cache: {e}")

    async def query_knowledge(self, entry_type: str = None, 
                               tender_id: str = None,
                               tags: List[str] = None,
                               limit: int = 100,
                               search_text: str = "",
                               agent_id: str = None) -> List[Dict]:
        """Query the knowledge store."""
        await self.ensure_knowledge_loaded(limit=max(limit * 5, 500))
        if search_text:
            semantic_hits = await self._project_memory.search_async(
                search_text,
                limit=limit,
                filters={
                    "entry_type": entry_type,
                    "tender_id": tender_id,
                    "agent_id": agent_id,
                },
            )
            if semantic_hits:
                results = []
                for hit in semantic_hits:
                    meta = hit.get("metadata", {})
                    results.append({
                        "entry_id": hit["entry_id"],
                        "entry_type": meta.get("entry_type"),
                        "tender_id": meta.get("tender_id"),
                        "summary": meta.get("summary"),
                        "tags": meta.get("tags", []),
                        "source": meta.get("agent_id"),
                        "score": hit.get("score"),
                        "text_preview": hit.get("text_preview"),
                    })
                return results

        results = await self._knowledge_store.query(
            entry_type=entry_type,
            tender_id=tender_id,
            agent_id=agent_id,
            tags=tags,
            limit=limit,
        )

        # If not in cache, try DB
        if not results:
            try:
                async with self.db() as session:
                    clauses = []
                    params: Dict[str, Any] = {"limit": limit}
                    if entry_type:
                        clauses.append("entry_type = :entry_type")
                        params["entry_type"] = entry_type
                    if tender_id:
                        clauses.append("tender_id = :tender_id")
                        params["tender_id"] = tender_id

                    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
                    result = await session.execute(
                        text(
                            # sql-ok: WHERE clause fragments from code constants; values bound
                            f"""
                            SELECT id, entry_type, tender_id, data, created_at
                            FROM knowledge_entries
                            {where_sql}
                            ORDER BY created_at DESC NULLS LAST, updated_at DESC NULLS LAST
                            LIMIT :limit
                            """
                        ),
                        params,
                    )
                    for row in result.fetchall():
                        entry = await self._hydrate_knowledge_row(row)
                        if not entry:
                            continue
                        source = entry.get("source")
                        row_tags = entry.get("tags", [])
                        if agent_id and source != agent_id:
                            continue
                        if tags and not all(tag in row_tags for tag in tags):
                            continue
                        results.append(entry)
            except Exception as e:
                logger.warning(f"Could not query knowledge DB: {e}")
        
        return results
    
    async def invalidate_knowledge(
        self,
        entry_type: Optional[str] = None,
        tender_id: Optional[str] = None,
    ) -> None:
        """W-009: invalidate cached knowledge by entry_type and/or tender_id.

        Removes all matching entries from the Redis-backed cache (and L1) so the
        next query re-reads from PostgreSQL.
        """
        await self._knowledge_store.invalidate(entry_type, tender_id)
    
    # ── Knowledge Graph (T-031 / ENT-04a) ────────────────────────────────
    # Persistent PostgreSQL graph alongside the Redis knowledge cache.
    # Agents call record_graph_relationship() to register structural links
    # (contractor→tender, award→contractor, etc.) so the graph survives restarts
    # and is queryable across API replicas.

    async def record_graph_relationship(
        self,
        source_type: str,
        source_id: str,
        source_label: str,
        target_type: str,
        target_id: str,
        target_label: str,
        edge_type: str,
        tenant_id: str,
        weight: float = 1.0,
        meta: Optional[Dict] = None,
    ) -> Optional[str]:
        """Upsert nodes and a directed edge in the persistent knowledge graph.

        Returns the edge ID on success, None on failure (never raises — graph
        persistence is a secondary concern; callers must not depend on the return
        value for correctness).
        """
        def _sync_work():
            from sqlalchemy.orm import Session as _Session
            from app.db.database import get_sync_engine as _eng
            from app.services.knowledge_graph_service import KnowledgeGraphService as _KGS
            engine = _eng()
            with _Session(engine) as session:
                svc = _KGS(session)
                src_list = svc.find_nodes_by_external_id(source_id, node_type=source_type)
                src = src_list[0] if src_list else svc.create_node(
                    source_type, source_id, source_label, tenant_id
                )
                tgt_list = svc.find_nodes_by_external_id(target_id, node_type=target_type)
                tgt = tgt_list[0] if tgt_list else svc.create_node(
                    target_type, target_id, target_label, tenant_id
                )
                edge = svc.create_edge(
                    src.id, tgt.id, edge_type, tenant_id, weight=weight, meta_json=meta or {}
                )
                session.commit()
                return edge.id

        loop = asyncio.get_event_loop()
        try:
            edge_id = await loop.run_in_executor(None, _sync_work)
            logger.debug("kg_edge recorded: %s→%s [%s]", source_id, target_id, edge_type)
            return edge_id
        except Exception as exc:
            logger.warning("record_graph_relationship failed (%s→%s %s): %s", source_id, target_id, edge_type, exc)
            return None

    async def query_graph_neighbors(
        self,
        node_type: str,
        external_id: str,
        tenant_id: str,
        direction: str = "outgoing",
    ) -> List[Dict[str, Any]]:
        """Return neighbors of a node from the persistent knowledge graph.

        direction: 'outgoing' (edges FROM this node) or 'incoming' (edges TO this node).
        Returns a list of dicts with keys: edge_type, weight, neighbor_type, neighbor_id, neighbor_label.
        Falls back to empty list on any error.
        """
        def _sync_work():
            from sqlalchemy.orm import Session as _Session
            from app.db.database import get_sync_engine as _eng
            from app.services.knowledge_graph_service import KnowledgeGraphService as _KGS
            engine = _eng()
            with _Session(engine) as session:
                svc = _KGS(session)
                nodes = svc.find_nodes_by_external_id(external_id, node_type=node_type)
                if not nodes:
                    return []
                node = nodes[0]
                if direction == "incoming":
                    edges = svc.get_incoming_edges(node.id)
                    results = []
                    for e in edges:
                        nb = svc.get_node(e.source_node_id)
                        if nb:
                            results.append({
                                "edge_type": e.edge_type,
                                "weight": e.weight,
                                "neighbor_type": nb.node_type,
                                "neighbor_id": nb.external_id,
                                "neighbor_label": nb.label,
                            })
                    return results
                else:
                    edges = svc.get_outgoing_edges(node.id)
                    results = []
                    for e in edges:
                        nb = svc.get_node(e.target_node_id)
                        if nb:
                            results.append({
                                "edge_type": e.edge_type,
                                "weight": e.weight,
                                "neighbor_type": nb.node_type,
                                "neighbor_id": nb.external_id,
                                "neighbor_label": nb.label,
                            })
                    return results

        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, _sync_work)
        except Exception as exc:
            logger.warning("query_graph_neighbors failed (%s %s): %s", node_type, external_id, exc)
            return []

    async def get_agent_result(self, agent_id: str, tender_id: str = None,
                                request_id: str = None) -> Optional[Dict]:
        """Get the latest result from a specific agent."""
        try:
            async with self.db() as session:
                query = select(AgentResult).where(
                    AgentResult.agent_id == agent_id
                )
                if tender_id:
                    query = query.where(AgentResult.tender_id == tender_id)
                if request_id:
                    query = query.where(AgentResult.request_id == request_id)
                
                query = query.order_by(AgentResult.created_at.desc()).limit(1)
                result = await session.execute(query)
                row = result.scalar_one_or_none()
                if row:
                    return {
                        "agent_id": row.agent_id,
                        "tender_id": row.tender_id,
                        "status": row.status,
                        "output": row.output,
                        "execution_time_ms": row.execution_time_ms,
                        "created_at": str(row.created_at),
                    }
        except Exception as e:
            logger.warning(f"Could not query agent result: {e}")
        return None
    
    # ── Message Processing ──────────────────────────────────────────────
    
    async def _process_messages(self):
        """Background task to process queued messages."""
        while self._running:
            try:
                msg = await asyncio.wait_for(self._message_queue.get(), timeout=1.0)
                try:
                    # W-007: bound per-message processing so a single slow
                    # handler cannot stall the bus. On timeout we drop the
                    # message (logged, marked failed) and keep consuming.
                    await asyncio.wait_for(
                        self._deliver_message(msg),
                        timeout=self.MESSAGE_PROCESSING_TIMEOUT_SECONDS,
                    )
                    await self._mark_message_status(msg.id, "delivered")
                except asyncio.TimeoutError:
                    logger.error(
                        "Brain message %s exceeded processing timeout (%ss); skipping",
                        msg.id, self.MESSAGE_PROCESSING_TIMEOUT_SECONDS,
                    )
                    try:
                        await self._mark_message_status(msg.id, "failed")
                    except Exception:
                        pass
                except Exception:
                    # Mark as failed but don't re-raise — keep the loop running
                    try:
                        await self._mark_message_status(msg.id, "failed")
                    except Exception:
                        pass
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    async def _deliver_message(self, msg: BrainMessage):
        """Deliver a message to its recipient(s)."""
        if msg.recipient_id == "*" or not msg.recipient_id:
            # Broadcast to all
            excluded = set((msg.body or {}).get("_broadcast_exclude", []) or [])
            semaphore = asyncio.Semaphore(10)

            async def deliver_one(agent_id: str, handler: Callable):
                async with semaphore:
                    try:
                        await asyncio.wait_for(handler(msg), timeout=30.0)
                    except Exception as e:
                        logger.error(f"Broadcast delivery error to {agent_id}: {e}")

            tasks = []
            for agent_id, handler in self._message_handlers.items():
                if agent_id != msg.sender_id and agent_id not in excluded:
                    tasks.append(asyncio.create_task(deliver_one(agent_id, handler)))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        elif msg.recipient_id in self._message_handlers:
            try:
                await asyncio.wait_for(self._message_handlers[msg.recipient_id](msg), timeout=30.0)
            except Exception as e:
                logger.error(f"Delivery error to {msg.recipient_id}: {e}")
                raise
    
    async def start(self):
        """Start the brain's message processing loop."""
        if self._running:
            logger.warning("Agent Brain is already running")
            return
        
        self._running = True
        try:
            from app.core.event_bus import event_bus

            self._event_bus_connected = event_bus.is_connected or await event_bus.connect()
            if self._event_bus_connected:
                self._event_consumer_task = asyncio.create_task(self._consume_message_events())
                logger.info("🧠 Agent Brain Redis event bus connected")
        except Exception as exc:
            self._event_bus_connected = False
            logger.warning("Agent Brain Redis event bus unavailable; using DB + in-memory queue: %s", exc)
        self._processing_task = asyncio.create_task(self._process_messages())
        self._idle_task = asyncio.create_task(self._idle_time_cycle())
        await self._replay_pending_messages()
        # T-032: warm the shared Redis cache immediately on startup so the first
        # queries after a restart don't all cold-miss to PostgreSQL.
        asyncio.create_task(self.ensure_knowledge_loaded())
        logger.info("🧠 Agent Brain started — message + idle processing active")
    
    async def stop(self):
        """Stop the brain."""
        self._running = False
        tasks = []
        if self._idle_task:
            self._idle_task.cancel()
            tasks.append(self._idle_task)
            self._idle_task = None
        if self._processing_task:
            self._processing_task.cancel()
            tasks.append(self._processing_task)
            self._processing_task = None
        if self._event_consumer_task:
            self._event_consumer_task.cancel()
            tasks.append(self._event_consumer_task)
            self._event_consumer_task = None
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if self._event_bus_connected:
            try:
                from app.core.event_bus import event_bus

                await event_bus.disconnect()
            except Exception:
                pass
            self._event_bus_connected = False
        logger.info("🧠 Agent Brain stopped")
    
    # ── Workflow Orchestration ──────────────────────────────────────────
    
    async def run_workflow(self, workflow: List[Dict[str, Any]], 
                            context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run a workflow of chained agent executions.
        
        workflow: [
            {"agent_id": "agent-001", "input": {...}, "depends_on": []},
            {"agent_id": "agent-005", "input": {...}, "depends_on": ["agent-001"]},
        ]
        """
        context = context or {}
        results = {}
        
        for step in workflow:
            agent_id = step["agent_id"]
            depends_on = step.get("depends_on", [])
            
            # Check dependencies
            for dep in depends_on:
                if dep not in results:
                    raise ValueError(f"Dependency {dep} not satisfied for {agent_id}")
            
            agent = self.get_agent(agent_id)
            if not agent:
                logger.warning(f"Agent {agent_id} not found in workflow")
                continue
            
            step_input = {**context, **step.get("input", {})}
            for dep in depends_on:
                step_input[dep] = results[dep]
            
            try:
                start = time.time()
                if hasattr(agent, "execute"):
                    if asyncio.iscoroutinefunction(agent.execute):
                        result = await agent.execute(step_input)
                    else:
                        result = agent.execute(step_input)
                else:
                    result = {"error": f"Agent {agent_id} has no execute method"}
                
                elapsed = int((time.time() - start) * 1000)
                results[agent_id] = result
                logger.info(f"  ⚡ {agent_id} completed in {elapsed}ms")
                
                # Store result
                if hasattr(result, "output") if not isinstance(result, dict) else True:
                    output = result if isinstance(result, dict) else getattr(result, "output", {})
                    try:
                        async with self.db() as session:
                            ar = AgentResult(
                                agent_id=agent_id,
                                request_id=step.get("request_id", context.get("request_id")),
                                tender_id=step.get("tender_id", context.get("tender_id")),
                                status="success",
                                output=output if isinstance(output, dict) else {},
                                execution_time_ms=elapsed,
                            )
                            session.add(ar)
                            await session.commit()
                    except Exception as e:
                        logger.warning(f"Could not store result: {e}")
                
            except Exception as e:
                logger.error(f"Workflow step {agent_id} failed: {e}")
                results[agent_id] = {"error": str(e)}
        
        return results
    
    # ── Utilities ───────────────────────────────────────────────────────
    
    async def _idle_time_cycle(self):
        """
        Background idle-time processing cycle.
        Runs pre-emptive intelligence agents during idle periods.
        
        Cycle:
          5 min: Quick check for new tenders
          15 min: Run pre-screener on tenders
          30 min: Run full MOAT/SLT/NPPI analysis  
          60 min: Full intelligence refresh + knowledge persistence
        """
        cycle_count = 0
        while self._running:
            try:
                cycle_count += 1
                elapsed_mins = cycle_count * 5
                
                # ENT-04: resolve idle agents by capability, not hardcoded IDs
                idle_agents = self.find_agents_by_capability("idle_intelligence")
                pre_screeners = self.find_agents_by_capability("pre_screening")

                if elapsed_mins % 60 == 5:  # Every ~60 min
                    logger.info("🧠 Idle cycle: Full intelligence refresh")
                    await self._refresh_intelligence_if_stale()
                    for cap in idle_agents:
                        agent = self._agent_instances.get(cap.agent_id)
                        if agent:
                            try:
                                if hasattr(agent, 'execute'):
                                    await agent.execute({"action": "full_analysis"})
                            except Exception as e:
                                logger.warning(f"Idle agent {cap.agent_id} error: {e}")

                elif elapsed_mins % 30 == 5:  # Every ~30 min
                    logger.info("🧠 Idle cycle: MOAT/SLT/Pre-screen")
                    for cap in idle_agents:
                        agent = self._agent_instances.get(cap.agent_id)
                        if agent:
                            try:
                                await agent.execute({"action": "idle_cycle"})
                            except Exception as e:
                                logger.warning(f"Idle agent {cap.agent_id} error: {e}")

                elif elapsed_mins % 15 == 5:  # Every ~15 min
                    logger.info("🧠 Idle cycle: Pre-screening tenders")
                    for cap in pre_screeners:
                        agent = self._agent_instances.get(cap.agent_id)
                        if agent:
                            try:
                                await agent.execute({"action": "pre_screen", "company_profile": {}})
                            except Exception as e:
                                logger.warning(f"Pre-screener {cap.agent_id} error: {e}")
                
                # Sleep 5 minutes
                for _ in range(300):
                    if not self._running:
                        break
                    await asyncio.sleep(1)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"🧠 Idle cycle error: {e}")
                await asyncio.sleep(60)

    async def _refresh_intelligence_if_stale(self):
        """Idle-time maintenance: re-aggregate intelligence tables when the
        underlying canonical_contracts data has changed since the last pass.
        Staleness is detected by row count + max(rebuilt_at), so an unchanged
        warehouse costs one cheap SELECT per hour."""
        def _sync_work():
            from sqlalchemy import text as _t
            from app.db.database import get_sync_engine as _eng
            engine = _eng()
            with engine.connect() as c:
                sig = str(c.execute(_t(
                    "SELECT count(*) || '|' || coalesce(max(rebuilt_at)::text,'') FROM canonical_contracts"
                )).scalar())
            if sig == getattr(self, "_intel_signature", None):
                return None
            import subprocess, sys
            from pathlib import Path
            backend = Path(__file__).resolve().parents[3]
            r = subprocess.run(
                [sys.executable, "-c",
                 f"import sys; sys.path.insert(0, r'{backend}'); "
                 "from refresh_intelligence_tables import main; main()"],
                capture_output=True, text=True, timeout=1800,
            )
            if r.returncode == 0:
                self._intel_signature = sig
            return r.returncode
        try:
            rc = await asyncio.to_thread(_sync_work)
            if rc is None:
                logger.info("🧠 Intelligence tables fresh — skipped")
            elif rc == 0:
                logger.info("🧠 Intelligence tables re-aggregated (idle-time)")
            else:
                logger.warning("🧠 Intelligence refresh failed rc=%s", rc)
        except Exception as e:
            logger.warning("🧠 Intelligence staleness check failed: %s", e)

    def get_stats(self) -> Dict:
        """Get brain statistics."""
        _ci = self._knowledge_store.get_info()
        return {
            "registered_agents": len(self._agents),
            "active_handlers": len(self._message_handlers),
            "queue_size": self._message_queue.qsize(),
            "knowledge_entries": len(self._knowledge_store),
            "knowledge_cache_loaded": self._knowledge_cache_loaded,
            "cache_has_redis": _ci["has_redis"],
            "cache_degraded": _ci["degraded"],
            "cache_l1_size": _ci["l1_size"],
            "agents": [
                {"id": a.agent_id, "name": a.agent_name, "available": a.is_available}
                for a in self._agents.values()
            ],
        }
    
    async def get_system_memory(self) -> Dict:
        """Get system checkpoint/memory summary."""
        await self.ensure_knowledge_loaded(limit=500)
        memory = {
            "agent_count": len(self._agents),
            "knowledge_count": len(self._knowledge_store),
            "uptime": "active",
            "last_idle_cycle": None,
            "agents": [
                {"id": a.agent_id, "name": a.agent_name}
                for a in self._agents.values()
            ],
        }
        # Get last knowledge entries for context
        recent = await self.query_knowledge(limit=5)
        if recent:
            memory["recent_knowledge"] = recent
        memory["project_memory"] = self._project_memory.stats()
        memory["architecture_context"] = self._project_memory.get_context_entries(limit=5)
        return memory
