"""
System, SLT Dashboard, and SOR Legacy API Router.
Contains /api/slt/*, /api/sor/legacy/* endpoints.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.core.config import settings as boq_settings
from app.core.security import require_role
from app.schemas.response_models import AdminActionResult, SLTDashboardResponse, SORStatsResponse
from app.sor.sor_service import sor_service

logger = logging.getLogger("procureflow")
router = APIRouter()


def _enqueue_admin_task(action: str) -> Dict[str, Any]:
    from app.workers.tasks.maintenance_tasks import run_admin_maintenance_task

    task = run_admin_maintenance_task.delay(action)
    return {
        "success": True,
        "message": f"{action} queued",
        "job_id": task.id,
        "status": "processing",
    }


@router.get("/slt/dashboard", response_model=SLTDashboardResponse)
async def slt_dashboard():
    """Senior Leadership Team dashboard — aggregated executive view."""
    from app.agents import AgentRegistry
    registry = AgentRegistry()
    agents = registry.list_agents()

    from app.services.bwdb_monitor import bwdb_monitor
    from app.services.monitor_config import monitor_config_service

    monitor_stats = {}
    try:
        ms = await bwdb_monitor.get_stats()
        if isinstance(ms, dict):
            monitor_stats = ms
    except Exception:
        pass

    embed_stats = {"available": False, "reason": "embedding dependencies unavailable"}
    try:
        from app.services.tender_embedding import tender_embedding_service

        es = tender_embedding_service.get_stats()
        if isinstance(es, dict):
            embed_stats = {"available": True, **es}
    except Exception:
        pass

    config = {}
    try:
        config = monitor_config_service.get_config()
    except Exception:
        pass

    alert_history = []
    try:
        alert_history = await bwdb_monitor.get_alert_history(limit=10)
    except Exception:
        pass

    pipeline_phases = {}
    from app.agents.orchestrator import PipelinePhase, PIPELINE_DEFINITION
    for phase_name, phase in PipelinePhase.__members__.items():
        agent_ids = PIPELINE_DEFINITION.get(phase, [])
        registered = [a for a in agents if a["agent_id"] in agent_ids]
        pipeline_phases[phase.value] = {
            "total": len(agent_ids),
            "registered": len(registered),
            "agents": agent_ids,
        }

    return {
        "success": True,
        "slt": {
            "system": {
                "app": boq_settings.APP_NAME,
                "version": boq_settings.VERSION,
                "agents_total": len(agents),
                "agents_active": sum(1 for a in agents if a.get("status") in ("idle", "success", "ready")),
                "agents_idle": sum(1 for a in agents if a.get("status") in ("idle", "success", "ready")),
            },
            "pipeline_phases": pipeline_phases,
            "monitor": {
                "config": config,
                "stats": monitor_stats,
                "recent_alerts": alert_history[:5] if alert_history else [],
            },
            "embeddings": embed_stats,
            "total_tenders_monitored": monitor_stats.get("total_scanned", 0) or embed_stats.get("total_indexed", 0) or 0,
            "alerts_sent": len(alert_history) if alert_history else 0,
            "pipeline_ready": all(
                p["registered"] == p["total"] for p in pipeline_phases.values()
            ) if pipeline_phases else False,
        },
    }


@router.get("/sor/legacy/stats", response_model=SORStatsResponse)
async def sor_stats():
    """Get SOR loading statistics for all agencies."""
    agencies = {}
    for a in ['BWDB', 'PWD', 'LGED']:
        agencies[a] = sor_service.get_stats(a)
    return {"success": True, "agencies": agencies}


@router.post("/admin/rebuild-lifecycle", response_model=AdminActionResult)
async def admin_rebuild_lifecycle(user: dict = Depends(require_role("owner", "admin"))):
    """Admin: Rebuild procurement_lifecycle from awards + APP records."""
    return _enqueue_admin_task("rebuild_lifecycle")


@router.post("/admin/rebuild-agencies", response_model=AdminActionResult)
async def admin_rebuild_agencies(user: dict = Depends(require_role("owner", "admin"))):
    """Admin: Build unified agency master from all data sources."""
    return _enqueue_admin_task("rebuild_agencies")


@router.post("/admin/import-opening-reports", response_model=AdminActionResult)
async def admin_import_opening_reports(user: dict = Depends(require_role("owner", "admin"))):
    """Admin: Import crawled opening reports from JSON files."""
    return _enqueue_admin_task("import_opening_reports")


@router.post("/admin/rebuild-contractor-dna", response_model=AdminActionResult)
async def admin_rebuild_contractor_dna(user: dict = Depends(require_role("owner", "admin"))):
    """Admin: Rebuild contractor DNA from award_records_v2."""
    return _enqueue_admin_task("rebuild_contractor_dna")
