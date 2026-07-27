"""W-002: No tenant context — session fails closed (zero rows).

Verifies that without setting tenant context, sessions still function
but apply the NO_TENANT fallback. In strict mode (RLS_STRICT_CONTEXT=true),
missing context raises an error instead.
"""

import os
import pytest


class TestNoContextBehavior:
    """Sessions without tenant context use __no_tenant__ fallback."""

    def test_no_context_uses_fallback(self):
        from app.db.database import _resolve_tenant_context, NO_TENANT

        tid, _ = _resolve_tenant_context()
        assert tid == NO_TENANT

    def test_strict_mode_raises(self):
        from app.db.database import (
            _resolve_tenant_context, MissingTenantContextError,
            _STRICT_TENANT_CONTEXT,
        )
        if not _STRICT_TENANT_CONTEXT:
            pytest.skip("RLS_STRICT_CONTEXT not enabled — skipping strict-mode test")

        with pytest.raises(MissingTenantContextError):
            _resolve_tenant_context()

    def test_tenant_context_propagates(self):
        from app.db.database import (
            set_tenant_context, reset_tenant_context,
            get_tenant_context, _resolve_tenant_context,
        )

        assert get_tenant_context() is None
        token = set_tenant_context("my-tenant", is_superuser=True)
        try:
            tid, sup = get_tenant_context()
            assert tid == "my-tenant"
            assert sup is True

            resolved_tid, resolved_sup = _resolve_tenant_context()
            assert resolved_tid == "my-tenant"
            assert resolved_sup is True
        finally:
            reset_tenant_context(token)

        assert get_tenant_context() is None

    def test_tenant_context_reset(self):
        from app.db.database import set_tenant_context, reset_tenant_context, get_tenant_context

        token = set_tenant_context("tenant-a")
        assert get_tenant_context() == ("tenant-a", False)
        reset_tenant_context(token)
        assert get_tenant_context() is None

    def test_tenant_context_nested(self):
        from app.db.database import set_tenant_context, reset_tenant_context, get_tenant_context

        token_outer = set_tenant_context("outer")
        try:
            token_inner = set_tenant_context("inner")
            try:
                assert get_tenant_context() == ("inner", False)
            finally:
                reset_tenant_context(token_inner)
            assert get_tenant_context() == ("outer", False)
        finally:
            reset_tenant_context(token_outer)

    def test_strict_env_var_read(self):
        from app.db.database import _STRICT_TENANT_CONTEXT
        expected = os.getenv("RLS_STRICT_CONTEXT", "false").strip().lower() == "true"
        assert _STRICT_TENANT_CONTEXT == expected

    def test_sync_tenant_context_applies(self):
        from app.db.database import (
            set_tenant_context, reset_tenant_context,
            apply_tenant_context_sync,
        )
        from unittest.mock import MagicMock

        token = set_tenant_context("sync-tenant")
        try:
            mock_session = MagicMock()
            apply_tenant_context_sync(mock_session)
            mock_session.execute.assert_called_once()
            call_args = str(mock_session.execute.call_args[0][0])
            assert "set_config" in call_args
            assert "app.tenant_id" in call_args
        finally:
            reset_tenant_context(token)
