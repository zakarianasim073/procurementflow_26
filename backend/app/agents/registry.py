"""
Procurement Flow Specialist BD — Agent Registry
Central registry for discovering, managing, and executing agents.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type

from app.agents.core.base import BaseAgent, AgentResult, AgentStatus

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Singleton registry that holds all agent instances.
    
    Provides discovery, dependency resolution, and orchestrated execution.
    """

    _instance: Optional["AgentRegistry"] = None
    _agents: Dict[str, BaseAgent] = {}
    _PARTIAL_DEPENDENCY_AGENTS = {
        "agent-022-executive-decision",
        "agent-031-tender-preparation",
    }

    def __new__(cls, brain=None) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
            cls._instance._brain = None
        if brain is not None:
            cls._instance._brain = brain
        elif cls._instance._brain is None:
            cls._instance._ensure_brain()
        return cls._instance

    def _ensure_brain(self):
        """Lazily initialize brain from canonical singleton."""
        if self._brain is not None:
            return
        try:
            from app.api.brain_router import get_brain
            self._brain = get_brain()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, agent: BaseAgent) -> None:
        if not agent.agent_id:
            raise ValueError(f"Cannot register agent without agent_id: {type(agent).__name__}")
        self._agents[agent.agent_id] = agent
        if self._brain is not None:
            self._brain.register_agent(
                agent_id=agent.agent_id,
                instance=agent,
                name=agent.agent_name,
                description=agent.description,
                version=agent.version,
            )
        logger.info(f"Registered agent [{agent.agent_id}] {agent.agent_name}")

    def register_many(self, *agents: BaseAgent) -> None:
        for a in agents:
            self.register(a)

    def get(self, agent_id: str) -> Optional[BaseAgent]:
        if self._brain is not None:
            agent = self._brain.get_agent(agent_id)
            if agent is not None:
                return agent
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        if self._brain is not None:
            return [a.info() for a in self._brain._agent_instances.values()]
        return [
            {"agent_id": a.agent_id, "agent_name": a.agent_name,
             "description": a.description, "status": a.status.value,
             "dependencies": a.dependencies, "version": a.version}
            for a in self._agents.values()
        ]

    def list_by_status(self, status: AgentStatus) -> List[BaseAgent]:
        return [a for a in self._agents.values() if a.status == status]

    @property
    def count(self) -> int:
        if self._brain is not None:
            return len(self._brain._agent_instances)
        return len(self._agents)

    # ------------------------------------------------------------------
    # Dependency resolution
    # ------------------------------------------------------------------

    def _resolve_order(self, agent_ids: List[str]) -> List[str]:
        """Topological sort of requested agents by dependency graph."""
        graph: Dict[str, List[str]] = {}
        for aid in agent_ids:
            agent = self.get(aid)
            if not agent:
                raise ValueError(f"Unknown agent: {aid}")
            graph[aid] = [d for d in agent.dependencies if d in agent_ids]

        visited: set = set()
        visiting: set = set()
        resolved: List[str] = []

        def dfs(node: str, path: List[str]) -> None:
            if node in visiting:
                cycle = " -> ".join(path + [node])
                raise ValueError(f"Circular agent dependency detected: {cycle}")
            if node in visited:
                return
            visiting.add(node)
            for dep in graph.get(node, []):
                dfs(dep, path + [node])
            visiting.remove(node)
            visited.add(node)
            resolved.append(node)

        for aid in agent_ids:
            dfs(aid, [])
        return resolved

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def run_agent(self, agent_id: str, context: Dict[str, Any]) -> AgentResult:
        agent = self.get(agent_id)
        if not agent:
            return AgentResult(
                agent_id=agent_id, agent_name="Unknown",
                status=AgentStatus.FAILED, error=f"Agent not found: {agent_id}",
            )
        timeout = self._agent_timeout_seconds(context)
        try:
            return await asyncio.wait_for(agent.run(context), timeout=timeout)
        except asyncio.TimeoutError:
            return AgentResult(
                agent_id=agent_id,
                agent_name=agent.agent_name,
                status=AgentStatus.FAILED,
                error=f"Timed out after {timeout}s",
            )

    async def run_pipeline(
        self,
        agent_ids: List[str],
        context: Dict[str, Any],
        stop_on_failure: bool = True,
    ) -> Dict[str, AgentResult]:
        """
        Run a list of agents in dependency order, passing the shared context.
        Each agent's output is merged into context under agent_results[agent_id].
        """
        if "agent_results" not in context:
            context["agent_results"] = {}

        order = self._resolve_order(agent_ids)
        results: Dict[str, AgentResult] = {}
        allow_partial_agents = set(context.get("allow_partial_agents", [])) | self._PARTIAL_DEPENDENCY_AGENTS
        timeout = self._agent_timeout_seconds(context)

        for aid in order:
            agent = self.get(aid)
            if not agent:
                continue

            # Check dependencies
            prior_results = context.get("agent_results", {})
            missing_deps = [
                d for d in agent.dependencies
                if d not in results and d not in prior_results
            ]
            failed_deps = [
                d for d in agent.dependencies
                if d in results and results[d].status in {AgentStatus.FAILED, AgentStatus.BLOCKED}
            ]
            failed_deps.extend(
                d for d in agent.dependencies
                if (
                    d in prior_results
                    and isinstance(prior_results[d], dict)
                    and prior_results[d].get("status") in {AgentStatus.FAILED.value, AgentStatus.BLOCKED.value}
                )
            )
            if missing_deps:
                result = AgentResult(
                    agent_id=aid, agent_name=agent.agent_name,
                    status=AgentStatus.BLOCKED,
                    error=f"Missing dependencies: {missing_deps}",
                )
                results[aid] = result
                if stop_on_failure:
                    break
                continue
            if failed_deps and aid not in allow_partial_agents and not context.get("continue_on_failed_dependencies", False):
                result = AgentResult(
                    agent_id=aid, agent_name=agent.agent_name,
                    status=AgentStatus.BLOCKED,
                    error=f"Failed dependencies: {failed_deps}",
                    output={"failed_dependencies": failed_deps},
                )
                results[aid] = result
                context["agent_results"][aid] = result.to_dict()
                if stop_on_failure:
                    break
                continue

            # Merge upstream outputs into context for this agent
            run_context = dict(context)
            run_context["upstream"] = {
                dep: results[dep].output if dep in results else prior_results.get(dep, {}).get("output", {})
                for dep in agent.dependencies
                if dep in results or dep in prior_results
            }
            if failed_deps:
                run_context["degraded_mode"] = True
                run_context["failed_dependencies"] = failed_deps

            try:
                result = await asyncio.wait_for(agent.run(run_context), timeout=timeout)
            except asyncio.TimeoutError:
                result = AgentResult(
                    agent_id=aid,
                    agent_name=agent.agent_name,
                    status=AgentStatus.FAILED,
                    error=f"Timed out after {timeout}s",
                    execution_time_ms=int(timeout * 1000),
                )
            results[aid] = result
            context["agent_results"][aid] = result.to_dict()

            if result.status == AgentStatus.FAILED and stop_on_failure:
                logger.warning(f"Pipeline stopped at [{aid}] due to failure")
                break

        return results

    @staticmethod
    def _agent_timeout_seconds(context: Dict[str, Any]) -> float:
        try:
            timeout = float(context.get("agent_timeout_seconds", 180))
        except (TypeError, ValueError):
            timeout = 180.0
        return max(1.0, timeout)
