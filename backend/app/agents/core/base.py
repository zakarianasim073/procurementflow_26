from __future__ import annotations
"""
Base Agent — All agents inherit from this.
Provides DB integration, Agent Brain communication, standard result format.
Includes configurable timeout, max_iterations, and circuit breaker.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)

from app.core.config import settings


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


@dataclass
class AgentResult:
    """Standard agent execution result."""
    agent_id: str = ""
    agent_name: str = ""
    status: AgentStatus = AgentStatus.PENDING
    output: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    execution_time_ms: int = 0
    model_used: str = ""
    trace_id: str = ""
    request_id: str = ""
    tender_id: str = ""
    source_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self.status.value if isinstance(self.status, AgentStatus) else self.status,
            "output": self.output,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "model_used": self.model_used,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "tender_id": self.tender_id,
            "created_at": self.created_at,
        }
class BaseAgent(ABC):
    """Abstract base class for all ProcureFlow agents.
    
    Every agent must implement:
    - agent_id: Unique identifier
    - agent_name: Human-readable name
    - description: What this agent does
    - execute(context): Main execution method
    
    Optional:
    - dependencies: List of agent_ids this agent depends on
    - version: Semantic version
    - brain: AgentBrain instance for inter-agent communication
    """
    
    agent_id: str = "base-agent"
    agent_name: str = "Base Agent"
    description: str = "Base agent class"
    dependencies: List[str] = []
    version: str = "1.0.0"
    timeout_seconds: int = 300
    max_iterations: int = 50
    _iteration_count: int = 0
    _circuit_open: bool = False
    _circuit_open_since: Optional[float] = None
    _circuit_cooldown_seconds: int = 60
    _circuit_half_open: bool = False
    _consecutive_failures: int = 0
    _max_consecutive_failures: int = 3
    
    def __init__(self, brain=None, memory=None, llm_service=None, vector_db=None, session_id: str = None):
        self.brain = brain
        self.memory = memory
        self.llm_service = llm_service
        self.vector_db = vector_db
        self._db_session = None
        self._status = AgentStatus.PENDING
        self._session_id = session_id or str(uuid.uuid4())

    @property
    def circuit_breaker_state(self) -> str:
        """Return circuit breaker state: 'closed', 'open', or 'half-open'."""
        if not self._circuit_open:
            return "closed"
        if self._circuit_open_since is None:
            return "open"
        elapsed = time.time() - self._circuit_open_since
        if elapsed >= self._circuit_cooldown_seconds:
            return "half-open"
        return "open"

    def _record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._circuit_half_open:
            # Failure during half-open trial — restart cooldown
            self._circuit_open_since = time.time()
            self._circuit_half_open = False
            logger.warning("Agent %s: half-open trial FAILED, restarting cooldown", self.agent_id)
        elif self._consecutive_failures >= self._max_consecutive_failures:
            self._circuit_open = True
            if self._circuit_open_since is None:
                self._circuit_open_since = time.time()
            logger.error("Agent %s: circuit OPEN after %d failures", self.agent_id, self._consecutive_failures)
    
    def _record_success(self) -> None:
        self._consecutive_failures = 0
        if self._circuit_open or self._circuit_half_open:
            self._circuit_open = False
            self._circuit_half_open = False
            self._circuit_open_since = None
            logger.info("Agent %s: circuit CLOSED (recovered)", self.agent_id)

    def _check_circuit_breaker(self) -> None:
        if not self._circuit_open:
            return
        elapsed = time.time() - (self._circuit_open_since or 0)
        if elapsed >= self._circuit_cooldown_seconds:
            if not self._circuit_half_open:
                self._circuit_half_open = True
                logger.info("Agent %s: entering HALF-OPEN (cooldown elapsed, allowing trial)", self.agent_id)
            return  # Allow one trial execution
        remaining = int(self._circuit_cooldown_seconds - elapsed)
        raise RuntimeError(f"Agent {self.agent_id}: circuit breaker open, retry in {remaining}s")

    def reset_circuit_breaker(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        self._circuit_open = False
        self._circuit_half_open = False
        self._circuit_open_since = None
        self._consecutive_failures = 0
        logger.info("Agent %s: circuit breaker manually RESET", self.agent_id)

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute the agent's primary function.
        
        Args:
            context: Dict containing:
                - tender_id: str
                - request_id: str
                - bid_data: Dict
                - upstream: Dict of upstream agent results
                - Any other agent-specific data
        
        Returns:
            AgentResult with status and output
        """
        pass
    
    async def run(self, context: Optional[Dict[str, Any]] = None, **kwargs) -> AgentResult:
        """Execute the agent with tracing, persistence, timeout, and circuit breaker."""
        start = time.time()
        trace_id = str(uuid.uuid4())
        if context is None:
            context = {}
        elif not isinstance(context, dict):
            context = {"input": context}
        if kwargs:
            context = {**context, **kwargs}
        request_id = context.get("request_id", trace_id)
        tender_id = context.get("tender_id", "")
        self._status = AgentStatus.RUNNING
        
        logger.info(f"▶ {self.agent_id} ({self.agent_name}) starting — request_id={request_id[:8]}...")
        
        try:
            self._check_circuit_breaker()
            self._iteration_count += 1
            if self._iteration_count > self.max_iterations:
                raise RuntimeError(f"Max iterations ({self.max_iterations}) exceeded")

            # Add trace info
            context["_trace_id"] = trace_id
            context["_request_id"] = request_id
            context["_agent_id"] = self.agent_id
            context["_start_time"] = start
            
            result = await asyncio.wait_for(self.execute(context), timeout=self.timeout_seconds)
            
            if not isinstance(result, AgentResult):
                result = AgentResult(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    status=AgentStatus.SUCCESS,
                    output=result if isinstance(result, dict) else {"result": result},
                )
            
            result.agent_id = self.agent_id
            result.agent_name = self.agent_name
            result.execution_time_ms = int((time.time() - start) * 1000)
            result.trace_id = trace_id
            result.request_id = request_id
            result.tender_id = tender_id
            
            if result.status == AgentStatus.PENDING:
                result.status = AgentStatus.SUCCESS

            self._status = result.status
            if result.status == AgentStatus.FAILED:
                self._record_failure()
            else:
                self._record_success()
            logger.info(f"✓ {self.agent_id} completed in {result.execution_time_ms}ms — {result.status.value}")

        except asyncio.TimeoutError:
            elapsed = int((time.time() - start) * 1000)
            self._record_failure()
            result = AgentResult(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status=AgentStatus.FAILED,
                error=f"Timeout after {self.timeout_seconds}s",
                execution_time_ms=elapsed,
                trace_id=trace_id,
                request_id=request_id,
                tender_id=tender_id,
            )
            self._status = AgentStatus.FAILED
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            self._record_failure()
            logger.error(f"✗ {self.agent_id} FAILED after {elapsed}ms: {e}")
            
            result = AgentResult(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status=AgentStatus.FAILED,
                error=str(e),
                execution_time_ms=elapsed,
                trace_id=trace_id,
                request_id=request_id,
                tender_id=tender_id,
            )
            self._status = AgentStatus.FAILED

        await self.store_result(result)
        return result
    
    async def store_result(self, result: AgentResult, session=None):
        """Persist agent result to database using async session."""
        from app.db import AgentResult as DBResult
        from app.db.base import get_session_factory

        output = json.loads(json.dumps(result.output, default=str))

        # If a session was injected (e.g. from orchestrator), use it directly
        if session is not None:
            try:
                db_result = DBResult(
                    agent_id=result.agent_id,
                    agent_name=result.agent_name,
                    agent_version=self.version,
                    request_id=result.request_id,
                    tender_id=result.tender_id,
                    status=result.status.value if isinstance(result.status, AgentStatus) else result.status,
                    output=output,
                    error=result.error,
                    execution_time_ms=result.execution_time_ms,
                    trace_id=result.trace_id,
                )
                session.add(db_result)
                await session.flush()
            except Exception as e:
                logger.warning(f"Could not persist result (injected session): {e}")
            return

        # Own an async session for fire-and-forget persistence
        try:
            sf = get_session_factory()
            async with sf() as async_session:
                db_result = DBResult(
                    agent_id=result.agent_id,
                    agent_name=result.agent_name,
                    agent_version=self.version,
                    request_id=result.request_id,
                    tender_id=result.tender_id,
                    status=result.status.value if isinstance(result.status, AgentStatus) else result.status,
                    output=output,
                    error=result.error,
                    execution_time_ms=result.execution_time_ms,
                    trace_id=result.trace_id,
                )
                async_session.add(db_result)
                await async_session.commit()
                self._schedule_result_webhook(result)
        except Exception as e:
            logger.warning(f"Could not persist result: {e}")

    def _schedule_result_webhook(self, result: AgentResult) -> None:
        if os.getenv("WEBHOOK_AGENT_EVENTS", "").strip().lower() not in {"1", "true", "yes", "on"}:
            return
        try:
            from app.services.webhook_service import schedule_webhook_event
            status = result.status.value if isinstance(result.status, AgentStatus) else str(result.status)
            event_type = "agent.failed" if status == AgentStatus.FAILED.value else "agent.completed"
            schedule_webhook_event(
                event_type,
                {
                    "agent_id": result.agent_id,
                    "agent_name": result.agent_name,
                    "status": status,
                    "request_id": result.request_id,
                    "tender_id": result.tender_id,
                    "execution_time_ms": result.execution_time_ms,
                    "error": result.error,
                },
                event_id=result.request_id or result.trace_id,
            )
        except Exception as exc:
            logger.debug("Agent result webhook scheduling skipped: %s", exc)
    
    async def share_knowledge(self, entry_type: str, tender_id: str = "",
                               data: Dict = None, summary: str = "", tags: List[str] = None):
        """Share knowledge via the Agent Brain."""
        if self.brain is None:
            logger.warning("%s: share_knowledge skipped; no AgentBrain connected", self.agent_id)
            return None
        return await self.brain.store_knowledge(
            agent_id=self.agent_id,
            entry_type=entry_type,
            tender_id=tender_id,
            data=data,
            summary=summary,
            tags=tags,
        )
    
    async def query_brain(self, entry_type: str = None, tender_id: str = None) -> List[Dict]:
        """Query the Agent Brain for knowledge."""
        if self.brain is None:
            logger.warning("%s: query_brain skipped; no AgentBrain connected", self.agent_id)
            return []
        return await self.brain.query_knowledge(
            entry_type=entry_type, tender_id=tender_id
        )
    
    async def ask_agent(self, recipient_id: str, subject: str,
                         body: Dict, timeout: float = 30.0) -> Optional[Dict]:
        """Ask another agent for help via the Agent Brain."""
        if self.brain is None:
            logger.warning("%s: ask_agent(%s) skipped; no AgentBrain connected", self.agent_id, recipient_id)
            return None
        return await self.brain.request(
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            subject=subject,
            body=body,
            timeout=timeout,
        )
    
    def get_dependencies(self) -> List[str]:
        return self.dependencies

    # ------------------------------------------------------------------
    # Memory helpers
    # ------------------------------------------------------------------

    async def _remember(self, key: str, value: Any, ttl: int = 3600):
        """Store agent state in memory service."""
        if self.memory:
            await self.memory.store_state(self.agent_id, key, value, ttl)

    async def _recall(self, key: str, default: Any = None) -> Any:
        """Retrieve agent state from memory service."""
        if self.memory:
            return await self.memory.get_state(self.agent_id, key, default)
        return default

    async def _forget(self, key: str) -> bool:
        """Delete agent state from memory service."""
        if self.memory:
            return await self.memory.delete_state(self.agent_id, key)
        return False

    async def _store_conversation(self, role: str, content: str, metadata: Dict = None):
        """Store a conversation message."""
        if self.memory:
            await self.memory.store_conversation(
                session_id=self._session_id,
                agent_id=self.agent_id,
                role=role,
                content=content,
                metadata=metadata,
            )

    async def _get_conversation(self, limit: int = 50) -> List[Dict]:
        """Retrieve conversation history."""
        if self.memory:
            return await self.memory.get_conversation(self._session_id, limit)
        return []

    async def _link_entities(self, entity1: str, relation: str, entity2: str, confidence: float = 1.0):
        """Create a knowledge graph relationship."""
        if self.memory:
            await self.memory.link_entities(self.agent_id, entity1, relation, entity2, confidence)

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_with_llm(
        self,
        prompt: str,
        provider: str = "auto",
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: str = "",
        use_cache: bool = True,
    ) -> str:
        """Generate text using the LLM service. Returns content string."""
        if not self.llm_service:
            raise RuntimeError(
                f"{self.agent_id}: LLM service not available. "
                f"Ensure LLMService is initialized and passed to the agent."
            )
        response = await self.llm_service.generate(
            prompt=prompt,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            use_cache=use_cache,
        )
        return response.content

    async def _generate_structured(
        self,
        prompt: str,
        schema: Dict,
        provider: str = "auto",
        model: str = None,
        temperature: float = 0.3,
    ) -> Dict:
        """Generate structured output using the LLM service."""
        if not self.llm_service:
            raise RuntimeError(
                f"{self.agent_id}: LLM service not available."
            )
        return await self.llm_service.generate_structured(
            prompt=prompt,
            schema=schema,
            provider=provider,
            model=model,
            temperature=temperature,
        )

    async def _embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using the LLM service."""
        if not self.llm_service:
            raise RuntimeError(
                f"{self.agent_id}: LLM service not available."
            )
        return await self.llm_service.embed(texts)

    async def _vision_extract(self, image_path: str, prompt: str = "Extract all text from this document.") -> str:
        """Extract text from image using vision model."""
        if not self.llm_service:
            raise RuntimeError(
                f"{self.agent_id}: LLM service not available."
            )
        response = await self.llm_service.vision_extract(image_path, prompt)
        return response.content

    # ------------------------------------------------------------------
    # Vector DB helpers
    # ------------------------------------------------------------------

    async def _query_knowledge(self, query: str, collection: str = "agent_knowledge", n_results: int = 5) -> List[Dict]:
        """Query vector knowledge base."""
        if not self.vector_db:
            return []
        return await self.vector_db.query(
            collection=collection,
            query_text=query,
            n_results=n_results,
        )

    async def _store_knowledge_vector(self, content: str, knowledge_type: str = "insight", tags: List[str] = None):
        """Store knowledge in vector DB."""
        if not self.vector_db:
            return 0
        return await self.vector_db.ingest_agent_knowledge(
            agent_id=self.agent_id,
            knowledge_items=[{
                "content": content,
                "type": knowledge_type,
                "tags": tags or [],
                "id": str(uuid.uuid4()),
            }],
        )

    async def _retrieve_tender_docs(self, query: str, tender_id: str = None, n_results: int = 5) -> List[Dict]:
        """Retrieve relevant tender documents from vector DB."""
        if not self.vector_db:
            return []
        return await self.vector_db.retrieve_for_tender(query, tender_id, n_results)

    # ------------------------------------------------------------------
    # Properties & info
    # ------------------------------------------------------------------

    @property
    def status(self) -> AgentStatus:
        return self._status

    def info(self) -> Dict[str, Any]:
        """Return a stable metadata payload for registry and API consumers."""
        status = getattr(self, "_status", None)
        if isinstance(status, AgentStatus):
            status_value = status.value
        else:
            status_value = AgentStatus.PENDING.value

        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "description": self.description,
            "dependencies": list(self.dependencies),
            "version": self.version,
            "status": status_value,
            "has_brain": self.brain is not None,
            "has_memory": self.memory is not None,
            "has_llm": self.llm_service is not None,
            "has_vector_db": self.vector_db is not None,
        }

    def __repr__(self):
        return f"<{self.agent_id}: {self.agent_name}>"
