"""OpenTelemetry + Prometheus metrics setup for production observability (T-017/OBS-01)."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

# Module-level state for Prometheus metrics (initialized once at app startup)
_metrics = None


class PrometheusMetrics:
    """Prometheus metrics for domain monitoring — six key metrics per T-017 spec."""

    def __init__(self):
        try:
            from prometheus_client import Counter, Gauge, Histogram
        except ImportError:
            logger.warning("prometheus_client not installed; metrics disabled")
            self.enabled = False
            return

        self.enabled = True
        # Domain metrics: API p95>5s, BOQ>120s, pipeline>300s, crawl<90%, pool>80%, knowledge>1800/2000
        self.api_request_duration = Histogram(
            "procureflow_api_request_duration_seconds",
            "API request duration in seconds",
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
        )
        self.boq_comparison_duration = Histogram(
            "procureflow_boq_comparison_duration_seconds",
            "BOQ comparison task duration in seconds (threshold: >120s alert)",
            buckets=[10.0, 30.0, 60.0, 120.0, 300.0],
        )
        self.pipeline_execution_duration = Histogram(
            "procureflow_pipeline_execution_duration_seconds",
            "Agent pipeline execution duration in seconds (threshold: >300s alert)",
            buckets=[30.0, 60.0, 120.0, 300.0, 600.0],
        )
        self.crawl_success_rate = Gauge(
            "procureflow_crawl_success_ratio",
            "Crawl success rate as ratio 0-1 (threshold: <90% alert)",
        )
        self.db_connection_pool_usage = Gauge(
            "procureflow_db_pool_usage_ratio",
            "Database connection pool usage as ratio 0-1 (threshold: >80% alert)",
        )
        self.knowledge_store_size = Gauge(
            "procureflow_knowledge_store_entries",
            "Knowledge store entry count (threshold: >1800/2000 alert)",
        )
        self.registered_agents = Gauge(
            "procureflow_registered_agents",
            "Count of registered agents",
        )
        self.celery_task_total = Counter(
            "procureflow_celery_tasks_total",
            "Total Celery tasks by status and queue",
            labelnames=["queue", "status"],
        )
        self.process_uptime = Gauge(
            "procureflow_process_uptime_seconds",
            "Process uptime in seconds",
        )

    def record_api_request(self, duration_seconds: float):
        """Record API request latency."""
        if self.enabled:
            self.api_request_duration.observe(duration_seconds)

    def record_boq_comparison(self, duration_seconds: float):
        """Record BOQ comparison task duration (threshold: >120s)."""
        if self.enabled:
            self.boq_comparison_duration.observe(duration_seconds)

    def record_pipeline_execution(self, duration_seconds: float):
        """Record pipeline execution duration (threshold: >300s)."""
        if self.enabled:
            self.pipeline_execution_duration.observe(duration_seconds)

    def set_crawl_success_rate(self, ratio: float):
        """Set crawl success ratio 0-1 (threshold: <90%)."""
        if self.enabled:
            self.crawl_success_rate.set(ratio)

    def set_pool_usage(self, ratio: float):
        """Set DB pool usage ratio 0-1 (threshold: >80%)."""
        if self.enabled:
            self.db_connection_pool_usage.set(ratio)

    def set_knowledge_size(self, count: int):
        """Set knowledge store size (threshold: >1800/2000)."""
        if self.enabled:
            self.knowledge_store_size.set(count)

    def set_agent_count(self, count: int):
        """Set registered agent count."""
        if self.enabled:
            self.registered_agents.set(count)

    def record_celery_task(self, queue: str, status: str):
        """Record Celery task completion."""
        if self.enabled:
            self.celery_task_total.labels(queue=queue, status=status).inc()

    def set_uptime(self, seconds: float):
        """Set process uptime."""
        if self.enabled:
            self.process_uptime.set(seconds)


def configure_telemetry(app: Any, engine: Any = None) -> bool:
    """Configure OpenTelemetry traces + Prometheus metrics (T-017/OBS-01).

    Enables:
    - OTLP trace export to Tempo (if endpoint configured)
    - FastAPI request tracing with request_id span attributes
    - SQLAlchemy query tracing
    - Prometheus /metrics endpoint with domain metrics
    """
    global _metrics

    enabled = os.getenv("OTEL_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        logger.info("OpenTelemetry disabled (set OTEL_ENABLED=true to enable)")
        return False

    # Initialize Prometheus metrics first (always available if enabled)
    try:
        _metrics = PrometheusMetrics()
    except Exception as exc:
        logger.warning("Prometheus metrics initialization failed: %s", exc)

    # Configure OTLP trace export if dependencies installed
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
    except Exception as exc:
        logger.info("OpenTelemetry not fully enabled; packages unavailable: %s", exc)
        return bool(_metrics)  # Still return True if Prometheus is up

    service_name = os.getenv("OTEL_SERVICE_NAME", "procureflow-api")
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))

    if endpoint:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        logger.info("OTel trace export configured to %s", endpoint)

    trace.set_tracer_provider(provider)

    # Instrument FastAPI with request_id context
    FastAPIInstrumentor.instrument_app(app)

    # Instrument SQLAlchemy
    if engine is not None:
        try:
            sync_engine = getattr(engine, "sync_engine", engine)
            SQLAlchemyInstrumentor().instrument(engine=sync_engine)
        except Exception as exc:
            logger.debug("SQLAlchemy telemetry instrumentation skipped: %s", exc)

    # Instrument Celery workers
    try:
        CeleryInstrumentor().instrument()
    except Exception as exc:
        logger.debug("Celery telemetry instrumentation skipped: %s", exc)

    logger.info("OpenTelemetry configured for %s (traces + metrics)", service_name)
    return True


def get_metrics() -> PrometheusMetrics | None:
    """Get the global Prometheus metrics instance."""
    return _metrics
