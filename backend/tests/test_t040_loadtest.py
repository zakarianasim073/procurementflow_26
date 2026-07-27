"""T-040: Load test suite unit tests (no live server required)."""
from __future__ import annotations

from loadtest.runner import (
    SCENARIOS,
    SLO_ERROR_RATE,
    SLO_P95_MS,
    Scenario,
    StepResult,
    _weighted_cycle,
    render_markdown,
)


class TestStepResult:

    def test_percentiles(self):
        r = StepResult(concurrency=10, duration_s=10)
        r.latencies_ms = [float(i) for i in range(1, 101)]  # 1..100
        r.requests = 100
        assert r.pct(50) == 50.0
        assert r.pct(95) == 95.0
        assert r.pct(99) == 99.0

    def test_empty_percentile_is_zero(self):
        r = StepResult(concurrency=1, duration_s=1)
        assert r.pct(95) == 0.0

    def test_error_rate(self):
        r = StepResult(concurrency=1, duration_s=1)
        r.requests = 200
        r.errors = 10
        assert r.error_rate == 0.05

    def test_slo_breach_on_latency(self):
        r = StepResult(concurrency=1, duration_s=1)
        r.requests = 100
        r.latencies_ms = [SLO_P95_MS + 100] * 100
        assert r.slo_breached is True

    def test_slo_breach_on_errors(self):
        r = StepResult(concurrency=1, duration_s=1)
        r.requests = 100
        r.errors = int(100 * (SLO_ERROR_RATE + 0.01)) + 1
        r.latencies_ms = [10.0] * 100
        assert r.slo_breached is True

    def test_slo_ok(self):
        r = StepResult(concurrency=1, duration_s=1)
        r.requests = 100
        r.latencies_ms = [100.0] * 100
        assert r.slo_breached is False


class TestWeightedCycle:

    def test_weights_respected(self):
        bag = _weighted_cycle([
            Scenario("a", "GET", "/a", weight=3),
            Scenario("b", "GET", "/b", weight=1),
        ])
        assert len(bag) == 4
        assert sum(1 for s in bag if s.name == "a") == 3

    def test_default_scenarios_nonempty(self):
        assert len(SCENARIOS) >= 4
        assert len(_weighted_cycle(SCENARIOS)) >= len(SCENARIOS)


class TestReportRendering:

    def _fake_report(self, breached: bool):
        return {
            "generated_at": "2026-07-20T00:00:00+00:00",
            "base_url": "http://localhost:8000",
            "slo": {"p95_ms": SLO_P95_MS, "error_rate": SLO_ERROR_RATE},
            "step_duration_s": 15.0,
            "authenticated": True,
            "steps": [{
                "concurrency": 10, "requests": 500, "rps": 33.3,
                "errors": 0, "error_rate_pct": 0.0,
                "p50_ms": 120.0, "p95_ms": 300.0, "p99_ms": 450.0, "max_ms": 500.0,
                "slo_breached": breached,
                "per_scenario": {"health": {"requests": 100, "errors": 0, "avg_ms": 5.0}},
            }],
            "breaking_point_concurrency": 10 if breached else None,
            "max_sustained_concurrency": None if breached else 10,
        }

    def test_render_with_breaking_point(self):
        md = render_markdown(self._fake_report(True))
        assert "SLO breached at 10" in md
        assert "| 10 | 500 |" in md

    def test_render_without_breaking_point(self):
        md = render_markdown(self._fake_report(False))
        assert "No breaking point found" in md
        assert "health" in md
