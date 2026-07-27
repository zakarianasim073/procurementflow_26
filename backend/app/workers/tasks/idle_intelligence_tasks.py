"""Low-priority, Works-only intelligence precomputation for shortlisted tenders."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from redis import Redis
from sqlalchemy import text

from app.celery_app import REDIS_URL, celery_app
from app.db.database import get_sync_engine

logger = logging.getLogger("procureflow.tasks.idle_intelligence")

LOCK_KEY = "procureflow:idle-shortlist-intelligence"
CACHE_PREFIX = "idle_works_tender_"

# Read-only analytical agents only. Acquisition, crawling, submissions,
# notifications, document generation, and learning are deliberately excluded.
IDLE_ANALYTICAL_AGENTS = (
    "agent-004-document-ai",
    "agent-005-boq-intelligence",
    "agent-006-spec-intelligence",
    "agent-046-data-quality-validator",
    "agent-007-eligibility-compliance",
    "agent-008-risk-intelligence",
    "agent-009-ppr-evaluation",
    "agent-010-ppr-compliance",
    "agent-011-rate-analysis",
    "agent-012-market-rate-intelligence",
    "agent-013-competitor-intelligence",
    "agent-015-competitor-pricing",
    "agent-016-win-probability",
    "agent-017-bid-position-optimizer",
    "agent-036-moat-slt-analyzer",
    "agent-037-ppr2025-dashboard",
    "agent-044-sor-zone-matcher",
    "agent-049-material-margin-analyzer",
)
DOCUMENT_EVIDENCE = {
    "agent-004-document-ai": {"tender_document", "tds_text", "boq_text"},
    "agent-005-boq-intelligence": {"boq_text"},
    "agent-006-spec-intelligence": {"tds_text", "tds_criteria"},
}
IDLE_AGENT_TIMEOUT_SECONDS = 45


def _select_candidates(limit: int) -> list[dict[str, Any]]:
    """Return stale/missing HIGH then MEDIUM shortlist rows certified as Works."""
    with get_sync_engine().connect() as connection:
        rows = connection.execute(
            text("""
                WITH priorities AS (
                    SELECT tender_id,
                           max(priority_score) AS priority_score,
                           CASE
                               WHEN bool_or(priority_tier = 'HIGH') THEN 'HIGH'
                               ELSE 'MEDIUM'
                           END AS priority_tier
                    FROM client_priority_states
                    WHERE priority_tier IN ('HIGH', 'MEDIUM')
                    GROUP BY tender_id
                ),
                works_tenders AS (
                    SELECT DISTINCT ON (tender_id)
                           tender_id, package_no, title, agency_code, zone_name,
                           estimated_cost_bdt, procurement_method
                    FROM procurement_lifecycle
                    WHERE tender_id IS NOT NULL AND tender_id <> ''
                    ORDER BY tender_id, updated_at DESC NULLS LAST, package_no
                )
                SELECT l.tender_id,
                       l.package_no,
                       l.title,
                       l.agency_code,
                       l.zone_name,
                       l.estimated_cost_bdt,
                       l.procurement_method,
                       p.priority_score,
                       p.priority_tier
                FROM priorities p
                JOIN works_tenders l ON l.tender_id = p.tender_id
                LEFT JOIN pre_computed_intelligence cache
                  ON cache.cache_key = :prefix || l.tender_id
                WHERE (
                      cache.id IS NULL
                      OR cache.updated_at < now() - interval '24 hours'
                  )
                ORDER BY
                    CASE p.priority_tier WHEN 'HIGH' THEN 0 ELSE 1 END,
                    p.priority_score DESC,
                    cache.updated_at NULLS FIRST,
                    l.tender_id
                LIMIT :limit
            """),
            {"prefix": CACHE_PREFIX, "limit": limit},
        ).mappings()
        return [dict(row) for row in rows]


def _local_file_paths(tender_id: str) -> dict[str, str]:
    """Discover already-acquired documents without network access."""
    from app.core.config import settings
    from app.services.tender_manager import tender_manager

    paths: dict[str, str] = {}
    for doc_type in ("notice", "tds", "tds_2", "boq", "sor"):
        try:
            candidate = tender_manager.get_document_path(tender_id, doc_type)
            if candidate and Path(candidate).is_file():
                paths[doc_type] = str(Path(candidate).resolve())
        except Exception:
            continue

    tender_upload = Path(settings.BASE_DIR) / "uploads" / tender_id
    if tender_upload.is_dir():
        for candidate in tender_upload.rglob("*"):
            if not candidate.is_file():
                continue
            lowered = candidate.name.lower()
            doc_type = next(
                (kind for kind in ("tds_2", "notice", "tds", "boq", "sor") if kind in lowered),
                None,
            )
            if doc_type and doc_type not in paths:
                paths[doc_type] = str(candidate.resolve())
    return paths


def _knowledge_types(tender_id: str) -> set[str]:
    with get_sync_engine().connect() as connection:
        rows = connection.execute(
            text("""
                SELECT DISTINCT entry_type
                FROM knowledge_entries
                WHERE tender_id = :tender_id
                  AND is_archived = false
            """),
            {"tender_id": tender_id},
        )
        return {str(row[0]) for row in rows}


def _save_snapshot(tender: dict[str, Any], payload: dict[str, Any]) -> None:
    cache_key = f"{CACHE_PREFIX}{tender['tender_id']}"
    encoded = json.dumps(payload, default=str)
    with get_sync_engine().begin() as connection:
        connection.execute(
            text("""
                INSERT INTO pre_computed_intelligence (
                    id, cache_key, cache_data, intelligence_type, agency,
                    category, zone, tender_id, created_at, updated_at
                )
                VALUES (
                    gen_random_uuid()::text, :cache_key, CAST(:cache_data AS json),
                    'idle_shortlist', :agency, 'Works', :zone, :tender_id,
                    now(), now()
                )
                ON CONFLICT (cache_key) DO UPDATE SET
                    cache_data = EXCLUDED.cache_data,
                    intelligence_type = EXCLUDED.intelligence_type,
                    agency = EXCLUDED.agency,
                    category = EXCLUDED.category,
                    zone = EXCLUDED.zone,
                    tender_id = EXCLUDED.tender_id,
                    updated_at = now()
            """),
            {
                "cache_key": cache_key,
                "cache_data": encoded,
                "agency": tender.get("agency_code"),
                "zone": tender.get("zone_name"),
                "tender_id": tender["tender_id"],
            },
        )


async def _precompute_tender(tender: dict[str, Any], brain: Any) -> dict[str, Any]:
    tender_id = str(tender["tender_id"])
    context: dict[str, Any] = {
        "tender_id": tender_id,
        "package_no": tender.get("package_no"),
        "title": tender.get("title"),
        "agency": tender.get("agency_code") or "BWDB",
        "sor_agency": tender.get("agency_code") or "BWDB",
        "zone": tender.get("zone_name") or "A",
        "estimated_cost": tender.get("estimated_cost_bdt"),
        "procurement_method": tender.get("procurement_method"),
        "procurement_type": "Works",
        "category": "Works",
        "file_paths": _local_file_paths(tender_id),
        "upstream": {},
        "agent_results": {},
        "source": "idle_shortlist_precompute",
    }
    knowledge_types = _knowledge_types(tender_id)
    results: dict[str, Any] = {}

    for agent_id in IDLE_ANALYTICAL_AGENTS:
        required_evidence = DOCUMENT_EVIDENCE.get(agent_id)
        if (
            required_evidence
            and not context["file_paths"]
            and required_evidence.isdisjoint(knowledge_types)
        ):
            results[agent_id] = {
                "status": "skipped",
                "reason": "required persisted document evidence is unavailable",
            }
            continue
        agent = brain.get_agent(agent_id)
        if agent is None:
            results[agent_id] = {"status": "not_registered"}
            continue
        try:
            result = await asyncio.wait_for(
                agent.run(dict(context)),
                timeout=IDLE_AGENT_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            results[agent_id] = {
                "status": "failed",
                "error": f"idle timeout after {IDLE_AGENT_TIMEOUT_SECONDS}s",
            }
            continue
        result_data = result.to_dict()
        results[agent_id] = result_data
        context["agent_results"][agent_id] = result_data
        if result_data.get("status") == "success":
            context["upstream"][agent_id] = result_data.get("output") or {}

    succeeded = sum(1 for result in results.values() if result.get("status") == "success")
    snapshot = {
        "tender_id": tender_id,
        "package_no": tender.get("package_no"),
        "category": "Works",
        "agency": tender.get("agency_code"),
        "zone": tender.get("zone_name"),
        "priority_tier": tender.get("priority_tier"),
        "priority_score": tender.get("priority_score"),
        "documents_available": sorted(context["file_paths"]),
        "agents_requested": len(IDLE_ANALYTICAL_AGENTS),
        "agents_succeeded": succeeded,
        "agent_results": results,
        "precomputed_at": datetime.now(timezone.utc).isoformat(),
        "provenance": "certified procurement_lifecycle and persisted agent outputs",
    }
    _save_snapshot(tender, snapshot)
    return {
        "tender_id": tender_id,
        "agents_requested": len(IDLE_ANALYTICAL_AGENTS),
        "agents_succeeded": succeeded,
    }


async def _run_batch(limit: int) -> dict[str, Any]:
    from app.agents.core.brain import AgentBrain
    from app.api.brain_router import _register_all_agents_into_brain

    brain = AgentBrain()
    _register_all_agents_into_brain(brain)
    candidates = _select_candidates(limit)
    completed = []
    for tender in candidates:
        try:
            completed.append(await _precompute_tender(tender, brain))
        except Exception as exc:
            logger.exception("Idle intelligence failed for tender %s", tender.get("tender_id"))
            completed.append({"tender_id": tender.get("tender_id"), "error": str(exc)})
    return {
        "status": "complete",
        "works_candidates": len(candidates),
        "completed": completed,
    }


@celery_app.task(name="idle_shortlist_intelligence", queue="low")
def idle_shortlist_intelligence(limit: int = 5) -> dict[str, Any]:
    """Precompute a bounded batch while the low-priority worker is available."""
    safe_limit = max(1, min(int(limit), 20))
    redis_client = Redis.from_url(REDIS_URL)
    lock = redis_client.lock(LOCK_KEY, timeout=55 * 60, blocking_timeout=0)
    try:
        if not lock.acquire(blocking=False):
            return {"status": "skipped", "reason": "already_running"}
        return asyncio.run(_run_batch(safe_limit))
    except Exception as exc:
        logger.exception("Idle shortlist intelligence cycle failed")
        return {"status": "failed", "error": str(exc)}
    finally:
        try:
            if lock.owned():
                lock.release()
        finally:
            redis_client.close()
