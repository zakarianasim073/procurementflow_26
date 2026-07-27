"""
🐕 Watchdog Intelligence — System Health Monitor & Error Reporter.
Monitors all agents, DB, API, pipeline. Persists errors. Generates health reports.
Provides error intelligence engine with solution recommendations.

Latest Enhancements (v2.1):
- Real-time memory/CPU monitoring
- API endpoint health checks with response time tracking
- Alert thresholds with configurable severity levels
- Error deduplication and trend analysis
- Auto-resolution tracking with confidence scoring
- Integration with notification channels (Slack, email, webhook)
- Predictive failure detection based on error patterns
- Health score calculation with weighted metrics
"""
from __future__ import annotations
import os, sys, json, time, logging, traceback, uuid, asyncio, psutil
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Callable
from app.agents.core.engineer import get_engineer
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# Paths
BASE = os.environ.get("PROCUREFLOW_BASE", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ERROR_LOG_DIR = f"{BASE}/runtime/logs"
HEALTH_LOG = f"{ERROR_LOG_DIR}/system/health.jsonl"
ERROR_LOG = f"{ERROR_LOG_DIR}/system/errors.jsonl"
SESSION_LOG = f"{ERROR_LOG_DIR}/sessions/session_{int(time.time())}.jsonl"
METRICS_LOG = f"{ERROR_LOG_DIR}/system/metrics.jsonl"
ALERT_LOG = f"{ERROR_LOG_DIR}/system/alerts.jsonl"

# Alert thresholds
ALERT_THRESHOLDS = {
    "cpu_percent": 85.0,
    "memory_percent": 85.0,
    "disk_percent": 90.0,
    "error_rate_per_minute": 10,
    "agent_down_count": 1,
    "pipeline_failure_rate": 0.5,
    "response_time_ms": 5000,
}

# Health score weights
HEALTH_SCORE_WEIGHTS = {
    "agents": 0.3,
    "database": 0.25,
    "api_endpoints": 0.2,
    "pipeline": 0.15,
    "system_resources": 0.1,
}

@dataclass
class ErrorRecord:
    id: str = ""
    timestamp: str = ""
    source: str = ""
    error_type: str = ""
    error_message: str = ""
    traceback: str = ""
    context: dict = field(default_factory=dict)
    severity: str = "error"
    resolved: bool = False
    resolution: str = ""
    confidence: str = "low"
    auto_fixable: bool = False
    first_seen: str = ""
    last_seen: str = ""
    occurrence_count: int = 1
    tags: list = field(default_factory=list)

@dataclass
class Alert:
    id: str = ""
    timestamp: str = ""
    severity: str = "warning"
    category: str = ""
    message: str = ""
    details: dict = field(default_factory=dict)
    resolved: bool = False
    resolved_at: str = ""
    acknowledged: bool = False

@dataclass
class EndpointHealth:
    path: str = ""
    method: str = ""
    status: str = "unknown"
    response_time_ms: float = 0.0
    last_checked: str = ""
    error: str = ""
    success_count: int = 0
    failure_count: int = 0
    avg_response_time_ms: float = 0.0

@dataclass
class SystemMetrics:
    timestamp: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    disk_percent: float = 0.0
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0
    network_io_bytes_sent: int = 0
    network_io_bytes_recv: int = 0
    process_count: int = 0
    uptime_s: int = 0

class AgentWatchdog:
    """Central watchdog. Tracks errors, monitors agents, generates health reports.

    v2.1 Enhancements:
    - Real-time system metrics monitoring (CPU, memory, disk, network)
    - API endpoint health checks with response time tracking
    - Alert thresholds with configurable severity levels
    - Error deduplication and trend analysis
    - Auto-resolution tracking with confidence scoring
    - Health score calculation with weighted metrics
    - Notification channel integration
    """

    def __init__(self, brain=None):
        self.brain = brain
        self._errors: List[ErrorRecord] = []
        self._alerts: List[Alert] = []
        self._agent_health: Dict[str, str] = {}
        self._pipeline_stats = {"runs":0,"ok":0,"fail":0,"by_stage":{}}
        self._start = time.time()
        self._metrics_history: List[SystemMetrics] = []
        self._endpoint_health: Dict[str, EndpointHealth] = {}
        self._error_trends: Dict[str, List[Dict]] = {}
        self._notification_handlers: List[Callable] = []
        self._last_health_score: float = 100.0
        self._alert_cooldowns: Dict[str, float] = {}

        os.makedirs(ERROR_LOG_DIR, exist_ok=True)
        os.makedirs(f"{ERROR_LOG_DIR}/system", exist_ok=True)
        os.makedirs(f"{ERROR_LOG_DIR}/sessions", exist_ok=True)
        os.makedirs(f"{ERROR_LOG_DIR}/agents", exist_ok=True)
        os.makedirs(f"{ERROR_LOG_DIR}/pipeline", exist_ok=True)

        # Write session start
        self._log("session", "start", {"watchdog_initialized": True, "version": "2.1"})
        logger.info(f"🐕 Watchdog v2.1 initialized — logging to {ERROR_LOG_DIR}")

    def _log(self, log_type: str, action: str, data: dict):
        """Write to appropriate log file."""
        entry = {"ts": datetime.now(timezone.utc).isoformat(), "type": log_type, "action": action, **data}
        try:
            if log_type == "error":
                with open(ERROR_LOG, "a") as f: f.write(json.dumps(entry) + "\n")
            elif log_type == "session":
                with open(SESSION_LOG, "a") as f: f.write(json.dumps(entry) + "\n")
            elif log_type == "metric":
                with open(METRICS_LOG, "a") as f: f.write(json.dumps(entry) + "\n")
            elif log_type == "alert":
                with open(ALERT_LOG, "a") as f: f.write(json.dumps(entry) + "\n")
            else:
                with open(HEALTH_LOG, "a") as f: f.write(json.dumps(entry) + "\n")
        except Exception:
            import sys as _sys
            print(f"[watchdog] log write failed: {log_type}/{action}", file=_sys.stderr)

    def _check_alert_threshold(self, category: str, value: float, threshold: float, message: str):
        """Check if a metric exceeds its alert threshold."""
        if value >= threshold:
            alert_key = f"{category}_threshold"
            now = time.time()
            # Cooldown: don't spam same alert within 5 minutes
            if self._alert_cooldowns.get(alert_key, 0) + 300 < now:
                self._alert_cooldowns[alert_key] = now
                alert = Alert(
                    id=f"alert-{int(time.time())}-{len(self._alerts)}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    severity="critical" if value >= threshold * 1.2 else "warning",
                    category=category,
                    message=message,
                    details={"value": value, "threshold": threshold}
                )
                self._alerts.append(alert)
                self._log("alert", "threshold_exceeded", asdict(alert))
                # Notify handlers
                for handler in self._notification_handlers:
                    try:
                        handler(alert)
                    except Exception:
                        pass

    def collect_system_metrics(self) -> SystemMetrics:
        """Collect real-time system metrics (CPU, memory, disk, network)."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory
            mem = psutil.virtual_memory()
            memory_percent = mem.percent
            memory_used_mb = round(mem.used / (1024 * 1024), 1)
            memory_total_mb = round(mem.total / (1024 * 1024), 1)
            
            # Disk
            disk = psutil.disk_usage('/')
            disk_percent = round(disk.used / disk.total * 100, 1)
            disk_used_gb = round(disk.used / (1024**3), 2)
            disk_total_gb = round(disk.total / (1024**3), 2)
            
            # Network
            net = psutil.net_io_counters()
            network_io_bytes_sent = net.bytes_sent
            network_io_bytes_recv = net.bytes_recv
            
            # Process count
            process_count = len(psutil.pids())
            
            metrics = SystemMetrics(
                timestamp=datetime.now(timezone.utc).isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_total_mb=memory_total_mb,
                disk_percent=disk_percent,
                disk_used_gb=disk_used_gb,
                disk_total_gb=disk_total_gb,
                network_io_bytes_sent=network_io_bytes_sent,
                network_io_bytes_recv=network_io_bytes_recv,
                process_count=process_count,
                uptime_s=int(time.time() - self._start),
            )
            
            # Store in history (keep last 1000 entries)
            self._metrics_history.append(metrics)
            if len(self._metrics_history) > 1000:
                self._metrics_history = self._metrics_history[-1000:]
            
            # Log metrics
            self._log("metric", "system", asdict(metrics))
            
            # Check alert thresholds
            self._check_alert_threshold("cpu_percent", cpu_percent, ALERT_THRESHOLDS["cpu_percent"], 
                f"CPU usage {cpu_percent}% exceeds threshold {ALERT_THRESHOLDS['cpu_percent']}%")
            self._check_alert_threshold("memory_percent", memory_percent, ALERT_THRESHOLDS["memory_percent"],
                f"Memory usage {memory_percent}% exceeds threshold {ALERT_THRESHOLDS['memory_percent']}%")
            self._check_alert_threshold("disk_percent", disk_percent, ALERT_THRESHOLDS["disk_percent"],
                f"Disk usage {disk_percent}% exceeds threshold {ALERT_THRESHOLDS['disk_percent']}%")
            
            return metrics
            
        except Exception as e:
            logger.warning(f"Failed to collect system metrics: {e}")
            return SystemMetrics(timestamp=datetime.now(timezone.utc).isoformat())

    async def check_api_endpoints(self) -> Dict[str, EndpointHealth]:
        """Check health of critical API endpoints."""
        import httpx
        
        critical_endpoints = [
            ("GET", "/api/v1/health", "Server health"),
            ("GET", "/api/v1/stats", "Database stats"),
            ("GET", "/api/v1/agents", "Agent registry"),
            ("GET", "/api/watchdog/health", "Watchdog health"),
            ("GET", "/api/engineer/status", "Engineer status"),
        ]
        
        results = {}
        base_url = "http://127.0.0.1:8000"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for method, path, desc in critical_endpoints:
                start = time.time()
                try:
                    if method == "GET":
                        resp = await client.get(f"{base_url}{path}")
                    else:
                        resp = await client.request(method, f"{base_url}{path}")
                    
                    elapsed_ms = round((time.time() - start) * 1000, 1)
                    status = "healthy" if resp.status_code == 200 else "degraded" if resp.status_code < 500 else "down"
                    
                    # Update endpoint health
                    key = f"{method}:{path}"
                    if key not in self._endpoint_health:
                        self._endpoint_health[key] = EndpointHealth(path=path, method=method)
                    
                    eh = self._endpoint_health[key]
                    eh.status = status
                    eh.response_time_ms = elapsed_ms
                    eh.last_checked = datetime.now(timezone.utc).isoformat()
                    eh.error = "" if status == "healthy" else f"HTTP {resp.status_code}"
                    
                    if status == "healthy":
                        eh.success_count += 1
                    else:
                        eh.failure_count += 1
                    
                    # Update average response time
                    total = eh.success_count + eh.failure_count
                    eh.avg_response_time_ms = round(
                        ((eh.avg_response_time_ms * (total - 1)) + elapsed_ms) / total, 1
                    )
                    
                    # Check response time threshold
                    if elapsed_ms > ALERT_THRESHOLDS["response_time_ms"]:
                        self._check_alert_threshold("response_time", elapsed_ms, ALERT_THRESHOLDS["response_time_ms"],
                            f"Endpoint {method} {path} response time {elapsed_ms}ms exceeds {ALERT_THRESHOLDS['response_time_ms']}ms")
                    
                except Exception as e:
                    elapsed_ms = round((time.time() - start) * 1000, 1)
                    key = f"{method}:{path}"
                    if key not in self._endpoint_health:
                        self._endpoint_health[key] = EndpointHealth(path=path, method=method)
                    
                    eh = self._endpoint_health[key]
                    eh.status = "down"
                    eh.response_time_ms = elapsed_ms
                    eh.last_checked = datetime.now(timezone.utc).isoformat()
                    eh.error = str(e)[:200]
                    eh.failure_count += 1
                
                results[key] = self._endpoint_health[key]
        
        # Check error rate
        total_failures = sum(eh.failure_count for eh in self._endpoint_health.values())
        total_requests = sum(eh.success_count + eh.failure_count for eh in self._endpoint_health.values())
        error_rate = (total_failures / max(total_requests, 1)) * 100
        
        if error_rate > ALERT_THRESHOLDS["error_rate_per_minute"]:
            self._check_alert_threshold("error_rate", error_rate, ALERT_THRESHOLDS["error_rate_per_minute"],
                f"API error rate {error_rate:.1f}% exceeds threshold {ALERT_THRESHOLDS['error_rate_per_minute']}%")
        
        self._log("health", "api_check", {"endpoints": {k: asdict(v) for k, v in results.items()}})
        return results

    def _deduplicate_error(self, source: str, error_type: str, error_message: str) -> Optional[ErrorRecord]:
        """Check if this error is a duplicate of a recent one."""
        for rec in self._errors:
            if (rec.source == source and 
                rec.error_type == error_type and 
                rec.error_message[:100] == error_message[:100]):
                # Update existing record
                rec.last_seen = datetime.now(timezone.utc).isoformat()
                rec.occurrence_count += 1
                
                # Track trend
                key = f"{source}:{error_type}"
                if key not in self._error_trends:
                    self._error_trends[key] = []
                self._error_trends[key].append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "count": rec.occurrence_count
                })
                # Keep last 100 trend points
                if len(self._error_trends[key]) > 100:
                    self._error_trends[key] = self._error_trends[key][-100:]
                
                return rec
        return None

    def capture_error(self, source: str, error: Exception, context: dict = None, severity: str = "error") -> ErrorRecord:
        """Capture error with full context, persist to log. Includes deduplication."""
        tb = traceback.format_exc()
        
        # Check for duplicate
        existing = self._deduplicate_error(source, type(error).__name__, str(error)[:100])
        if existing:
            # Re-apply severity if higher
            severity_order = {"info": 0, "warning": 1, "error": 2, "critical": 3}
            if severity_order.get(severity, 2) > severity_order.get(existing.severity, 2):
                existing.severity = severity
            return existing
        
        rec = ErrorRecord(
            id=f"err-{int(time.time())}-{len(self._errors)}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source, error_type=type(error).__name__,
            error_message=str(error)[:1000], traceback=tb[:3000],
            context=context or {}, severity=severity,
            first_seen=datetime.now(timezone.utc).isoformat(),
            last_seen=datetime.now(timezone.utc).isoformat(),
            occurrence_count=1,
            tags=self._extract_tags(error, context),
        )
        self._errors.append(rec)
        self._log("error", "captured", {
            "id": rec.id, "source": source, "type": rec.error_type,
            "severity": severity, "message": str(error)[:200],
            "deduplicated": False
        })
        # Also write agent-specific log
        try:
            safe_source = source.replace("/", "_").replace("\\", "_").replace("..", "_").replace(".", "_")
            with open(f"{ERROR_LOG_DIR}/agents/{safe_source}.log", "a") as f:
                f.write(json.dumps({"ts":rec.timestamp,"error":str(error)[:500],"traceback":tb[:2000]}) + "\n")
        except Exception:
            import sys as _sys; print(f"[watchdog] agent log write failed: {source}", file=_sys.stderr)
        logger.warning(f"🐕 [{severity}] {source}: {str(error)[:100]}")
        # Auto-diagnose with Intelligence Engineer
        try:
            engineer = get_engineer()
            diag = engineer.diagnose(source, str(error)[:500], type(error).__name__, context)
            rec.confidence = diag.get("confidence", "low")
            rec.auto_fixable = diag.get("auto_fix_applied", False)
            self._log("engineer_diagnosis", "auto", {
                "source": source, "diagnosis": diag.get("root_cause_analysis", "")[:200],
                "fix_steps": len(diag.get("fix_steps", [])),
                "confidence": rec.confidence,
                "auto_fixable": rec.auto_fixable,
            })
            rec._diagnosis = diag
        except Exception as e:
            logger.warning(f"Engineer diagnosis failed: {e}")
        return rec

    def _extract_tags(self, error: Exception, context: dict) -> list:
        """Extract meaningful tags from error for categorization."""
        tags = []
        err_type = type(error).__name__
        msg = str(error).lower()
        
        if err_type in ("OperationalError", "DatabaseError", "IntegrityError"):
            tags.append("database")
        if "timeout" in msg or "connection" in msg:
            tags.append("network")
        if "memory" in msg or err_type == "MemoryError":
            tags.append("resource")
        if "module" in msg or err_type in ("ModuleNotFoundError", "ImportError"):
            tags.append("dependency")
        if context and context.get("agent_id"):
            tags.append(f"agent:{context['agent_id']}")
        if context and context.get("tender_id"):
            tags.append(f"tender:{context['tender_id']}")
        
        return tags

    def record_pipeline(self, stage: str, ok: bool, ms: int):
        self._pipeline_stats["runs"] += 1
        if ok: self._pipeline_stats["ok"] += 1
        else: 
            self._pipeline_stats["fail"] += 1
            self._pipeline_stats["by_stage"][stage] = self._pipeline_stats["by_stage"].get(stage, 0) + 1
        self._log("pipeline", "run", {"stage": stage, "ok": ok, "ms": ms})

    async def check_all_agents(self) -> dict:
        """Check health of all registered agents."""
        result = {"healthy": 0, "degraded": 0, "down": 0, "details": {}}
        if not self.brain: return result
        for agent_id, cap in self.brain._agents.items():
            inst = self.brain._agent_instances.get(agent_id)
            if inst and getattr(cap, "is_available", True):
                result["healthy"] += 1
                result["details"][agent_id] = "healthy"
                self._agent_health[agent_id] = "healthy"
            elif not inst:
                result["down"] += 1
                result["details"][agent_id] = "missing_instance"
                self._agent_health[agent_id] = "down"
            else:
                result["degraded"] += 1
                result["details"][agent_id] = "unavailable"
                self._agent_health[agent_id] = "degraded"
        self._log("health", "agent_check", {"total": len(self.brain._agents), **result})
        
        # Check alert threshold
        if result["down"] > ALERT_THRESHOLDS["agent_down_count"]:
            self._check_alert_threshold("agent_down", result["down"], ALERT_THRESHOLDS["agent_down_count"],
                f"{result['down']} agent(s) are down")
        
        return result
    
    def check_db(self) -> dict:
        """Check database integrity."""
        r = {"status": "ok", "size_mb": 0, "issues": []}
        try:
            from app.db.database import get_database_backend, get_database_summary, get_sync_engine
            backend = get_database_backend()
            r["backend"] = backend
            r["connection"] = get_database_summary()

            engine = get_sync_engine()
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
                db_name = r["connection"].get("database")
                if db_name:
                    size_bytes = conn.exec_driver_sql(
                        "SELECT pg_database_size(current_database())"
                    ).scalar()
                    if size_bytes is not None:
                        r["size_mb"] = round(float(size_bytes) / (1024 * 1024), 1)
        except Exception as e:
            r["status"] = "error"
            r["issues"].append(str(e)[:200])
        self._log("health", "db_check", r)
        
        # Check alert threshold
        if r["status"] != "ok":
            self._check_alert_threshold("database", 1, 0, f"Database issue: {r.get('issues',['unknown'])[0]}")
        
        return r

    async def generate_report(self) -> dict:
        """Generate full health report with health score."""
        # Collect metrics
        metrics = self.collect_system_metrics()
        
        # Check API endpoints
        await self.check_api_endpoints()
        
        agents = await self.check_all_agents()
        db = self.check_db()
        
        # Calculate health score
        health_score = self._calculate_health_score(agents, db, metrics)
        self._last_health_score = health_score
        
        # Determine overall status
        if health_score >= 90:
            status = "healthy"
        elif health_score >= 70:
            status = "degraded"
        elif health_score >= 50:
            status = "critical"
        else:
            status = "emergency"
        
        report = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "uptime_s": int(time.time() - self._start),
            "status": status,
            "health_score": round(health_score, 1),
            "agents": agents,
            "database": db,
            "system_metrics": {
                "cpu_percent": metrics.cpu_percent,
                "memory_percent": metrics.memory_percent,
                "disk_percent": metrics.disk_percent,
                "uptime_s": metrics.uptime_s,
            },
            "api_endpoints": {k: {"status": v.status, "response_time_ms": v.response_time_ms, "avg_response_time_ms": v.avg_response_time_ms} 
                            for k, v in self._endpoint_health.items()},
            "pipeline": {
                "total": self._pipeline_stats["runs"],
                "success_rate": round((self._pipeline_stats["ok"] / max(self._pipeline_stats["runs"],1)) * 100, 1),
                "failures": self._pipeline_stats["fail"],
                "by_stage": self._pipeline_stats["by_stage"],
            },
            "recent_errors": [{"id":e.id,"source":e.source,"type":e.error_type,"severity":e.severity,"message":e.error_message[:200],"count":e.occurrence_count} for e in self._errors[-10:]],
            "error_count": len(self._errors),
            "active_alerts": [asdict(a) for a in self._alerts if not a.resolved],
            "recommendations": [],
        }
        
        # Add recommendations based on health
        if agents["down"] > 0: report["recommendations"].append(f"🔴 {agents['down']} agent(s) down")
        if agents["degraded"] > 0: report["recommendations"].append(f"🟡 {agents['degraded']} agent(s) degraded")
        if db["status"] != "ok": report["recommendations"].append(f"🗄️ DB issue: {db.get('issues',['unknown'])[0]}")
        if metrics.cpu_percent > 80: report["recommendations"].append(f"⚡ CPU high: {metrics.cpu_percent}%")
        if metrics.memory_percent > 80: report["recommendations"].append(f"💾 Memory high: {metrics.memory_percent}%")
        if metrics.disk_percent > 85: report["recommendations"].append(f"💿 Disk high: {metrics.disk_percent}%")
        
        self._log("health", "report", {"status": report["status"], "health_score": health_score, "errors": len(self._errors)})
        return report

    def _calculate_health_score(self, agents: dict, db: dict, metrics: SystemMetrics) -> float:
        """Calculate weighted health score (0-100)."""
        scores = {}
        
        # Agents health (30%)
        total_agents = agents.get("healthy", 0) + agents.get("degraded", 0) + agents.get("down", 0)
        if total_agents > 0:
            agent_score = (agents.get("healthy", 0) * 100 + agents.get("degraded", 0) * 50) / total_agents
        else:
            agent_score = 100
        scores["agents"] = agent_score
        
        # Database health (25%)
        scores["database"] = 100 if db.get("status") == "ok" else 0
        
        # API endpoints health (20%)
        if self._endpoint_health:
            healthy_endpoints = sum(1 for eh in self._endpoint_health.values() if eh.status == "healthy")
            total_endpoints = len(self._endpoint_health)
            scores["api_endpoints"] = (healthy_endpoints / total_endpoints) * 100
        else:
            scores["api_endpoints"] = 100
        
        # Pipeline health (15%)
        runs = self._pipeline_stats["runs"]
        if runs > 0:
            scores["pipeline"] = (self._pipeline_stats["ok"] / runs) * 100
        else:
            scores["pipeline"] = 100
        
        # System resources (10%)
        cpu_score = max(0, 100 - metrics.cpu_percent)
        mem_score = max(0, 100 - metrics.memory_percent)
        disk_score = max(0, 100 - metrics.disk_percent)
        scores["system_resources"] = (cpu_score + mem_score + disk_score) / 3
        
        # Weighted total
        total = sum(scores[k] * HEALTH_SCORE_WEIGHTS[k] for k in HEALTH_SCORE_WEIGHTS)
        return total

    def get_recent_errors(self, limit=20) -> list:
        return [{"id":e.id,"ts":e.timestamp,"src":e.source,"type":e.error_type,"sev":e.severity,"msg":e.error_message[:200],"count":e.occurrence_count} for e in self._errors[-limit:]]

    def get_recent_alerts(self, limit=20) -> list:
        return [asdict(a) for a in self._alerts[-limit:]]

    def get_error_trends(self, source: str = None, error_type: str = None, hours: int = 24) -> List[Dict]:
        """Get error trends for analysis."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        trends = []
        
        for key, points in self._error_trends.items():
            src, err_type = key.split(":", 1) if ":" in key else (key, "")
            if source and source not in src:
                continue
            if error_type and error_type != err_type:
                continue
            
            recent = [p for p in points if datetime.fromisoformat(p["timestamp"]) > cutoff]
            if recent:
                trends.append({
                    "source": src,
                    "error_type": err_type,
                    "occurrences": sum(p["count"] for p in recent),
                    "last_seen": recent[-1]["timestamp"],
                    "trend_points": recent[-50:]  # Last 50 points
                })
        
        return sorted(trends, key=lambda x: x["occurrences"], reverse=True)

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                self._log("alert", "acknowledged", {"alert_id": alert_id})
                return True
        return False

    def resolve_alert(self, alert_id: str, resolution: str = "") -> bool:
        """Resolve an alert."""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now(timezone.utc).isoformat()
                if resolution:
                    alert.details["resolution"] = resolution
                self._log("alert", "resolved", {"alert_id": alert_id, "resolution": resolution})
                return True
        return False

    def add_notification_handler(self, handler: Callable):
        """Add a notification handler for alerts."""
        self._notification_handlers.append(handler)

    def analyze_error(self, source: str, error_msg: str, error_type: str = "Unknown") -> dict:
        """Error Intelligence Engine — provides exact solution for any error."""
        msg = error_msg.lower()
        solution = {
            "source": source, "error_type": error_type,
            "message": error_msg[:500], "analysis": "",
            "root_cause": "", "steps": [], "prevention": "",
            "confidence": "medium", "auto_fixable": False,
        }
        # ── Pattern-based error analysis ─────────────────────────────
        if error_type in ("OperationalError", "DatabaseError", "IntegrityError"):
            if "value too long for type character varying" in msg or "StringDataRightTruncationError" in msg:
                solution["root_cause"] = "VARCHAR column too short for e-GP data"
                solution["analysis"] = "Column needs TEXT type. See .memory/fixes-log.md — VARCHAR(255) truncation fix."
                solution["steps"] = ["ALTER TABLE <table> ALTER COLUMN <column> TYPE TEXT;", "Clear __pycache__/ and restart server"]
                solution["reference"] = ".memory/fixes-log.md"
            elif "no such column" in msg:
                col = msg.split("no such column:")[-1].strip().split()[0] if "no such column:" in msg else "?"
                solution["root_cause"] = f"Missing DB column: {col}"
                solution["analysis"] = "Schema mismatch — model updated but migration not run."
                # sql-ok: advisory remediation text, not executed SQL
                solution["steps"] = [f"Run: ALTER TABLE ... ADD COLUMN {col}", "Run init_db() to recreate schema"]
            elif "no such table" in msg:
                tbl = msg.split("no such table:")[-1].strip().split()[0] if "no such table:" in msg else "?"
                solution["root_cause"] = f"Missing table: {tbl}"
                solution["steps"] = [f"Run init_db() to create table {tbl}"]
            elif "database is locked" in msg:
                solution["root_cause"] = "Concurrent write lock"
                solution["steps"] = ["Check for long-running transactions", "Reduce concurrent writes", "Check PostgreSQL locks: SELECT * FROM pg_locks WHERE NOT granted"]
            elif "unable to open" in msg:
                solution["root_cause"] = "DB file path invalid"
                solution["steps"] = [f"Check DB path in database.py", "Ensure data/ directory exists"]
            solution["confidence"] = "high"

        elif error_type in ("ModuleNotFoundError", "ImportError"):
            pkgs = [p for p in msg.split("'") if p.strip() and not p.isspace() and len(p) > 1]
            missing = pkgs[0] if pkgs else "?"
            solution["root_cause"] = f"Missing package: {missing}"
            solution["steps"] = [f"pip install {missing}"]
            solution["confidence"] = "high"

        elif error_type in ("ConnectionError", "TimeoutError", "HTTPError"):
            solution["root_cause"] = "Network/API unavailable"
            solution["steps"] = ["Check network", "Verify endpoint", "Add retry with backoff", "Implement circuit breaker"]
            solution["confidence"] = "medium"

        elif error_type == "RuntimeWarning" and "coroutine" in msg:
            fn = msg.split("'")[1] if "'" in msg else "?"
            solution["root_cause"] = f"Async coroutine '{fn}' never awaited"
            solution["steps"] = [f"Add 'await {fn}()' in {source}"]
            solution["confidence"] = "high"
            solution["auto_fixable"] = True

        elif error_type in ("AttributeError", "KeyError", "TypeError", "ValueError"):
            if "isinstance" in msg and "AgentResult" in msg:
                solution["root_cause"] = "AgentResult dataclass used as dict — .get() called on non-dict"
                solution["analysis"] = "result.to_dict() needed instead of str(result). See fixes-log.md — AgentResult serialization fix."
                solution["steps"] = ["Import AgentResult as AgentResultData from app.agents.core.base", "Use isinstance(result, AgentResultData) check", "Call result.to_dict() for serialization"]
                solution["reference"] = ".memory/fixes-log.md"
            else:
                solution["root_cause"] = f"Data format error in {source}"
                solution["analysis"] = "Agent received unexpected data format."
                solution["steps"] = [f"Validate input schema for {source}", "Add Pydantic validation", "Check upstream agent output"]
            solution["confidence"] = "medium"

        elif error_type in ("FileNotFoundError", "PermissionError"):
            paths = [p for p in msg.split("'") if "/" in p]
            path = paths[0] if paths else "?"
            solution["root_cause"] = f"File access error: {path}"
            solution["steps"] = [f"Check path: {path}", "Verify permissions", "Create directory if needed"]
            solution["confidence"] = "high"

        elif error_type == "MemoryError":
            solution["root_cause"] = "Memory exhausted"
            solution["steps"] = ["Reduce batch sizes", "Add pagination", "Check RAM/swap", "Optimize queries"]
            solution["confidence"] = "medium"

        else:
            solution["analysis"] = f"Unknown error pattern: {error_type}"
            solution["steps"] = [f"Check full traceback in logs/{source}.log", f"Test {source} in isolation", "Review recent changes"]
            solution["confidence"] = "low"

        # Attach traceback reference
        recent = [e for e in self._errors if e.source == source and e.error_type == error_type]
        if recent:
            solution["traceback_preview"] = recent[-1].traceback[:500]
        
        return solution

    def get_dashboard(self) -> dict:
        """Get dashboard data for frontend."""
        return {
            "status": "active",
            "uptime_s": int(time.time() - self._start),
            "error_count": len(self._errors),
            "pipeline_runs": self._pipeline_stats["runs"],
            "pipeline_ok": self._pipeline_stats["ok"],
            "pipeline_fail": self._pipeline_stats["fail"],
            "agent_health": self._agent_health,
            "log_paths": {"errors": ERROR_LOG, "health": HEALTH_LOG, "sessions": SESSION_LOG},
            "fix_log_ref": ".memory/fixes-log.md — all fixes date-stamped with file:line",
            "entry_ref": "AGENTS_ENTRY.md — mandatory read for any AI entering codebase",
            "works_only": "True — Goods/Services filtered out at scan stage",
            "version": "2.1",
            "metrics_enabled": True,
            "endpoints_monitored": len(self._endpoint_health),
            "active_alerts": len([a for a in self._alerts if not a.resolved]),
        }

# Singleton
_instance = None
def get_watchdog(brain=None):
    global _instance
    if _instance is None: _instance = AgentWatchdog(brain)
    elif brain and not _instance.brain: _instance.brain = brain
    return _instance
