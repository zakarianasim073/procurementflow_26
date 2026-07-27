"""
Agent Memory Service — Persistent state, conversations, and knowledge graph.
Uses PostgreSQL for persistence + optional Redis for caching.

This builds ON TOP of the existing AgentBrain (core/brain.py) by adding:
- Persistent agent state (key-value with TTL)
- Conversation history
- Knowledge graph (entity relationships)
- Cleanup of expired entries

Tables auto-created on first use:
  agent_memory, agent_conversations, agent_knowledge_graph
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from app.db.database import get_session

logger = logging.getLogger(__name__)


class AgentMemoryService:
    """
    Persistent memory for agents.

    Features:
    - Agent state storage (key-value with TTL)
    - Conversation history (session-based)
    - Knowledge graph (entity relationships)
    - Expired entry cleanup

    Storage layers:
    - L1: Redis (if available) — fast cache
    - L2: PostgreSQL — persistent storage
    """

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or getattr(config, 'redis_url', '') or ''
        self._redis = None
        self._tables_ensured = False
        self._tables_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Table management
    # ------------------------------------------------------------------

    async def _ensure_tables(self):
        """Create memory tables if they don't exist."""
        if self._tables_ensured:
            return
        async with self._tables_lock:
            if self._tables_ensured:
                return
            try:
                await asyncio.to_thread(self._ensure_tables_sync)
                logger.info("✓ Agent memory tables ensured")
                self._tables_ensured = True
            except Exception as e:
                logger.warning(f"Could not ensure memory tables: {e}")

    def _ensure_tables_sync(self):
        """Run synchronous DDL without blocking the event loop."""
        from app.db.database import get_sync_engine
        engine = get_sync_engine()
        with engine.connect() as conn:
            # Agent memory (key-value state)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS agent_memory (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    agent_id VARCHAR(100) NOT NULL,
                    mem_key VARCHAR(255) NOT NULL,
                    mem_value JSONB NOT NULL,
                    expires_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            conn.execute(text("""
                DELETE FROM agent_memory a
                USING agent_memory b
                WHERE a.ctid < b.ctid
                  AND a.agent_id = b.agent_id
                  AND a.mem_key = b.mem_key
            """))
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_memory_agent_key_unique
                ON agent_memory(agent_id, mem_key)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_agent_memory_expires
                ON agent_memory(expires_at) WHERE expires_at IS NOT NULL
            """))

            # Conversations
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS agent_conversations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    session_id VARCHAR(100) NOT NULL,
                    agent_id VARCHAR(100) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_agent_conversations_session
                ON agent_conversations(session_id, created_at DESC)
            """))

            # Knowledge graph
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS agent_knowledge_graph (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    agent_id VARCHAR(100) NOT NULL,
                    entity1 VARCHAR(255) NOT NULL,
                    relation VARCHAR(100) NOT NULL,
                    entity2 VARCHAR(255) NOT NULL,
                    confidence FLOAT DEFAULT 1.0,
                    metadata JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_agent_knowledge_graph_agent
                ON agent_knowledge_graph(agent_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_agent_knowledge_graph_entities
                ON agent_knowledge_graph(entity1, entity2)
            """))

            conn.commit()

    # ------------------------------------------------------------------
    # Redis helpers
    # ------------------------------------------------------------------

    async def _get_redis(self):
        if self._redis is None and self.redis_url:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
            except Exception as e:
                logger.debug(f"Redis not available: {e}")
        return self._redis

    async def _redis_set(self, agent_id: str, key: str, value: Any, ttl: int):
        redis = await self._get_redis()
        if not redis:
            return
        try:
            redis_key = f"procureflow:agent:{agent_id}:state:{key}"
            await redis.set(redis_key, json.dumps(value, default=str), ex=ttl)
        except Exception as e:
            logger.debug(f"Redis cache set failed: {e}")

    async def _redis_get(self, agent_id: str, key: str) -> Optional[Any]:
        redis = await self._get_redis()
        if not redis:
            return None
        try:
            redis_key = f"procureflow:agent:{agent_id}:state:{key}"
            cached = await redis.get(redis_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass
        return None

    async def _redis_delete(self, agent_id: str, key: str):
        redis = await self._get_redis()
        if not redis:
            return
        try:
            redis_key = f"procureflow:agent:{agent_id}:state:{key}"
            await redis.delete(redis_key)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Agent state (key-value with TTL)
    # ------------------------------------------------------------------

    async def store_state(
        self,
        agent_id: str,
        key: str,
        value: Any,
        ttl: int = 3600,
    ) -> str:
        """
        Store agent state. Overwrites existing key for this agent.

        Args:
            agent_id: Agent identifier
            key: State key
            value: JSON-serializable value
            ttl: Time-to-live in seconds (0 = permanent)
        """
        await self._ensure_tables()
        entry_id = str(uuid.uuid4())
        expires_at = None
        if ttl > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        try:
            async with get_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO agent_memory (id, agent_id, mem_key, mem_value, expires_at, updated_at)
                        VALUES (:id, :agent_id, :key, CAST(:value AS jsonb), :expires_at, NOW())
                        ON CONFLICT (agent_id, mem_key) DO UPDATE SET
                            mem_value = EXCLUDED.mem_value,
                            expires_at = EXCLUDED.expires_at,
                            updated_at = NOW()
                    """),
                    {
                        "id": entry_id,
                        "agent_id": agent_id,
                        "key": key,
                        "value": json.dumps(value, default=str),
                        "expires_at": expires_at,
                    }
                )
                await session.commit()
        except Exception as e:
            logger.warning(f"Could not store agent state for {agent_id}/{key}: {e}")
            return ""

        # Cache in Redis
        await self._redis_set(agent_id, key, value, ttl)

        return entry_id

    async def get_state(self, agent_id: str, key: str, default: Any = None) -> Any:
        """Retrieve agent state. Returns default if not found or expired."""
        await self._ensure_tables()

        # Try Redis first
        cached = await self._redis_get(agent_id, key)
        if cached is not None:
            return cached

        # Fall back to DB
        try:
            async with get_session() as session:
                result = await session.execute(
                    text("""
                        SELECT mem_value FROM agent_memory
                        WHERE agent_id = :agent_id AND mem_key = :key
                        AND (expires_at IS NULL OR expires_at > NOW())
                        ORDER BY created_at DESC LIMIT 1
                    """),
                    {"agent_id": agent_id, "key": key}
                )
                row = result.fetchone()
                if row and row[0]:
                    value = row[0]
                    if isinstance(value, str):
                        return json.loads(value)
                    return value
        except Exception as e:
            logger.debug(f"Could not retrieve agent state for {agent_id}/{key}: {e}")

        return default

    async def delete_state(self, agent_id: str, key: str) -> bool:
        """Delete agent state."""
        await self._ensure_tables()
        await self._redis_delete(agent_id, key)
        try:
            async with get_session() as session:
                await session.execute(
                    text("""
                        DELETE FROM agent_memory
                        WHERE agent_id = :agent_id AND mem_key = :key
                    """),
                    {"agent_id": agent_id, "key": key}
                )
                await session.commit()
                return True
        except Exception as e:
            logger.warning(f"Could not delete agent state for {agent_id}/{key}: {e}")
            return False

    async def list_states(self, agent_id: str) -> Dict[str, Any]:
        """List all non-expired states for an agent."""
        await self._ensure_tables()
        states = {}
        try:
            async with get_session() as session:
                result = await session.execute(
                    text("""
                        SELECT mem_key, mem_value FROM agent_memory
                        WHERE agent_id = :agent_id
                        AND (expires_at IS NULL OR expires_at > NOW())
                        ORDER BY mem_key
                    """),
                    {"agent_id": agent_id}
                )
                for row in result.fetchall():
                    key, value = row[0], row[1]
                    try:
                        states[key] = json.loads(value) if isinstance(value, str) else value
                    except Exception:
                        states[key] = value
        except Exception as e:
            logger.warning(f"Could not list states for {agent_id}: {e}")
        return states

    # ------------------------------------------------------------------
    # Conversations
    # ------------------------------------------------------------------

    async def store_conversation(
        self,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        metadata: Dict = None
    ) -> str:
        """Store a conversation message."""
        await self._ensure_tables()
        entry_id = str(uuid.uuid4())
        try:
            async with get_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO agent_conversations
                            (id, session_id, agent_id, role, content, metadata)
                        VALUES (:id, :session_id, :agent_id, :role, :content, :metadata)
                    """),
                    {
                        "id": entry_id,
                        "session_id": session_id,
                        "agent_id": agent_id,
                        "role": role,
                        "content": content,
                        "metadata": json.dumps(metadata or {}, default=str),
                    }
                )
                await session.commit()
        except Exception as e:
            logger.warning(f"Could not store conversation: {e}")
        return entry_id

    async def get_conversation(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Retrieve conversation history (oldest first)."""
        await self._ensure_tables()
        try:
            async with get_session() as session:
                result = await session.execute(
                    text("""
                        SELECT agent_id, role, content, metadata, created_at
                        FROM agent_conversations
                        WHERE session_id = :session_id
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"session_id": session_id, "limit": limit}
                )
                rows = []
                for row in result.fetchall():
                    meta = row[3]
                    rows.append({
                        "agent_id": row[0],
                        "role": row[1],
                        "content": row[2],
                        "metadata": json.loads(meta) if isinstance(meta, str) else (meta or {}),
                        "created_at": str(row[4]),
                    })
                # Reverse to get oldest first
                return list(reversed(rows))
        except Exception as e:
            logger.warning(f"Could not retrieve conversation for {session_id}: {e}")
            return []

    async def delete_conversation(self, session_id: str) -> bool:
        """Delete all messages in a session."""
        await self._ensure_tables()
        try:
            async with get_session() as session:
                await session.execute(
                    text("DELETE FROM agent_conversations WHERE session_id = :session_id"),
                    {"session_id": session_id}
                )
                await session.commit()
                return True
        except Exception as e:
            logger.warning(f"Could not delete conversation {session_id}: {e}")
            return False

    # ------------------------------------------------------------------
    # Knowledge graph
    # ------------------------------------------------------------------

    async def link_entities(
        self,
        agent_id: str,
        entity1: str,
        relation: str,
        entity2: str,
        confidence: float = 1.0,
        metadata: Dict = None
    ) -> str:
        """Create a knowledge graph relationship."""
        await self._ensure_tables()
        entry_id = str(uuid.uuid4())
        try:
            async with get_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO agent_knowledge_graph
                            (id, agent_id, entity1, relation, entity2, confidence, metadata)
                        VALUES (:id, :agent_id, :entity1, :relation, :entity2, :confidence, :metadata)
                    """),
                    {
                        "id": entry_id,
                        "agent_id": agent_id,
                        "entity1": entity1,
                        "relation": relation,
                        "entity2": entity2,
                        "confidence": confidence,
                        "metadata": json.dumps(metadata or {}, default=str),
                    }
                )
                await session.commit()
        except Exception as e:
            logger.warning(f"Could not link entities: {e}")
        return entry_id

    async def query_knowledge_graph(
        self,
        agent_id: str = None,
        entity: str = None,
        relation: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query knowledge graph relationships."""
        await self._ensure_tables()
        try:
            async with get_session() as session:
                clauses = []
                params: Dict[str, Any] = {"limit": limit}
                if agent_id:
                    clauses.append("agent_id = :agent_id")
                    params["agent_id"] = agent_id
                if entity:
                    clauses.append("(entity1 = :entity OR entity2 = :entity)")
                    params["entity"] = entity
                if relation:
                    clauses.append("relation = :relation")
                    params["relation"] = relation

                where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
                result = await session.execute(
                    # sql-ok: WHERE clause fragments from code constants; values bound
                    text(f"""
                        SELECT agent_id, entity1, relation, entity2, confidence, metadata, created_at
                        FROM agent_knowledge_graph
                        {where_sql}
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    params
                )
                return [
                    {
                        "agent_id": row[0],
                        "entity1": row[1],
                        "relation": row[2],
                        "entity2": row[3],
                        "confidence": row[4],
                        "metadata": json.loads(row[5]) if isinstance(row[5], str) else (row[5] or {}),
                        "created_at": str(row[6]),
                    }
                    for row in result.fetchall()
                ]
        except Exception as e:
            logger.warning(f"Could not query knowledge graph: {e}")
            return []

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    async def cleanup_expired(self) -> int:
        """Remove expired memory entries."""
        await self._ensure_tables()
        try:
            async with get_session() as session:
                result = await session.execute(
                    text("""
                        DELETE FROM agent_memory
                        WHERE expires_at IS NOT NULL AND expires_at < NOW()
                    """)
                )
                await session.commit()
                count = result.rowcount
                if count > 0:
                    logger.info(f"Cleaned up {count} expired agent memory entries")
                return count
        except Exception as e:
            logger.warning(f"Could not cleanup expired memory: {e}")
            return 0

    async def get_stats(self) -> Dict:
        """Get memory statistics."""
        await self._ensure_tables()
        stats = {"redis_available": self._redis is not None}
        try:
            async with get_session() as session:
                mem_count = await session.execute(
                    text("SELECT COUNT(*) FROM agent_memory")
                )
                conv_count = await session.execute(
                    text("SELECT COUNT(*) FROM agent_conversations")
                )
                kg_count = await session.execute(
                    text("SELECT COUNT(*) FROM agent_knowledge_graph")
                )
                expired_count = await session.execute(
                    text("SELECT COUNT(*) FROM agent_memory WHERE expires_at < NOW()")
                )
                stats["memory_entries"] = mem_count.scalar()
                stats["conversation_entries"] = conv_count.scalar()
                stats["knowledge_graph_entries"] = kg_count.scalar()
                stats["expired_entries"] = expired_count.scalar()
        except Exception as e:
            logger.warning(f"Could not get memory stats: {e}")
        return stats
