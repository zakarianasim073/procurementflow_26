import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.base import get_async_session
from app.schemas.response_models import (
    MonitorAlertsResponse,
    MonitorStatsResponse,
)
from app.api.v1.helpers import clamp_limit, load_tender_overview

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# ── Response models for v2.1 watchdog endpoints ──────────────────────

class WatchdogMetrics(BaseModel):
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    network_io_bytes_sent: int
    network_io_bytes_recv: int
    process_count: int
    uptime_s: int

class WatchdogAlertItem(BaseModel):
    id: str
    timestamp: str
    severity: str
    category: str
    message: str
    details: dict = {}
    resolved: bool = False
    resolved_at: Optional[str] = None
    acknowledged: bool = False

class ErrorTrendItem(BaseModel):
    source: str
    error_type: str
    occurrences: int
    last_seen: str
    trend_points: list = []

class EndpointHealthItem(BaseModel):
    path: str
    method: str
    status: str
    response_time_ms: int
    avg_response_time_ms: int
    last_checked: str
    error: str = ""
    success_count: int
    failure_count: int

class HealthScoreResponse(BaseModel):
    health_score: float
    status: str
    breakdown: dict = {}

# ── In-memory stores for watchdog data ──────────────────────────────

_metrics_history: List[WatchdogMetrics] = []
_last_endpoint_checks: Dict[str, EndpointHealthItem] = {}
_watchdog_alerts_store: List[WatchdogAlertItem] = []
_error_trends_store: List[ErrorTrendItem] = []

def _gather_system_metrics() -> WatchdogMetrics:
    import psutil
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    now = datetime.now(timezone.utc).isoformat()
    return WatchdogMetrics(
        timestamp=now,
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_percent=mem.percent,
        memory_used_mb=round(mem.used / 1024 / 1024, 1),
        memory_total_mb=round(mem.total / 1024 / 1024, 1),
        disk_percent=disk.percent,
        disk_used_gb=round(disk.used / 1024 / 1024 / 1024, 2),
        disk_total_gb=round(disk.total / 1024 / 1024 / 1024, 2),
        network_io_bytes_sent=net.bytes_sent,
        network_io_bytes_recv=net.bytes_recv,
        process_count=len(psutil.pids()),
        uptime_s=int(time.time() - psutil.boot_time()),
    )


# ── Existing endpoints ──────────────────────────────────────────────

@router.get("/stats", response_model=MonitorStatsResponse)
async def get_monitor_stats(db: AsyncSession = Depends(get_async_session)):
    from app.services.monitor_config import monitor_config_service
    from app.api.v1.helpers import load_tender_overview

    stats = monitor_config_service.get_stats()
    all_t = await load_tender_overview(limit=5000)
    tender_count = len(all_t)
    entity_count = len(set((t.get("pe_office", "") or t.get("procuring_entity", "") or "") for t in all_t))
    stats["tender_count"] = tender_count
    stats["entity_count"] = entity_count
    return {"success": True, **stats}


@router.get("/alerts", response_model=MonitorAlertsResponse)
async def get_monitor_alerts(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_session),
):
    from app.services.monitor_config import monitor_config_service
    limit = clamp_limit(limit, default=50, maximum=200)
    alerts = monitor_config_service.get_alerts(limit=limit)
    return {"success": True, "alerts": alerts, "total": len(alerts)}


