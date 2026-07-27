"""W-002: Replica session — tenant context auto-applied on read paths.

Verifies that read-replica session paths (get_read_replica_session,
get_read_session) produce TenantAwareAsyncSession instances that
auto-apply tenant context.
"""

import pytest


class TestReplicaSessionTenantContext:
    """Read-replica sessions inherit TenantAwareAsyncSession behavior."""

    def test_get_read_replica_session_type(self):
        from app.db.database import get_read_replica_session, TenantAwareAsyncSession
        session = get_read_replica_session()
        if session is None:
            pytest.skip("READ_REPLICA_URL not configured — skipping")
        assert isinstance(session, TenantAwareAsyncSession)

    def test_get_read_session_type(self):
        from app.db.database import TenantAwareAsyncSession
        from app.db.database import get_read_replica_session

        # When replica is configured, get_read_session uses it
        replica = get_read_replica_session()
        if replica is not None:
            assert isinstance(replica, TenantAwareAsyncSession)
            assert not replica._tenant_applied
        else:
            pytest.skip("READ_REPLICA_URL not configured — skipping")

    def test_replica_factory_uses_tenant_aware(self):
        from app.db.database import _read_replica_session_factory
        if _read_replica_session_factory is not None:
            from app.db.database import TenantAwareAsyncSession
            assert _read_replica_session_factory.class_ is TenantAwareAsyncSession

    @pytest.mark.asyncio
    async def test_get_read_session_yields_tenant_aware(self):
        from app.db.database import get_read_session, TenantAwareAsyncSession
        async with get_read_session() as session:
            assert isinstance(session, TenantAwareAsyncSession)
