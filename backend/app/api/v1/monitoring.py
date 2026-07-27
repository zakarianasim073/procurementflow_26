"""
Monitoring Dashboard API Router.
Contains /api/monitor/* endpoints.
"""

from typing import Any, Dict

from fastapi import APIRouter, Query

from app.api.v1.helpers import clamp_limit, load_tender_overview
from app.schemas.response_models import (
    MonitorAlertsResponse,
    MonitorConfigResponse,
    MonitorConfigUpdateResponse,
    MonitorScanResponse,
    MonitorStatsResponse,
    MonitorToggleResponse,
)

router = APIRouter()


@router.get("/monitor/config", response_model=MonitorConfigResponse)
async def get_monitor_config():
    """Get current monitor configuration."""
    from app.services.monitor_config import monitor_config_service
    return monitor_config_service.get_config()


@router.post("/monitor/config", response_model=MonitorConfigUpdateResponse)
async def update_monitor_config(req: Dict[str, Any]):
    """Update monitor configuration."""
    from app.services.monitor_config import monitor_config_service
    config = monitor_config_service.update_config(req)
    return {"success": True, "config": config}


@router.post("/monitor/config/reset", response_model=MonitorConfigUpdateResponse)
async def reset_monitor_config():
    """Reset monitor config to defaults."""
    from app.services.monitor_config import monitor_config_service
    config = monitor_config_service.reset_config()
    return {"success": True, "config": config}


@router.post("/monitor/toggle", response_model=MonitorToggleResponse)
async def toggle_monitor(req: Dict[str, Any]):
    """Enable/disable monitor."""
    from app.services.monitor_config import monitor_config_service
    enabled = req.get("enabled")
    state = monitor_config_service.toggle(enabled)
    return {"success": True, "enabled": state}


@router.post("/monitor/scan", response_model=MonitorScanResponse)
async def run_monitor_scan():
    """Run a manual monitoring scan against collected tender data."""
    from app.services.monitor_config import monitor_config_service
    results = monitor_config_service.run_scan()
    return {"success": True, "results": results}


@router.get("/monitor/alerts", response_model=MonitorAlertsResponse)
async def get_monitor_alerts(limit: int = Query(50, ge=1, le=200)):
    """Get recent monitor alerts."""
    from app.services.monitor_config import monitor_config_service
    limit = clamp_limit(limit, default=50, maximum=200)
    alerts = monitor_config_service.get_alerts(limit=limit)
    return {"success": True, "alerts": alerts, "total": len(alerts)}


@router.get("/monitor/stats", response_model=MonitorStatsResponse)
async def get_monitor_stats():
    """Get monitor statistics."""
    from app.services.monitor_config import monitor_config_service
    stats = monitor_config_service.get_stats()
    all_t = await load_tender_overview(limit=5000)
    tender_count = len(all_t)
    entity_count = len(set((t.get("pe_office", "") or t.get("procuring_entity", "") or "") for t in all_t))
    stats["tender_count"] = tender_count
    stats["entity_count"] = entity_count
    return {"success": True, **stats}


@router.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus /metrics endpoint — all domain metrics (T-017/OBS-01).

    Exposed metrics:
    - procureflow_api_request_duration_seconds (histogram) — threshold p95 > 5s
    - procureflow_boq_comparison_duration_seconds (histogram) — threshold > 120s
    - procureflow_pipeline_execution_duration_seconds (histogram) — threshold > 300s
    - procureflow_crawl_success_ratio (gauge) — threshold < 90%
    - procureflow_db_pool_usage_ratio (gauge) — threshold > 80%
    - procureflow_knowledge_store_entries (gauge) — threshold > 1800/2000
    - procureflow_registered_agents (gauge)
    - procureflow_celery_tasks_total (counter)
    - procureflow_process_uptime_seconds (gauge)
    """
    try:
        from prometheus_client import REGISTRY, generate_latest
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            generate_latest(REGISTRY).decode("utf-8"),
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except ImportError:
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse("Prometheus client not installed\n")
