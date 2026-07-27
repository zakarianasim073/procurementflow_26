"""
T-012 (WRK-01): Celery queue priority separation.

Proves the acceptance criteria without needing a live broker:
  - Tasks observably land on declared queues (real Celery router used)
  - Dedicated worker pools per queue exist in docker-compose.yml (-Q flags)
The "queue depth retrievable" criterion is covered by the existing
/api/health/celery probe (tests/test_health_probes.py) which already
reports high/default/low depths.
"""
import os
from pathlib import Path

import pytest

# Importing celery_app triggers config load; keep Redis optional.
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.celery_app import celery_app  # noqa: E402

# (expected_queue, [task names])
HIGH = [
    "pipeline_discovery",
    "app.workers.tasks.notification_tasks.send_approval_notification",
    "app.workers.tasks.notification_tasks.send_order_confirmation",
    "app.workers.tasks.notification_tasks.send_vendor_onboarding_email",
]
DEFAULT = [
    "run_agent_task",
    "run_pipeline_task",
    "enforce_data_retention",
    "process_tender_bundle_task",
    "process_boq_comparison_task",
    "generate_export_task",
    "app.workers.tasks.document_tasks.process_document",
    "app.workers.tasks.document_tasks.generate_document_preview",
    "pipeline_intelligence",
    "pipeline_evaluation",
    "pipeline_pricing",
    "pipeline_competitor",
    "pipeline_decision",
    "pipeline_reporting",
]
LOW = [
    "app.workers.tasks.report_tasks.generate_report",
    "app.workers.tasks.report_tasks.generate_spend_analysis",
]


def _queue_for(task_name: str) -> str:
    """Resolve a task to its target queue using Celery's real router."""
    router = celery_app.amqp.router
    route = router.route(celery_app.conf.task_routes, task_name)
    queue = route.get("queue")
    return queue.name if hasattr(queue, "name") else queue


def test_queues_declared():
    names = {q.name for q in celery_app.conf.task_queues}
    assert {"high", "default", "low"} <= names
    assert celery_app.conf.task_default_queue == "default"
    assert celery_app.conf.task_create_missing_queues is True


def test_high_priority_tasks_route_to_high():
    for name in HIGH:
        assert _queue_for(name) == "high", name


def test_default_tasks_route_to_default():
    for name in DEFAULT:
        assert _queue_for(name) == "default", name


def test_low_priority_tasks_route_to_low():
    for name in LOW:
        assert _queue_for(name) == "low", name


def test_per_queue_time_limits():
    router = celery_app.amqp.router
    opts = celery_app.conf.task_routes
    high_soft = router.route(opts, "pipeline_discovery").get("soft_time_limit")
    low_soft = router.route(opts, "app.workers.tasks.report_tasks.generate_report").get("soft_time_limit")
    # low gets a longer budget than high (least urgent, most expensive)
    assert high_soft == 15 * 60
    assert low_soft == 45 * 60
    assert low_soft > high_soft


def test_compose_declares_per_queue_workers():
    compose = Path(__file__).resolve().parents[2] / "docker-compose.yml"
    assert compose.exists(), "docker-compose.yml must exist at repo root"
    import yaml

    with compose.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    services = cfg.get("services", {})
    assert "worker-high" in services
    assert "worker-default" in services
    assert "worker-low" in services
    # The old single shared worker must be gone so nothing defaults to one queue.
    assert "worker" not in services

    def queue_flag(cmd) -> str:
        # command may be a string or list
        parts = cmd if isinstance(cmd, list) else cmd.split()
        for i, token in enumerate(parts):
            if token == "-Q":
                return parts[i + 1] if i + 1 < len(parts) else None
            if token.startswith("-Q") and len(token) > 2:
                return token[2:]  # attached form: -Qhigh
        return None

    assert queue_flag(services["worker-high"]["command"]) == "high"
    assert queue_flag(services["worker-default"]["command"]) == "default"
    assert queue_flag(services["worker-low"]["command"]) == "low"


def test_no_task_falls_through_to_unrouted():
    """Every known task must resolve to one of the three queues (never None)."""
    all_names = HIGH + DEFAULT + LOW
    for name in all_names:
        q = _queue_for(name)
        assert q in {"high", "default", "low"}, f"{name} -> {q}"
