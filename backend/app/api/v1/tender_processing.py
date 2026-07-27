"""
Tender Processing and Opening Reports API Router.
Contains /api/tender/{tender_id}/process-with-agents, /api/tender/{tender_id}/process-async,
/api/opening-reports, and /api/ppr/slt-analysis endpoints.
"""

import logging
import hashlib
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as boq_settings
from app.api.v1.helpers import clamp_limit, redis_broker_available, load_tender_overview
from app.core.security import get_current_user
from app.db.base import get_async_session
from app.models.intelligence import KnowledgeEntry

logger = logging.getLogger("procureflow")
router = APIRouter()


# ── Tender Processing Endpoints ─────────────────────────────────────────

@router.post("/tender/{tender_id}/process-with-agents")
async def process_tender_with_agents(tender_id: str,
                                      sor_agency: str = "BWDB",
                                      zone: str = None,
                                      run_live_acquisition: bool = False,
                                      full_pipeline: bool = False,
                                      db: AsyncSession = Depends(get_async_session)):
    """
    Run the full agent pipeline for a tender, then generate documents.
    Works even without pre-uploaded documents (agents run in demo mode).
    """
    from app.agents import AgentRegistry, WorkflowOrchestrator
    from app.services.tender_manager import tender_manager
    from app.services.tender_bundle import tender_bundle_processor

    file_paths = {}
    for doc_type in ['notice', 'tds', 'tds_2', 'boq', 'sor']:
        try:
            path = tender_manager.get_document_path(tender_id, doc_type)
            if path and Path(path).exists():
                file_paths[doc_type] = path
        except Exception:
            pass

    backend_root = Path(__file__).resolve().parents[3]
    upload_roots = [
        Path(boq_settings.BASE_DIR) / "uploads",
        Path(boq_settings.BASE_DIR) / "uploads" / tender_id,
        Path(boq_settings.BASE_DIR) / "runtime" / "tender_acquisition" / tender_id / "documents",
        backend_root / "uploads" / tender_id,
        backend_root / "runtime" / "tender_acquisition" / tender_id / "documents",
    ]
    for upload_dir in upload_roots:
        if upload_dir.exists():
            files = upload_dir.rglob("*") if upload_dir.name == tender_id or "tender_acquisition" in str(upload_dir) else upload_dir.iterdir()
        else:
            files = []
        for f in files:
            if not f.is_file():
                continue
            if upload_dir.name == tender_id or tender_id in f.stem or tender_id in f.parts:
                for doc_type in ['notice', 'tds', 'tds_2', 'boq', 'sor']:
                    lower_path = str(f).lower()
                    if doc_type.lower() in lower_path or f.suffix.lower() in ['.pdf', '.xlsx', '.xls']:
                        if doc_type not in file_paths:
                            file_paths[doc_type] = str(f)

    registry = AgentRegistry()
    # Agent 027 is a coordinator rather than a leaf registry agent. Older
    # code looked it up in AgentRegistry and made every live acquisition
    # request fail with "Orchestrator not available".
    orch = registry.get("agent-027-orchestrator") or WorkflowOrchestrator()

    started = time.perf_counter()
    quality_gate: Dict[str, Any] = {}
    if full_pipeline:
        criteria_entry = (
            await db.execute(
                select(KnowledgeEntry)
                .where(
                    KnowledgeEntry.tender_id == tender_id,
                    KnowledgeEntry.entry_type == "tds_criteria",
                    KnowledgeEntry.is_archived.is_(False),
                )
                .order_by(KnowledgeEntry.updated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        persisted_tds_criteria = {}
        if criteria_entry and isinstance(criteria_entry.data, dict):
            persisted_tds_criteria = criteria_entry.data.get("payload", criteria_entry.data)

        pipeline_result = await orch.run({
            "mode": "full",
            "tender_id": tender_id,
            "file_paths": file_paths,
            "persisted_tds_criteria": persisted_tds_criteria,
            "continue_on_failure": True,
            "agent_timeout_seconds": 180,
            "acquisition_subprocess_timeout_seconds": 60,
        })
        pipeline_payload = pipeline_result.to_dict()
    elif file_paths or run_live_acquisition:
        agent_ids = []
        agent_results: Dict[str, Any] = {}
        if run_live_acquisition:
            # Acquisition must run first so downloaded paths are available to
            # Document AI/BOQ/spec extraction. Calling the leaf agent directly
            # is intentional: this is a user-selected tender, so the radar scan
            # dependency has already been satisfied by that selection.
            acquisition_result = await registry.run_agent(
                "agent-002-tender-acquisition",
                {
                    "tender_id": tender_id,
                    "agent_timeout_seconds": 180,
                    "acquisition_subprocess_timeout_seconds": 60,
                },
            )
            agent_results["agent-002-tender-acquisition"] = acquisition_result.to_dict()

            acquisition_output = acquisition_result.output if isinstance(acquisition_result.output, dict) else {}
            candidates = acquisition_output.get("downloaded_files", []) or acquisition_output.get("documents", [])
            if isinstance(candidates, dict):
                candidates = [{"doc_type": key, "path": value} for key, value in candidates.items()]
            for item in candidates if isinstance(candidates, list) else []:
                if not isinstance(item, dict):
                    continue
                candidate_path = item.get("path") or item.get("file_path")
                if not candidate_path or not Path(candidate_path).exists():
                    continue
                label = str(item.get("doc_type") or item.get("type") or Path(candidate_path).stem).lower()
                doc_type = next((kind for kind in ["tds_2", "notice", "tds", "boq", "sor"] if kind in label), None)
                if doc_type:
                    file_paths[doc_type] = str(candidate_path)
        else:
            agent_results["agent-002-tender-acquisition"] = {
                "status": "success",
                "output": {
                    "tender_id": tender_id,
                    "status": "local_documents",
                    "documents": [
                        {"source": "local_upload", "name": Path(path).name, "path": path, "type": doc_type}
                        for doc_type, path in file_paths.items()
                    ],
                    "downloaded_files": [
                        {"doc_type": doc_type, "path": path, "source": "local_upload"}
                        for doc_type, path in file_paths.items()
                    ],
                },
            }
        from app.services.tender_data_quality import evaluate_tender_data_quality

        quality_gate = await evaluate_tender_data_quality(
            db, tender_id=tender_id, file_paths=file_paths,
        )
        if not quality_gate["agent_use_allowed"]:
            pipeline_payload = {
                "agent_id": "agent-027-orchestrator",
                "agent_name": "Workflow Orchestrator",
                "status": "blocked",
                "error": "Pre-agent data quality guardrails blocked downstream processing",
                "execution_time_ms": int((time.perf_counter() - started) * 1000),
                "output": {
                    "pipeline_run_id": "",
                    "mode": "quality_blocked",
                    "pipeline_complete": False,
                    "agent_results": agent_results,
                    "quality_gate": quality_gate,
                },
            }
        else:
            agent_ids.extend([
                "agent-004-document-ai",
                "agent-005-boq-intelligence",
                "agent-006-spec-intelligence",
                "agent-046-data-quality-validator",
                "agent-007-eligibility-compliance",
                "agent-009-ppr-evaluation",
                "agent-024-submission-validation",
                "agent-034-tender-document",
                "agent-032-document-preparation",
                "agent-031-tender-preparation",
            ])
            criteria_entry = (
                await db.execute(
                    select(KnowledgeEntry)
                    .where(
                        KnowledgeEntry.tender_id == tender_id,
                        KnowledgeEntry.entry_type == "tds_criteria",
                        KnowledgeEntry.is_archived.is_(False),
                    )
                    .order_by(KnowledgeEntry.updated_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            persisted_tds_criteria = {}
            if criteria_entry and isinstance(criteria_entry.data, dict):
                persisted_tds_criteria = criteria_entry.data.get("payload", criteria_entry.data)
            pipeline_result = await orch.run({
                "mode": "agents",
                "agent_ids": agent_ids,
                "tender_id": tender_id,
                "file_paths": file_paths,
                "persisted_tds_criteria": persisted_tds_criteria,
                "agent_results": agent_results,
                "continue_on_failure": True,
                "continue_on_failed_dependencies": True,
                "allow_partial_agents": ["agent-031-tender-preparation"],
                # PDF table extraction and TDS parsing are CPU/file-I/O heavy. The old
                # 45-second wrapper killed healthy agents before their own 120-second
                # execution budget, leaving incomplete persisted runtime output.
                "agent_timeout_seconds": 120,
                "acquisition_subprocess_timeout_seconds": 60,
            })
            pipeline_payload = pipeline_result.to_dict()
            pipeline_output = pipeline_payload.get("output")
            if isinstance(pipeline_output, dict) and agent_results:
                downstream_results = pipeline_output.setdefault("agent_results", {})
                if isinstance(downstream_results, dict):
                    pipeline_output["agent_results"] = {**agent_results, **downstream_results}
                    pipeline_output["agents_run"] = len(pipeline_output["agent_results"])
    else:
        pipeline_payload = {
            "agent_id": "agent-027-orchestrator",
            "agent_name": "Workflow Orchestrator",
            "status": "skipped",
            "error": None,
            "execution_time_ms": int((time.perf_counter() - started) * 1000),
            "output": {
                "pipeline_run_id": "",
                "mode": "local_documents_required",
                "pipeline_complete": False,
                "message": "No local tender documents found. Upload documents or call with run_live_acquisition=true.",
            },
        }

    agent_outputs = {}
    if hasattr(orch, '_phase_results') and orch._phase_results:
        for phase_name, phase_data in orch._phase_results.items():
            agent_results = phase_data.get("agent_results", {})
            for aid, r in agent_results.items():
                output = getattr(r, 'output', None) if hasattr(r, 'output') else (r.get("output") if isinstance(r, dict) else None)
                if output:
                    agent_outputs[aid] = output
    agent_results = (pipeline_payload.get("output") or {}).get("agent_results", {})
    if isinstance(agent_results, dict):
        for aid, r in agent_results.items():
            output = r.get("output") if isinstance(r, dict) else None
            if output:
                agent_outputs[aid] = output

    doc_result = None
    if quality_gate and not quality_gate.get("agent_use_allowed", True):
        doc_result = {
            "success": False,
            "status": "blocked",
            "message": "Document generation blocked by pre-agent data quality guardrails.",
            "quality_gate": quality_gate,
        }
    elif file_paths:
        try:
            doc_result = await tender_bundle_processor.process_from_paths(
                tender_id=tender_id,
                file_paths=file_paths,
                sor_agency=sor_agency,
                zone=zone,
                agent_outputs=agent_outputs,
            )
        except Exception as e:
            logger.warning(f"Document generation skipped: {e}")
            doc_result = {"success": False, "error": str(e)}
    else:
        doc_result = {
            "success": False,
            "message": "No tender documents uploaded yet. Upload via /upload page first, then re-run.",
            "note": "Agents still ran with the tender ID for intelligence gathering.",
        }

    # Persist the complete runtime snapshot through the canonical Brain. Agent
    # runs already live in agent_results; this knowledge entry preserves their
    # composed outputs plus generated/downloadable artifact provenance.
    artifacts: list[dict[str, Any]] = []
    seen_paths: set[str] = set()

    def file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def collect_artifacts(value: Any, label: str = "artifact") -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                collect_artifacts(nested, str(key))
        elif isinstance(value, list):
            for nested in value:
                collect_artifacts(nested, label)
        elif isinstance(value, str):
            path = Path(value)
            if path.exists() and path.is_file():
                resolved = str(path.resolve())
                if resolved not in seen_paths:
                    seen_paths.add(resolved)
                    artifacts.append({
                        "name": path.name,
                        "kind": label,
                        "path": resolved,
                        "size_bytes": path.stat().st_size,
                        "sha256": file_sha256(path),
                    })

    collect_artifacts(file_paths, "source_document")
    collect_artifacts(doc_result, "generated_artifact")
    from app.api.brain_router import get_brain
    await get_brain().store_knowledge(
        agent_id="agent-027-orchestrator",
        entry_type="tender_pipeline_runtime",
        tender_id=tender_id,
        data={
            "pipeline_result": pipeline_payload,
            "agent_outputs": agent_outputs,
            "documents": doc_result,
            "artifacts": artifacts,
        },
        summary=f"Tender pipeline runtime persisted with {len(artifacts)} artifacts",
        tags=["runtime", "agent_outputs", "downloadable_artifacts", "works_only"],
    )

    return {
        "success": True,
        "tender_id": tender_id,
        "quality_gate": quality_gate,
        "pipeline_result": pipeline_payload,
        "documents": doc_result,
        "agent_outputs": agent_outputs,
        "artifacts": artifacts,
    }


@router.get("/tender/{tender_id}/data-quality")
async def get_tender_data_quality(
    tender_id: str,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    entry = (
        await db.execute(
            select(KnowledgeEntry)
            .where(
                KnowledgeEntry.tender_id == tender_id,
                KnowledgeEntry.entry_type == "tender_data_quality",
                KnowledgeEntry.is_archived.is_(False),
            )
            .order_by(KnowledgeEntry.updated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return {
        "success": True,
        "tender_id": tender_id,
        "quality": entry.data if entry else None,
        "updated_at": entry.updated_at.isoformat() if entry and entry.updated_at else None,
    }


@router.post("/tender/{tender_id}/data-quality/recheck")
async def recheck_tender_data_quality(
    tender_id: str,
    db: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    from app.services.tender_data_quality import evaluate_tender_data_quality

    quality = await evaluate_tender_data_quality(
        db, tender_id=tender_id, tenant_id=user.get("tenant_id"),
    )
    return {"success": True, "tender_id": tender_id, "quality": quality}


@router.post("/tender/{tender_id}/process-async")
async def process_tender_async(tender_id: str,
                                sor_agency: str = "BWDB",
                                zone: str = None):
    """Process a tender bundle in the background via Celery."""
    from app.workers.tasks import process_tender_bundle_task
    from app.services.tender_manager import tender_manager

    file_paths = {}
    for doc_type in ['notice', 'tds', 'tds_2', 'boq']:
        path = tender_manager.get_document_path(tender_id, doc_type)
        if path:
            file_paths[doc_type] = path

    if not file_paths:
        raise HTTPException(status_code=404, detail="No documents found for this tender")

    task = process_tender_bundle_task.delay(
        tender_id=tender_id,
        file_paths=file_paths,
        sor_agency=sor_agency,
        zone=zone,
    )

    return {
        "success": True,
        "task_id": task.id,
        "status_url": f"/api/pipeline/status/{task.id}",
    }


# ── Opening Reports Endpoint ──────────────────────────────────────────────

@router.get("/opening-reports")
async def list_opening_reports(limit: int = Query(50, ge=1, le=200)):
    """Return a lightweight list of opening reports for the live UI."""
    from sqlalchemy import select
    from app.db.base import get_session_factory
    from app.models.procurement import OpeningReport

    sf = get_session_factory()
    async with sf() as session:
        rows = (
            await session.execute(
                select(OpeningReport)
                .order_by(OpeningReport.opening_date.desc().nullslast(), OpeningReport.created_at.desc())
                .limit(clamp_limit(limit, default=50, maximum=200))
            )
        ).scalars().all()

    return {
        "success": True,
        "total": len(rows),
        "items": [
            {
                "id": row.id,
                "tender_id": row.tender_id,
                "opening_date": row.opening_date.isoformat() if row.opening_date else None,
                "pe_office": row.pe_office,
                "agency": row.agency,
                "zone": row.zone,
                "winner_name": row.winner_name,
                "winner_amount": float(row.winner_amount or 0),
                "has_slt": bool(row.has_slt),
                "has_alt": bool(row.has_alt),
                "bidders_count": len(row.bidders or []),
                "source_pdf": row.source_pdf,
            }
            for row in rows
        ],
    }


# ── PPR 2025 SLT Analysis Endpoint ────────────────────────────────────

class SLTAnalysisRequest(BaseModel):
    boq_items: list = []
    estimated_cost: float = 0
    bid_price: float = 0


@router.post("/ppr/slt-analysis")
async def ppr_slt_analysis(req: SLTAnalysisRequest):
    """Run PPR 2025 Rule 31 SLT/ALT analysis on BOQ data."""
    from app.agents.ppr_evaluation import _analyze_slt
    result = _analyze_slt(
        boq_items=req.boq_items,
        estimated_cost=req.estimated_cost,
        bid_price=req.bid_price,
    )
    return {"success": True, "analysis": result}
