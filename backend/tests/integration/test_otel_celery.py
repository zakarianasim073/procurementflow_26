"""W-006: Celery tasks record duration metrics and propagate request_id (trace correlation)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.telemetry import get_metrics


def test_request_id_extracted_and_propagated():
    """request_id from the API context is threaded into the Celery task (criterion 4/6)."""
    from app.workers.tasks.agent_tasks import _extract_request_id

    # Explicit request_id forwarded unchanged
    ctx = {"request_id": "api-req-999"}
    assert _extract_request_id(ctx) == "api-req-999"
    assert ctx["request_id"] == "api-req-999"

    # Missing request_id is generated and written back into context
    ctx2: dict = {}
    rid = _extract_request_id(ctx2)
    assert rid and ctx2.get("request_id") == rid


def test_celery_task_duration_recorded_and_exposed():
    """A completed Celery task records duration + status to Prometheus (criterion 4)."""
    from app.workers.tasks.agent_tasks import _record_task_metrics

    with TestClient(app) as client:
        m = get_metrics()
        assert m is not None
        _record_task_metrics("run_agent_task", "default", "success", 0.75, "req-xyz")
        _record_task_metrics("run_pipeline_task", "low", "failed", 1.2, "req-abc")
        resp = client.get("/metrics")
    text = resp.text
    assert "procureflow_celery_task_duration_seconds" in text
    assert "procureflow_celery_tasks_total" in text


def test_celery_queue_depth_metric_exposed():
    """Queue depth gauge is exposed on /metrics (drives the backlog alert)."""
    with TestClient(app) as client:
        m = get_metrics()
        assert m is not None
        m.set_celery_queue_depth("default", 42)
        m.set_celery_workers_alive(4)
        resp = client.get("/metrics")
    text = resp.text
    assert "procureflow_celery_queue_depth" in text
    assert "procureflow_celery_workers_alive" in text
