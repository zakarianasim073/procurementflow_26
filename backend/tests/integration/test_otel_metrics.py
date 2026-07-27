"""W-006: Prometheus /metrics endpoint exposes all observability series."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.telemetry import get_metrics


def _seed_samples(m):
    """Generate at least one observation per custom metric family."""
    m.record_api_request(0.12, method="GET", path="/api/health", status="200")
    m.record_api_request(0.05, method="POST", path="/api/boq/compare", status="202")
    m.record_agent_execution(0.3, agent_id="agent-001", status="success")
    m.record_agent_execution(0.1, agent_id="agent-002", status="failed")
    m.record_celery_task_duration(0.6, "run_agent_task", "default", "success")
    m.record_celery_task_duration(0.2, "run_pipeline_task", "low", "failed")
    m.record_sor_match(0.008, agency="BWDB")
    m.record_sor_match(0.004, agency="PWD")
    m.set_db_up(True)
    m.set_redis_up(True)
    m.set_minio_up(False)
    m.set_celery_workers_alive(3)
    m.set_celery_queue_depth("high", 2)
    m.set_celery_queue_depth("default", 7)
    m.set_celery_queue_depth("low", 1)
    m.set_agent_count(49)


def test_metrics_endpoint_exposes_w006_metrics():
    with TestClient(app) as client:
        m = get_metrics()
        assert m is not None, "telemetry metrics not initialized"
        _seed_samples(m)
        resp = client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text

    expected = [
        "procureflow_api_request_duration_seconds",
        "procureflow_api_requests_total",
        "procureflow_agent_execution_duration_seconds",
        "procureflow_agent_executions_total",
        "procureflow_celery_task_duration_seconds",
        "procureflow_celery_tasks_total",
        "procureflow_sor_match_duration_seconds",
        "procureflow_knowledge_store_entries",
        "procureflow_health_db_up",
        "procureflow_health_redis_up",
        "procureflow_health_minio_up",
        "procureflow_celery_workers_alive",
        "procureflow_celery_queue_depth",
        "procureflow_api_routers_loaded",
        "procureflow_agent_runtime_ready",
    ]
    for name in expected:
        assert name in text, f"expected metric not exposed: {name}"


def test_metrics_endpoint_is_prometheus_format():
    with TestClient(app) as client:
        resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "# TYPE " in resp.text
    assert "# HELP " in resp.text
    assert "text/plain" in resp.headers.get("content-type", "")


def test_api_request_records_labeled_latency():
    """A real API request records a labeled observation in the histogram."""
    with TestClient(app) as client:
        client.get("/api/health")
        resp = client.get("/metrics")
    text = resp.text
    # The histogram bucket + count series must be present after a request
    assert "procureflow_api_request_duration_seconds_bucket" in text
    assert "procureflow_api_requests_total" in text
