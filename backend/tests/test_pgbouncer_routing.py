"""T-011 (DB-03): PgBouncer routing — async engine URL resolution + prepared-statement guard."""
from __future__ import annotations

import asyncio

import pytest

import app.db.database as database


@pytest.fixture(autouse=True)
def _reset_engine_singleton():
    """Ensure get_engine() rebuilds fresh for each test (module-level singleton)."""
    yield
    if database._engine is not None:
        asyncio.run(database._engine.dispose())
    database._engine = None


class TestPgBouncerRouting:
    def test_no_pgbouncer_url_uses_direct_database_url(self, monkeypatch):
        monkeypatch.setattr(database, "_PGBOUNCER_URL", "")
        assert not database.using_pgbouncer()
        assert database._resolve_async_engine_url() == database.DATABASE_URL

    def test_pgbouncer_url_overrides_async_engine_only(self, monkeypatch):
        pooled = "postgresql+asyncpg://postgres:pw@127.0.0.1:6432/procureflow_bd"
        monkeypatch.setattr(database, "_PGBOUNCER_URL", pooled)
        assert database.using_pgbouncer()
        assert database._resolve_async_engine_url() == pooled
        # Sync engine (Alembic path) is untouched — still direct
        assert "6432" not in database.SYNC_DATABASE_URL

    def test_bare_postgresql_scheme_normalized_to_asyncpg(self, monkeypatch):
        monkeypatch.setattr(database, "_PGBOUNCER_URL", "postgresql://postgres:pw@127.0.0.1:6432/procureflow_bd")
        assert database._resolve_async_engine_url().startswith("postgresql+asyncpg://")

    def test_connect_args_disable_statement_cache_when_pooled(self, monkeypatch):
        monkeypatch.setattr(database, "_PGBOUNCER_URL", "postgresql+asyncpg://postgres:pw@127.0.0.1:6432/procureflow_bd")
        assert database._async_connect_args() == {"statement_cache_size": 0}

    def test_connect_args_empty_when_not_pooled(self, monkeypatch):
        monkeypatch.setattr(database, "_PGBOUNCER_URL", "")
        assert database._async_connect_args() == {}

    def test_engine_constructs_cleanly_in_both_modes(self, monkeypatch):
        for url in ("", "postgresql+asyncpg://postgres:pw@127.0.0.1:6432/procureflow_bd"):
            monkeypatch.setattr(database, "_PGBOUNCER_URL", url)
            database._engine = None
            engine = database.get_engine()
            assert engine is not None


class TestDatabaseHealthReportsRouting:
    @pytest.mark.asyncio
    async def test_check_database_health_includes_via_pgbouncer_flag(self, monkeypatch):
        monkeypatch.setattr(database, "_PGBOUNCER_URL", "")
        health = await database.check_database_health()
        assert "via_pgbouncer" in health
        assert health["via_pgbouncer"] is False