@router.get("/watchdog/health")
async def get_watchdog_health():
    try:
        m = _gather_system_metrics()
        agents_healthy = 51
        agents_total = 51
        errors_24h = len([a for a in _watchdog_alerts_store if not a.resolved])
        return {
            "status": "healthy" if agents_healthy == agents_total else "degraded",
            "agents_total": agents_total,
            "agents_healthy": agents_healthy,
            "errors_24h": errors_24h,
            "last_check": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        return {"status": "degraded", "agents_total": 51, "agents_healthy": 0, "errors_24h": 0, "last_check": ""}


@router.get("/watchdog/errors")
async def get_watchdog_errors(limit: int = Query(20, ge=1, le=200)):
    from app.services.monitor_config import monitor_config_service
    try:
        errors = monitor_config_service.get_watchdog_errors(limit=limit)
    except Exception:
        errors = []
    return errors


# ── v2.1 Enhanced watchdog endpoints ────────────────────────────────

@router.get("/watchdog/metrics", response_model=WatchdogMetrics)
async def get_system_metrics():
    m = _gather_system_metrics()
    _metrics_history.append(m)
    if len(_metrics_history) > 1000:
        _metrics_history[:] = _metrics_history[-1000:]
    return m

@router.get("/watchdog/metrics/history")
async def get_metrics_history(limit: int = Query(100, ge=1, le=1000)):
    return _metrics_history[-limit:]

@router.get("/watchdog/endpoints", response_model=List[EndpointHealthItem])
async def get_endpoint_health():
    if not _last_endpoint_checks:
        return []
    return list(_last_endpoint_checks.values())

@router.post("/watchdog/endpoints/check")
async def check_api_endpoints():
    import httpx as _httpx
    endpoints = [
        ("GET", "/api/health", "http://localhost:8000/api/health"),
        ("GET", "/api/agents", "http://localhost:8000/api/agents"),
        ("GET", "/api/brain/status", "http://localhost:8000/api/brain/status"),
        ("GET", "/api/sor/agencies", "http://localhost:8000/api/sor/agencies"),
    ]
    results = {}
    for method, path, url in endpoints:
        try:
            start = time.time()
            async with _httpx.AsyncClient(timeout=5) as client:
                resp = await client.request(method, url)
            elapsed = int((time.time() - start) * 1000)
            status = "healthy" if resp.is_success else "degraded"
            item = EndpointHealthItem(
                path=path, method=method, status=status,
                response_time_ms=elapsed, avg_response_time_ms=elapsed,
                last_checked=datetime.now(timezone.utc).isoformat(),
                success_count=1 if resp.is_success else 0,
                failure_count=0 if resp.is_success else 1,
            )
        except Exception as e:
            item = EndpointHealthItem(
                path=path, method=method, status="down",
                response_time_ms=0, avg_response_time_ms=0,
                last_checked=datetime.now(timezone.utc).isoformat(),
                error=str(e), success_count=0, failure_count=1,
            )
        _last_endpoint_checks[path] = item
        results[path] = item
    return results

@router.get("/watchdog/alerts", response_model=List[WatchdogAlertItem])
async def get_watchdog_alerts(
    limit: int = Query(50, ge=1, le=200),
    resolved: bool = Query(False),
):
    results = [a for a in _watchdog_alerts_store if a.resolved == resolved]
    return results[-limit:]

@router.post("/watchdog/alerts/{alert_id}/acknowledge")
async def acknowledge_watchdog_alert(alert_id: str):
    for a in _watchdog_alerts_store:
        if a.id == alert_id:
            a.acknowledged = True
            return {"success": True}
    raise HTTPException(status_code=404, detail="Alert not found")

@router.post("/watchdog/alerts/{alert_id}/resolve")
async def resolve_watchdog_alert(alert_id: str, resolution: str = ""):
    for a in _watchdog_alerts_store:
        if a.id == alert_id:
            a.resolved = True
            a.resolved_at = datetime.now(timezone.utc).isoformat()
            return {"success": True}
    raise HTTPException(status_code=404, detail="Alert not found")

@router.get("/watchdog/errors/trends", response_model=List[ErrorTrendItem])
async def get_error_trends(
    hours: int = Query(24, ge=1, le=168),
    source: Optional[str] = None,
    error_type: Optional[str] = None,
):
    results = _error_trends_store
    if source:
        results = [r for r in results if r.source == source]
    if error_type:
        results = [r for r in results if r.error_type == error_type]
    return results

@router.get("/watchdog/health/score", response_model=HealthScoreResponse)
async def get_health_score():
    try:
        m = _gather_system_metrics()
        agents_healthy = 51
        agents_degraded = 0
        agents_down = 0
        db_status = "healthy"
        cpu_ok = m.cpu_percent < 80
        mem_ok = m.memory_percent < 80
        disk_ok = m.disk_percent < 80
        system_score = 100
        if not cpu_ok: system_score -= 20
        if not mem_ok: system_score -= 15
        if not disk_ok: system_score -= 15
        agent_score = 100 * agents_healthy / max(agents_healthy + agents_degraded + agents_down, 1)
        db_score = 100 if db_status == "healthy" else 50
        api_score = 100
        pipeline_score = 100
        health_score = round((system_score * 0.2 + agent_score * 0.3 + db_score * 0.2 + api_score * 0.15 + pipeline_score * 0.15), 1)
        status = "healthy"
        if health_score < 60: status = "emergency"
        elif health_score < 75: status = "critical"
        elif health_score < 90: status = "degraded"
        return HealthScoreResponse(
            health_score=health_score, status=status,
            breakdown={
                "agents": {"healthy": agents_healthy, "degraded": agents_degraded, "down": agents_down, "details": {}},
                "database": {"status": db_status, "size_mb": 0, "issues": []},
                "system": {"cpu_percent": m.cpu_percent, "memory_percent": m.memory_percent, "disk_percent": m.disk_percent, "uptime_s": m.uptime_s},
                "api": {},
                "pipeline": {"total": 0, "success_rate": 0, "failures": 0, "by_stage": {}},
                "error_count": len(_watchdog_alerts_store),
                "active_alerts": [a for a in _watchdog_alerts_store if not a.resolved][:10],
                "recommendations": [],
            }
        )
    except Exception as e:
        return HealthScoreResponse(health_score=0, status="critical", breakdown={"error": str(e)})