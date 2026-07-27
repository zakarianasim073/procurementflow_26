"""W-006: every API request trace carries request_id/tenant_id/path/duration_ms."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

OTEL_AVAILABLE = True
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
except Exception:  # pragma: no cover
    OTEL_AVAILABLE = False


pytestmark = pytest.mark.skipif(not OTEL_AVAILABLE, reason="opentelemetry SDK not installed")


def test_api_request_creates_trace_with_attributes():
    """Criterion 3: an API request trace carries request_id/tenant_id/path/duration_ms.

    The middleware attributes the active span via trace.get_current_span(), so
    we make our own span current around the request and assert the attributes
    land on it (deterministic, no reliance on global OTel provider state).
    """
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "procureflow-test"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")

    with tracer.start_as_current_span("api-request") as span:
        with TestClient(app) as client:
            client.get(
                "/api/health",
                headers={"x-request-id": "req-w006-123", "x-tenant-id": "tenant-abc"},
            )

    # The middleware wrote correlation attributes onto the active (our) span
    assert span.attributes.get("request_id") == "req-w006-123", "request_id missing"
    assert span.attributes.get("path") == "/api/health", "path missing"
    assert span.attributes.get("tenant_id") == "tenant-abc", "tenant_id missing"
    assert "duration_ms" in span.attributes, "duration_ms missing"

    # And the span was exported through our provider
    spans = exporter.get_finished_spans()
    assert any(s.name == "api-request" for s in spans), "span not exported"
    assert any(s.attributes.get("request_id") == "req-w006-123" for s in spans)


def test_record_span_attributes_helper():
    """record_span_attributes decorates the active span (covers criterion 3).

    Uses a LOCAL (non-global) TracerProvider so the test never mutates the
    process-wide OTel provider — re-calling trace.set_tracer_provider after the
    app is instrumented churns global state and triggers a startup recursion on
    the persistent module-level FastAPI app across repeated TestClient restarts.
    """
    from app.services.telemetry import record_span_attributes

    provider = TracerProvider(resource=Resource.create({"service.name": "procureflow-test"}))
    provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))
    tracer = provider.get_tracer("test")

    with tracer.start_as_current_span("op") as span:
        record_span_attributes("rid-1", tenant_id="t-1", path="/x", duration_ms=12.0)
        assert span.attributes.get("request_id") == "rid-1"
        assert span.attributes.get("tenant_id") == "t-1"
        assert span.attributes.get("path") == "/x"
        assert span.attributes.get("duration_ms") == 12.0

    # __no_tenant__ sentinel is redacted to empty string
    with tracer.start_as_current_span("op2") as span2:
        record_span_attributes("rid-2", tenant_id="__no_tenant__")
        assert span2.attributes.get("tenant_id") == ""
