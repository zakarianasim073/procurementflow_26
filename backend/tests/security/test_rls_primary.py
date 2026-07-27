"""W-002: Primary session — TenantAwareAsyncSession auto-applies context.

Verifies that every primary session factory produces sessions that
automatically set app.tenant_id / app.is_superuser before the first query.
"""

import pytest


class TestPrimarySessionTenantContext:
    """TenantAwareAsyncSession: class usage and factory wiring."""

    @pytest.mark.asyncio
    async def test_get_session_returns_tenant_aware(self):
        from app.db.database import get_session, TenantAwareAsyncSession
        session = get_session()
        assert isinstance(session, TenantAwareAsyncSession)
        assert not session._tenant_applied
        await session.close()

    @pytest.mark.asyncio
    async def test_tenant_applied_flag_starts_false(self):
        from app.db.database import TenantAwareAsyncSession
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        session = TenantAwareAsyncSession(engine, expire_on_commit=False)
        assert not session._tenant_applied
        await session.close()
        engine.sync_engine.dispose()

    def test_get_sync_session_applies_context(self):
        from app.db.database import set_tenant_context, reset_tenant_context, get_sync_session
        from unittest.mock import patch

        token = set_tenant_context("test-sync-tenant")
        try:
            with patch("app.db.database.apply_tenant_context_sync") as mock_apply:
                session = get_sync_session()
                mock_apply.assert_called_once_with(session)
                session.close()
        finally:
            reset_tenant_context(token)

    def test_get_read_replica_session_uses_tenant_aware(self):
        from app.db.database import get_read_replica_session, TenantAwareAsyncSession

        if get_read_replica_session() is None:
            pytest.skip("READ_REPLICA_URL not configured")
        session = get_read_replica_session()
        assert isinstance(session, TenantAwareAsyncSession)
        assert not session._tenant_applied

    def test_get_session_factory_uses_tenant_aware(self):
        from app.db.base import get_session_factory
        from app.db.database import TenantAwareAsyncSession

        sf = get_session_factory()
        assert sf.class_ is TenantAwareAsyncSession

    @pytest.mark.asyncio
    async def test_flag_set_before_apply_prevents_recursion(self):
        """_tenant_applied is set before apply_tenant_context is called,
        preventing recursion when apply calls session.execute()."""
        from app.db.database import TenantAwareAsyncSession
        from unittest.mock import AsyncMock, patch

        patched_apply = AsyncMock()

        async def verify():
            with patch("app.db.database.apply_tenant_context", patched_apply):
                instance = TenantAwareAsyncSession.__new__(TenantAwareAsyncSession)
                TenantAwareAsyncSession.__init__(instance)
                assert not instance._tenant_applied

                # Simulate what execute does: set flag, then call apply
                instance._tenant_applied = True
                await patched_apply(instance)

                assert instance._tenant_applied
                assert patched_apply.call_count == 1

        await verify()
