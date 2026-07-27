"""
Procurement Flow Specialist BD — Celery Background Worker Configuration
Offloads heavy agent processing (eGP scraping, PDF parsing, 27-agent pipeline)
to background workers so FastAPI stays responsive.

Includes Celery Beat schedule for automated tasks:
  - Tender Radar: every hour
  - Award Intelligence scraping: daily at 2 AM
  - Corrigendum Watchdog: every 6 hours
  - Tender cleanup: weekly
"""

import os
from celery import Celery
from celery.schedules import crontab
from kombu import Queue

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ── Queue priority separation (WRK-01 / T-012) ──────────────────────────────
# Three named queues. Time-sensitive work (alerts, radar) rides `high` so a
# flood of low-value report jobs can never delay it. Workers consume exactly
# one queue each (see docker-compose.yml worker-high/default/low services).
QUEUE_HIGH = "high"
QUEUE_DEFAULT = "default"
QUEUE_LOW = "low"

QUEUES = [
    Queue(QUEUE_HIGH, routing_key=QUEUE_HIGH),
    Queue(QUEUE_DEFAULT, routing_key=QUEUE_DEFAULT),
    Queue(QUEUE_LOW, routing_key=QUEUE_LOW),
]

# Per-queue ceilings (ADR-010 async budget). `low` gets the longest budget
# because report/ML batch jobs are the most expensive but least urgent.
_LIMITS = {
    QUEUE_HIGH: (15 * 60, 20 * 60),     # soft, hard
    QUEUE_DEFAULT: (25 * 60, 30 * 60),
    QUEUE_LOW: (45 * 60, 50 * 60),
}


def _route(queue: str, module_glob: str = None, task_name: str = None) -> dict:
    # Only route the queue here. Putting soft_time_limit/time_limit in task_routes
    # collides with Celery's protocol-v2 message builder ("as_task_v2() got multiple
    # values for argument 'soft_time_limit'") and breaks .delay()/apply_async. The
    # global task_soft_time_limit / task_time_limit (in conf.update below) apply as
    # the ceiling for every task; per-queue ceilings live in task_annotations.
    return {"queue": queue}


# Explicit routes cover every known task. Auto-named tasks (no `name=` arg)
# are routed by module glob so a newly added task in a module inherits the
# module's queue instead of silently falling back to `default`.
TASK_ROUTES = {
    # HIGH — time-sensitive: tender alerts, radar scan (pipeline_discovery)
    "pipeline_discovery": _route(QUEUE_HIGH),
    "app.workers.tasks.notification_tasks.*": _route(QUEUE_HIGH),

    # DEFAULT — interactive/heavy data work: BOQ, agents, documents, pipeline
    "run_agent_task": _route(QUEUE_DEFAULT),
    "run_pipeline_task": _route(QUEUE_DEFAULT),
    "enforce_data_retention": _route(QUEUE_DEFAULT),
    "process_tender_bundle_task": _route(QUEUE_DEFAULT),
    "run_admin_maintenance_task": _route(QUEUE_DEFAULT),
    "run_crawl_import_task": _route(QUEUE_DEFAULT),
    "process_boq_comparison_task": _route(QUEUE_DEFAULT),
    "generate_export_task": _route(QUEUE_DEFAULT),
    "app.workers.tasks.boq_tasks.*": _route(QUEUE_DEFAULT),
    "app.workers.tasks.document_tasks.*": _route(QUEUE_DEFAULT),
    "pipeline_intelligence": _route(QUEUE_DEFAULT),
    "pipeline_evaluation": _route(QUEUE_DEFAULT),
    "pipeline_pricing": _route(QUEUE_DEFAULT),
    "pipeline_competitor": _route(QUEUE_DEFAULT),
    "pipeline_decision": _route(QUEUE_DEFAULT),
    "pipeline_reporting": _route(QUEUE_DEFAULT),

    # DEFAULT — package-no repair (T-029): short-running, data-integrity
    "repair_package_nos": _route(QUEUE_DEFAULT),
    # LOW — reports / batch generation (least urgent)
    "app.workers.tasks.report_tasks.*": _route(QUEUE_LOW),
    # LOW — ML model (re)training is heavy but never urgent (W-008 / ADR-015)
    "reconcile_ppr_opening_labels": _route(QUEUE_LOW),
    "train_ppr_models": _route(QUEUE_LOW),
    "app.workers.tasks.ml_tasks.*": _route(QUEUE_LOW),
    "idle_shortlist_intelligence": _route(QUEUE_LOW),
    "app.workers.tasks.idle_intelligence_tasks.*": _route(QUEUE_LOW),
}

