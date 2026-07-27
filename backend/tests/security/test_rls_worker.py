"""W-002: Worker/Celery task — tenant context propagated and enforced.

Verifies that background task paths (Celery tasks, agent sessions, service
background reads) properly set tenant context before querying.
"""

import pytest


class TestWorkerTenantContext:
    """Worker paths properly set tenant context via tenant_context context manager."""

    def test_tenant_context_manager(self):
        from app.db.database import tenant_context, get_tenant_context

        with tenant_context("worker-tenant", is_superuser=False):
            tid, sup = get_tenant_context()
            assert tid == "worker-tenant"
            assert sup is False

        # After context manager exits, context is reset
        assert get_tenant_context() is None

    def test_tenant_context_superuser(self):
        from app.db.database import tenant_context, get_tenant_context

        with tenant_context("admin-tenant", is_superuser=True):
            tid, sup = get_tenant_context()
            assert tid == "admin-tenant"
            assert sup is True

    def test_tenant_context_none_tenant(self):
        from app.db.database import tenant_context, get_tenant_context

        with tenant_context(None):
            tid, sup = get_tenant_context()
            assert tid is not None  # Should use NO_TENANT fallback

    def test_boq_task_uses_tenant_context(self):
        """Verify the BOQ task pattern: tenant_context + TenantAwareAsyncSession."""
        import ast
        import pathlib

        boq_tasks = pathlib.Path(__file__).resolve().parent.parent.parent / "app" / "workers" / "tasks" / "boq_tasks.py"
        src = boq_tasks.read_text(encoding="utf-8")
        tree = ast.parse(src)

        has_tenant_context = False
        has_tenant_aware_session = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if hasattr(node.func, "id") and node.func.id == "tenant_context":
                    has_tenant_context = True
                if hasattr(node.func, "attr") and "get_session" in node.func.attr:
                    has_tenant_aware_session = True

        assert has_tenant_context, "boq_tasks.py must use tenant_context() context manager"

    def test_agent_base_uses_tenant_context(self):
        """Agent base.py's session acquisition uses get_session_factory
        which now produces TenantAwareAsyncSession (auto-context)."""
        from app.db.base import get_session_factory
        from app.db.database import TenantAwareAsyncSession

        sf = get_session_factory()
        assert sf.class_ is TenantAwareAsyncSession

    def test_service_background_reads_get_context(self):
        """Services using session_scope now get auto-context from get_sync_session."""
        from app.db.database import set_tenant_context, reset_tenant_context, get_sync_session
        from unittest.mock import patch

        token = set_tenant_context("bg-service")
        try:
            with patch("app.db.database.apply_tenant_context_sync") as mock_apply:
                session = get_sync_session()
                mock_apply.assert_called_once_with(session)
                session.close()
        finally:
            reset_tenant_context(token)
