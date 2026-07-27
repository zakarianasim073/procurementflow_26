"""T-009 (API-02): health/readiness/liveness probe surface."""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.core.security import create_token


@pytest.fixture(scope="module")
def client():
    with TestClient(main.app) as tc:
        yield tc


@pytest.fixture(scope="module")
def auth_headers():
    token = create_token("health-probe-test", "enterprise", role="owner")
    return {"Authorization": f"Bearer {token}"}


async def _ok():
    return {}


async def _fail():
    raise RuntimeError("dependency down")


@pytest.fixture(autouse=True)
def healthy_celery(monkeypatch):
    monkeypatch.setattr(main, "_probe_celery", _ok)


class TestLiveness:
    def test_live_always_200(self, client):
        r = client.get("/api/live")
        assert r.status_code == 200 and r.json()["status"] == "alive"


class TestReadiness:
    def test_ready_503_when_gating_dep_down(self, client, monkeypatch):
        monkeypatch.setattr(main, "_probe_database", _fail)
        monkeypatch.setattr(main, "_probe_redis", _ok)
        r = client.get("/api/ready")
        assert r.status_code == 503
        body = r.json()
        assert body["status"] == "not_ready"
        assert body["checks"]["database"]["ok"] is False
        assert "error" in body["checks"]["database"]

    def test_ready_200_when_all_gating_pass(self, client, monkeypatch):
        monkeypatch.setattr(main, "_probe_database", _ok)
        monkeypatch.setattr(main, "_probe_redis", _ok)
        monkeypatch.setattr(main.app.state, "api_routers_loaded", True)
        r = client.get("/api/ready")
        assert r.status_code == 200
        assert r.json()["status"] == "ready"

    def test_ready_503_when_no_worker_responds(self, client, monkeypatch):
        monkeypatch.setattr(main, "_probe_database", _ok)
        monkeypatch.setattr(main, "_probe_redis", _ok)
        monkeypatch.setattr(main, "_probe_celery", _fail)
        monkeypatch.setattr(main.app.state, "api_routers_loaded", True)
        r = client.get("/api/ready")
        assert r.status_code == 503
        assert r.json()["checks"]["celery"]["ok"] is False

    def test_ready_503_during_deferred_loading(self, client, monkeypatch):
        """Acceptance: 503 while routers still loading, 200 after."""
        monkeypatch.setattr(main, "_probe_database", _ok)
        monkeypatch.setattr(main, "_probe_redis", _ok)
        monkeypatch.setattr(main.app.state, "api_routers_loaded", False)
        assert client.get("/api/ready").status_code == 503
        monkeypatch.setattr(main.app.state, "api_routers_loaded", True)
        assert client.get("/api/ready").status_code == 200

    def test_agents_reported_but_not_gating(self, client, monkeypatch):
        monkeypatch.setattr(main, "_probe_database", _ok)
        monkeypatch.setattr(main, "_probe_redis", _ok)
        monkeypatch.setattr(main, "_probe_agents", _fail)
        monkeypatch.setattr(main.app.state, "api_routers_loaded", True)
        r = client.get("/api/ready")
        assert r.status_code == 200
        assert r.json()["checks"]["agents"]["ok"] is False

    def test_every_check_reports_latency(self, client, monkeypatch):
        monkeypatch.setattr(main, "_probe_database", _ok)
        monkeypatch.setattr(main, "_probe_redis", _fail)
        r = client.get("/api/ready")
        for name in ("database", "redis", "agents"):
            assert "latency_ms" in r.json()["checks"][name]


class TestSubChecks:
    @pytest.mark.parametrize("path,dep", [
        ("/api/health/db", "postgresql"),
        ("/api/health/redis", "redis"),
        ("/api/health/celery", "celery-broker"),
        ("/api/health/agents", "agent-runtime"),
    ])
    def test_subcheck_shape(self, client, auth_headers, path, dep):
        r = client.get(path, headers=auth_headers)
        assert r.status_code == 200  # detail endpoints always 200; ok flag carries state
        body = r.json()
        assert body["dependency"] == dep
        assert "ok" in body and "latency_ms" in body

    def test_subchecks_bounded_even_when_down(self, client, auth_headers, monkeypatch):
        """Acceptance: <1.5s response with a dependency down (timeout-bounded)."""
        async def _hang():
            import asyncio
            await asyncio.sleep(30)
        monkeypatch.setattr(main, "_probe_redis", _hang)
        started = time.perf_counter()
        r = client.get("/api/health/redis", headers=auth_headers)
        elapsed = time.perf_counter() - started
        assert elapsed < 1.5
        assert r.json()["ok"] is False

    def test_db_subcheck_includes_pool_stats_when_up(self, client, auth_headers):
        r = client.get("/api/health/db", headers=auth_headers)
        if r.json()["ok"]:
            assert "pool" in r.json()