celery_app = Celery(
    "procureflow",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.workers.tasks.agent_tasks",
        "app.workers.tasks.boq_tasks",
        "app.workers.tasks.pipeline_tasks",
        "app.workers.tasks.notification_tasks",
        "app.workers.tasks.document_tasks",
        "app.workers.tasks.report_tasks",
        "app.workers.tasks.shortlist_tasks",
        "app.workers.tasks.event_tasks",
        "app.workers.tasks.ml_tasks",  # W-008: PPR win-probability model training
        "app.workers.quota_tasks",  # T-036: quota reset tasks
        "app.workers.warehouse_tasks",  # T-020: analytics warehouse ETL tasks
        "app.workers.tasks.repair_tasks",  # T-029: package-no repair pipeline
        "app.workers.tasks.maintenance_tasks",
        "app.workers.tasks.crawl_tasks",
        "app.workers.tasks.idle_intelligence_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Dhaka",
    enable_utc=True,
    task_track_started=True,
    # Queues + routing (WRK-01 / T-012)
    task_default_queue=QUEUE_DEFAULT,
    task_queues=QUEUES,
    task_routes=TASK_ROUTES,
    task_create_missing_queues=True,
    # Per-task ceilings by queue (moved here from task_routes, which broke .delay()).
    task_annotations={
        # HIGH queue (15m soft / 20m hard)
        "pipeline_discovery": {"soft_time_limit": _LIMITS[QUEUE_HIGH][0], "time_limit": _LIMITS[QUEUE_HIGH][1]},
        "app.workers.tasks.notification_tasks.*": {"soft_time_limit": _LIMITS[QUEUE_HIGH][0], "time_limit": _LIMITS[QUEUE_HIGH][1]},
        # DEFAULT queue (25m soft / 30m hard) — agents, BOQ, documents, pipeline
        "run_agent_task": {"soft_time_limit": _LIMITS[QUEUE_DEFAULT][0], "time_limit": _LIMITS[QUEUE_DEFAULT][1]},
        "run_pipeline_task": {"soft_time_limit": _LIMITS[QUEUE_DEFAULT][0], "time_limit": _LIMITS[QUEUE_DEFAULT][1]},
        "process_tender_bundle_task": {"soft_time_limit": _LIMITS[QUEUE_DEFAULT][0], "time_limit": _LIMITS[QUEUE_DEFAULT][1]},
        "process_boq_comparison_task": {"soft_time_limit": _LIMITS[QUEUE_DEFAULT][0], "time_limit": _LIMITS[QUEUE_DEFAULT][1]},
        # LOW queue (45m soft / 50m hard) — reports / batch generation
        "app.workers.tasks.report_tasks.*": {"soft_time_limit": _LIMITS[QUEUE_LOW][0], "time_limit": _LIMITS[QUEUE_LOW][1]},
        # LOW queue (45m soft / 50m hard) — ML model (re)training is heavy but never urgent (W-008)
        "app.workers.tasks.ml_tasks.*": {"soft_time_limit": _LIMITS[QUEUE_LOW][0], "time_limit": _LIMITS[QUEUE_LOW][1]},
        "idle_shortlist_intelligence": {"soft_time_limit": _LIMITS[QUEUE_LOW][0], "time_limit": _LIMITS[QUEUE_LOW][1]},
    },
    # Default ceilings for everything else
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# ── Celery Beat Schedule (Automated Tasks) ────────────────────────────────

celery_app.conf.beat_schedule = {
    # 0. Daily per-firm shortlist via EPDP /v1/tender/shortlist (W-003), 6:00 AM
    "epdp-shortlist-daily": {
        "task": "epdp_daily_shortlist",
        "schedule": crontab(hour=6, minute=0),
    },
    # 0b. EPDP event consumption (X-003) - every 2 minutes, low queue
    "epdp-events-poll": {
        "task": "poll_epdp_events",
        "schedule": crontab(minute="*/2"),
    },
    # 1. Tender Radar — scan every hour for new matching tenders
    "radar-scan-hourly": {
        "task": "pipeline_discovery",
        "schedule": crontab(minute=0),
        "kwargs": {"context": {"mode": "discovery", "source": "celery_beat"}},
    },
    # 2. Award Intelligence — scrape eGP awards nightly at 2:00 AM (build Data Moat)
    "scrape-awards-daily": {
        "task": "run_agent_task",
        "schedule": crontab(hour=2, minute=0),
        "kwargs": {"agent_id": "agent-014-award-intelligence", "context": {"limit": 100}},
    },
    # 3. Corrigendum Watchdog — check for amendments every 6 hours
    "corrigendum-check": {
        "task": "run_agent_task",
        "schedule": crontab(hour="*/6", minute=0),
        "kwargs": {"agent_id": "agent-003-corrigendum-watchdog", "context": {}},
    },
    # 4. Daily Bulk Collection — collect 1000+ tenders every night at 3:00 AM
    "bulk-collection-daily": {
        "task": "run_agent_task",
        "schedule": crontab(hour=3, minute=0),
        "kwargs": {
            "agent_id": "agent-014-award-intelligence",
            "context": {"bulk_mode": True, "target_count": 1000, "run_bwdb_monitor": True},
        },
    },
    # 5. BWDB Monitor Scan — check for high-value tenders every 6 hours
    "bwdb-monitor-scan": {
        "task": "run_agent_task",
        "schedule": crontab(hour="*/6", minute=30),
        "kwargs": {
            "agent_id": "agent-014-award-intelligence",
            "context": {"bulk_mode": False, "limit": 200, "run_bwdb_monitor": True},
        },
    },
    # 6. Data cleanup — purge old temp files weekly on Sunday midnight
    "cleanup-weekly": {
        "task": "run_agent_task",
        "schedule": crontab(hour=0, minute=0, day_of_week=0),
        "kwargs": {"agent_id": "agent-025-knowledge-lake", "context": {"action": "cleanup"}},
    },
    # 7. Data retention — enforce retention policies daily at 4:00 AM
    "retention-daily": {
        "task": "app.workers.tasks.agent_tasks.enforce_data_retention",
        "schedule": crontab(hour=4, minute=0),
    },
    # 8. Monthly quota reset — reset all tenant quotas daily at midnight UTC (T-036)
    "quota-reset-daily": {
        "task": "app.workers.quota_tasks.reset_monthly_quotas",
        "schedule": crontab(hour=0, minute=0),
        "kwargs": {},
    },
    # 9. Rate limit cleanup — clean expired Redis keys weekly Sunday 2am UTC (T-036)
    "ratelimit-cleanup-weekly": {
        "task": "app.workers.quota_tasks.clean_expired_rate_limits",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),
        "kwargs": {},
    },
    # 10. Warehouse fact refresh — hourly (T-020: incremental 24-hour lookback)
    "warehouse-facts-hourly": {
        "task": "app.workers.warehouse_tasks.refresh_warehouse_facts",
        "schedule": crontab(minute=15),  # Every hour at :15 past
        "kwargs": {},
    },
    # 11. Warehouse dimension refresh — daily at 1:00 AM (T-020)
    "warehouse-dimensions-daily": {
        "task": "app.workers.warehouse_tasks.refresh_warehouse_dimensions",
        "schedule": crontab(hour=1, minute=0),
        "kwargs": {},
    },
    # 12. Materialized views refresh — daily at 1:30 AM (T-020)
    "warehouse-views-daily": {
        "task": "app.workers.warehouse_tasks.refresh_materialized_views",
        "schedule": crontab(hour=1, minute=30),
        "kwargs": {},
    },
    # 13. Warehouse health check — every 6 hours (T-020: monitoring/alerting)
    "warehouse-health-check": {
        "task": "app.workers.warehouse_tasks.get_warehouse_health_check",
        "schedule": crontab(minute=0, hour="*/6"),
        "kwargs": {},
    },
    # 14b. Award package-number repair — nightly at 4:30 AM (T-029 / DBT-01).
    # Resolves broken award→tender FK links via normalized_package_no, then
    # triggers a lifecycle rebuild so DNA / competition-intel stays accurate.
    "package-no-repair-daily": {
        "task": "repair_package_nos",
        "schedule": crontab(hour=4, minute=30),
    },
    # 14. Reconcile exact Works opening labels before model training.
    "ppr-opening-label-reconciliation": {
        "task": "reconcile_ppr_opening_labels",
        "schedule": crontab(hour=4, minute=50),
        "kwargs": {},
        "options": {"queue": "low"},
    },
    # 14a. PPR win-probability model (re)training — daily at 5:00 AM (W-008 / ADR-015).
    # Trains one model per agency/zone/regime slice + the global model, all
    # published to the versioned model registry. Routes to the LOW queue.
    "ppr-ml-train-daily": {
        "task": "train_ppr_models",
        "schedule": crontab(hour=5, minute=0),
        "kwargs": {"force": False},
        "options": {"queue": "low"},
    },
    # 15. Precompute analytical intelligence for certified Works shortlist
    # rows. The low queue only runs when higher-priority work is not consuming
    # its dedicated workers; fresh snapshots are skipped for 24 hours.
    "idle-shortlist-intelligence": {
        "task": "idle_shortlist_intelligence",
        "schedule": crontab(minute="*/20"),
        "kwargs": {"limit": 5},
        "options": {"queue": "low"},
    },
}
