"""T-034 (ENT-07): Read replica + caching strategy.

Tests verify:
  1. get_read_db() yields the primary session when READ_REPLICA_URL is not set.
  2. get_read_db() yields a replica session when READ_REPLICA_URL is set.
  3. advanced_analytics._analytics_db_url() returns the primary sync URL when
     no replica is configured.
  4. advanced_analytics._analytics_db_url() returns the replica URL (converted to
     psycopg2 format) when READ_REPLICA_URL is set.
  5. check_replica_lag() returns a dict with expected keys; no replica = has_replica False.
  6. /api/health/replica endpoint responds with 200 and expected fields.
"""
from __future__ import annotations

import os
import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# ── Unit: _analytics_db_url() ─────────────────────────────────────────────────

def test_analytics_db_url_no_replica(monkeypatch):
    """Without READ_REPLICA_URL, returns the primary sync URL with no asyncpg."""
    monkeypatch.delenv("READ_REPLICA_URL", raising=False)
    # _analytics_db_url reads os.getenv at call time — no reload needed.
    from app.api.v1.advanced_analytics import _analytics_db_url
    url = _analytics_db_url()
    assert "asyncpg" not in url


def test_analytics_db_url_with_replica(monkeypatch):
    """When READ_REPLICA_URL is set (asyncpg format), returns psycopg2-compatible URL."""
    monkeypatch.setenv("READ_REPLICA_URL", "postgresql+asyncpg://user:pw@replica:5432/db")
    from app.api.v1.advanced_analytics import _analytics_db_url
    url = _analytics_db_url()
    assert url.startswith("postgresql://")
    assert "replica" in url
    assert "asyncpg" not in url


def test_analytics_db_url_with_psycopg2_replica(monkeypatch):
    """READ_REPLICA_URL with psycopg2 prefix is also normalized correctly."""
    monkeypatch.setenv("READ_REPLICA_URL", "postgresql+psycopg2://user:pw@replica:5432/db")
    from app.api.v1.advanced_analytics import _analytics_db_url
    url = _analytics_db_url()
    assert url.startswith("postgresql://")
    assert "psycopg2" not in url


# ── Unit: get_read_db() routes ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_read_db_no_replica_uses_primary(monkeypatch):
    """Without a replica, get_read_db() falls back to the primary engine."""
    import app.db.database as db_module

    sessions_from = []

    @asynccontextmanager
    async def _fake_get_async_session():
        class _S:
            async def close(self):
                pass
        s = _S()
        sessions_from.append("primary")
        yield s

    # Patch both get_read_replica_session (returns None → no replica) and
    # get_async_session (the fallback) on the database module so get_read_session
    # picks them up from module globals.
    monkeypatch.setattr(db_module, "get_read_replica_session", lambda: None)
    monkeypatch.setattr(db_module, "get_async_session", _fake_get_async_session)

    gen = db_module.get_read_db()
    session = await gen.__anext__()
    assert sessions_from == ["primary"]
    try:
        await gen.__anext__()
    except StopAsyncIteration:
        pass


@pytest.mark.asyncio
async def test_get_read_db_uses_replica_when_configured(monkeypatch):
    """With a replica session available, get_read_db() yields that session."""
    import app.db.database as db_module

    fake_replica_session = MagicMock()
    fake_replica_session.close = AsyncMock()

    # Patch get_read_replica_session to return a truthy mock session.
    monkeypatch.setattr(db_module, "get_read_replica_session", lambda: fake_replica_session)

    gen = db_module.get_read_db()
    session = await gen.__anext__()
    assert session is fake_replica_session
    try:
        await gen.__anext__()
    except StopAsyncIteration:
        pass
    fake_replica_session.close.assert_awaited_once()


# ── Unit: check_replica_lag() ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_replica_lag_no_replica_configured(monkeypatch):
    """Without READ_REPLICA_URL, has_replica is False; max_lag_seconds is None."""
    import app.db.database as db_module

    monkeypatch.setattr(db_module, "_READ_REPLICA_URL", "")

    # Simulate pg_stat_replication returning 0 rows (no standbys).
    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_conn.execute = AsyncMock(return_value=mock_result)

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_conn
    monkeypatch.setattr(db_module, "get_engine", lambda: mock_engine)

    result = await db_module.check_replica_lag()
    assert result["has_replica"] is False
    assert result["max_lag_seconds"] is None
    assert result["replication_slots"] == []


@pytest.mark.asyncio
async def test_check_replica_lag_with_replica_and_lag(monkeypatch):
    """When pg_stat_replication returns a standby, lag is surfaced correctly."""
    import app.db.database as db_module

    monkeypatch.setattr(db_module, "_READ_REPLICA_URL", "postgresql+asyncpg://u:p@r:5432/db")

    # Simulate one standby with 5s lag and 1024 bytes lag.
    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("standby1", 5.0, 1024)]
    mock_conn.execute = AsyncMock(return_value=mock_result)

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_conn
    monkeypatch.setattr(db_module, "get_engine", lambda: mock_engine)

    result = await db_module.check_replica_lag()
    assert result["has_replica"] is True
    assert result["max_lag_seconds"] == 5.0
    assert len(result["replication_slots"]) == 1
    assert result["replication_slots"][0]["lag_seconds"] == 5.0


# ── Integration: /api/health/replica endpoint ──────────────────────────────────

def test_health_replica_endpoint_returns_200(monkeypatch):
    """GET /api/health/replica returns 200 with expected fields."""
    from app.main import app

    async def _fake_lag():
        return {
            "has_replica": False,
            "replication_slots": [],
            "max_lag_seconds": None,
        }

    monkeypatch.setattr("app.db.database.check_replica_lag", _fake_lag)

    client = TestClient(app, raise_server_exceptions=True)
    resp = client.get("/api/health/replica")
    assert resp.status_code == 200
    body = resp.json()
    assert body["dependency"] == "read-replica"
    assert "ok" in body
    assert "has_replica" in body
    assert "max_lag_seconds" in body


def test_health_replica_ok_false_when_lag_exceeds_threshold(monkeypatch):
    """ok is False when max_lag_seconds > REPLICA_LAG_WARN_SECONDS."""
    from app.main import app
    from app.core.config import settings

    # Force threshold to 10s, mock lag at 60s.
    monkeypatch.setattr(settings, "REPLICA_LAG_WARN_SECONDS", 10)

    async def _fake_lag():
        return {
            "has_replica": True,
            "replication_slots": [{"slot_name": "s1", "lag_seconds": 60.0, "lag_bytes": 1024}],
            "max_lag_seconds": 60.0,
        }

    monkeypatch.setattr("app.db.database.check_replica_lag", _fake_lag)

    client = TestClient(app, raise_server_exceptions=True)
    resp = client.get("/api/health/replica")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["max_lag_seconds"] == 60.0
