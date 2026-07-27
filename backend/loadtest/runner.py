"""T-040 (LOAD-01): Load testing suite + breaking-point report.

Self-contained async load generator (httpx, no Locust dependency).

Runs weighted scenarios against a live ProcureFlow backend at stepped
concurrency levels; each step measures throughput, latency percentiles and
error rate. The breaking point is the first step where the SLO is breached
(p95 > SLO_P95_MS or error rate > SLO_ERROR_RATE).

Usage:
    python -m loadtest.runner --base-url http://localhost:8000 \
        --email z.nasim073@gmail.com --password *** \
        --steps 5,10,25,50,100 --duration 15 \
        --report ../docs/LOAD_TEST_REPORT.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

SLO_P95_MS = 2000.0     # ENT-09 acceptance: <2s page loads
SLO_ERROR_RATE = 0.05   # 5%


@dataclass
class Scenario:
    name: str
    method: str
    path: str
    weight: int = 1
    needs_auth: bool = False
    params: Optional[Dict[str, Any]] = None


SCENARIOS: List[Scenario] = [
    Scenario("health", "GET", "/api/health", weight=1),
    Scenario("search_tenders", "GET", "/api/v1/search/tenders", weight=3,
             params={"q": "bridge construction", "limit": 20}, needs_auth=True),
    Scenario("search_contractors", "GET", "/api/v1/search/contractors", weight=2,
             params={"q": "engineering", "limit": 20}, needs_auth=True),
    Scenario("executive_pipeline", "GET", "/api/v1/executive/pipeline", weight=2, needs_auth=True),
    Scenario("executive_agency_spend", "GET", "/api/v1/executive/agency-spend", weight=2,
             params={"years": 5}, needs_auth=True),
    Scenario("executive_heatmap", "GET", "/api/v1/executive/contractor-heatmap", weight=1,
             params={"top_n": 15}, needs_auth=True),
]


@dataclass
class StepResult:
    concurrency: int
    duration_s: float
    requests: int = 0
    errors: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    per_scenario: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @property
    def error_rate(self) -> float:
        return self.errors / self.requests if self.requests else 0.0

    @property
    def rps(self) -> float:
        return self.requests / self.duration_s if self.duration_s else 0.0

    def pct(self, p: float) -> float:
        if not self.latencies_ms:
            return 0.0
        data = sorted(self.latencies_ms)
        k = min(len(data) - 1, max(0, round(p / 100 * len(data)) - 1))
        return data[k]

    @property
    def slo_breached(self) -> bool:
        return self.pct(95) > SLO_P95_MS or self.error_rate > SLO_ERROR_RATE

    def summary(self) -> Dict[str, Any]:
        return {
            "concurrency": self.concurrency,
            "requests": self.requests,
            "rps": round(self.rps, 1),
            "errors": self.errors,
            "error_rate_pct": round(self.error_rate * 100, 2),
            "p50_ms": round(self.pct(50), 1),
            "p95_ms": round(self.pct(95), 1),
            "p99_ms": round(self.pct(99), 1),
            "max_ms": round(max(self.latencies_ms), 1) if self.latencies_ms else 0.0,
            "slo_breached": self.slo_breached,
            "per_scenario": self.per_scenario,
        }


def _weighted_cycle(scenarios: List[Scenario]) -> List[Scenario]:
    bag: List[Scenario] = []
    for s in scenarios:
        bag.extend([s] * s.weight)
    return bag


async def _login(client: httpx.AsyncClient, email: str, password: str) -> Optional[str]:
    try:
        r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        if r.status_code == 200:
            return r.json().get("access_token")
    except Exception:
        pass
    return None


async def _worker(
    client: httpx.AsyncClient,
    bag: List[Scenario],
    token: Optional[str],
    stop_at: float,
    result: StepResult,
    worker_id: int,
) -> None:
    i = worker_id  # offset so workers don't hit scenarios in lockstep
    while time.monotonic() < stop_at:
        s = bag[i % len(bag)]
        i += 1
        headers = {"Authorization": f"Bearer {token}"} if (s.needs_auth and token) else {}
        t0 = time.perf_counter()
        ok = False
        try:
            r = await client.request(s.method, s.path, params=s.params, headers=headers, timeout=30.0)
            ok = r.status_code < 500
        except Exception:
            ok = False
        elapsed_ms = (time.perf_counter() - t0) * 1000
        result.requests += 1
        result.latencies_ms.append(elapsed_ms)
        sc = result.per_scenario.setdefault(s.name, {"requests": 0, "errors": 0, "lat_sum": 0.0})
        sc["requests"] += 1
        sc["lat_sum"] += elapsed_ms
        if not ok:
            result.errors += 1
            sc["errors"] += 1


async def run_step(base_url: str, concurrency: int, duration_s: float, token: Optional[str]) -> StepResult:
    result = StepResult(concurrency=concurrency, duration_s=duration_s)
    bag = _weighted_cycle(SCENARIOS)
    limits = httpx.Limits(max_connections=concurrency + 10, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(base_url=base_url, limits=limits) as client:
        stop_at = time.monotonic() + duration_s
        await asyncio.gather(*(
            _worker(client, bag, token, stop_at, result, w) for w in range(concurrency)
        ))
    for sc in result.per_scenario.values():
        sc["avg_ms"] = round(sc.pop("lat_sum") / sc["requests"], 1) if sc["requests"] else 0.0
    return result


async def run_suite(
    base_url: str,
    steps: List[int],
    duration_s: float,
    email: Optional[str],
    password: Optional[str],
) -> Dict[str, Any]:
    async with httpx.AsyncClient(base_url=base_url) as client:
        token = await _login(client, email, password) if email and password else None

    results: List[StepResult] = []
    breaking_point: Optional[int] = None
    for c in steps:
        print(f"→ step: {c} concurrent workers for {duration_s:.0f}s", file=sys.stderr)
        step = await run_step(base_url, c, duration_s, token)
        results.append(step)
        s = step.summary()
        print(
            f"   {s['requests']} req  {s['rps']} rps  p50 {s['p50_ms']}ms  "
            f"p95 {s['p95_ms']}ms  err {s['error_rate_pct']}%"
            + ("  ← SLO BREACH" if step.slo_breached else ""),
            file=sys.stderr,
        )
        if step.slo_breached and breaking_point is None:
            breaking_point = c
            break  # no point hammering a saturated server further

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "slo": {"p95_ms": SLO_P95_MS, "error_rate": SLO_ERROR_RATE},
        "step_duration_s": duration_s,
        "authenticated": token is not None,
        "steps": [r.summary() for r in results],
        "breaking_point_concurrency": breaking_point,
        "max_sustained_concurrency": (
            max((r.concurrency for r in results if not r.slo_breached), default=None)
        ),
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Load Test Report (T-040 / LOAD-01)",
        "",
        f"- **Generated**: {report['generated_at']}",
        f"- **Target**: {report['base_url']}",
        f"- **SLO**: p95 < {report['slo']['p95_ms']:.0f} ms, error rate < {report['slo']['error_rate']*100:.0f}%",
        f"- **Step duration**: {report['step_duration_s']:.0f}s per concurrency level",
        f"- **Authenticated**: {report['authenticated']}",
        "",
        "## Results by concurrency",
        "",
        "| Concurrency | Requests | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error % | SLO |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in report["steps"]:
        lines.append(
            f"| {s['concurrency']} | {s['requests']} | {s['rps']} | {s['p50_ms']} "
            f"| {s['p95_ms']} | {s['p99_ms']} | {s['error_rate_pct']} "
            f"| {'BREACH' if s['slo_breached'] else 'OK'} |"
        )
    bp = report["breaking_point_concurrency"]
    ms = report["max_sustained_concurrency"]
    lines += [
        "",
        "## Breaking point",
        "",
        (
            f"**SLO breached at {bp} concurrent workers.** "
            f"Maximum sustained concurrency within SLO: **{ms}**."
            if bp is not None
            else f"**No breaking point found** up to {report['steps'][-1]['concurrency']} concurrent workers "
                 f"(max tested). Maximum sustained concurrency within SLO: **{ms}**."
        ),
        "",
        "## Per-scenario latency (last completed step)",
        "",
        "| Scenario | Requests | Errors | Avg (ms) |",
        "|---|---|---|---|",
    ]
    last = report["steps"][-1]["per_scenario"]
    for name, sc in sorted(last.items(), key=lambda kv: -kv[1]["avg_ms"]):
        lines.append(f"| {name} | {sc['requests']} | {sc['errors']} | {sc['avg_ms']} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="ProcureFlow load test suite (T-040)")
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--steps", default="5,10,25,50,100")
    ap.add_argument("--duration", type=float, default=15.0)
    ap.add_argument("--email")
    ap.add_argument("--password")
    ap.add_argument("--report", help="write markdown report to this path")
    ap.add_argument("--json", dest="json_path", help="write raw JSON to this path")
    args = ap.parse_args()

    steps = [int(x) for x in args.steps.split(",") if x.strip()]
    report = asyncio.run(run_suite(args.base_url, steps, args.duration, args.email, args.password))

    md = render_markdown(report)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"report written: {args.report}", file=sys.stderr)
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    # Windows consoles may be cp1252; never let encoding kill the run
    try:
        print(md)
    except UnicodeEncodeError:
        print(md.encode("ascii", "replace").decode("ascii"))


if __name__ == "__main__":
    main()
