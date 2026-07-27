"""
Tenant context (SEC-02 / ADR-020).

Centralizes the tenant identity that RLS policies consult via
``current_setting('app.tenant_id')`` / ``current_setting('app.is_superuser')``.

Every session-acquisition path (API request, Celery task, agent, script) must
set this context before querying tenant-scoped tables. ``database.py`` installs
a session ``after_begin`` hook that issues ``SET LOCAL`` from this contextvar,
so the RLS policy is satisfied on every connection without per-query code.

Design notes
------------
* This module imports ONLY stdlib (``os``, ``contextvars``) — it must never
  pull in ``app.*`` to avoid import cycles (it is imported by ``database``,
  ``main``, and ``celery_app``).
* In the current single-tenant deployment no tenant is configured, so the
  context defaults to ``None`` and the hook leaves ``app.tenant_id`` unset.
  RLS policies allow ``tenant_id IS NULL`` rows, so existing behavior is
  preserved exactly (no rows vanish).
* ``strict_mode`` (``ENVIRONMENT=test`` or ``TENANT_CONTEXT_REQUIRED=1``) makes
  a missing context raise loudly — used by the isolation test harness. The
  normal running app (development/production) never raises; it falls back to
  the optional ``DEFAULT_TENANT_ID`` env value instead.
"""
from __future__ import annotations

import os
from contextvars import ContextVar
from typing import Optional, Tuple

TENANT_SETTING = "app.tenant_id"
SUPERUSER_SETTING = "app.is_superuser"

_tenant_id: ContextVar[Optional[str]] = ContextVar("procureflow_tenant_id", default=None)
_is_superuser: ContextVar[bool] = ContextVar("procureflow_is_superuser", default=False)


def _environment() -> str:
    return os.environ.get("ENVIRONMENT", "development").strip().lower()


def strict_mode() -> bool:
    """True when a missing tenant context must raise (test runs)."""
    if os.environ.get("TENANT_CONTEXT_REQUIRED") == "1":
        return True
    return _environment() == "test"


def get_default_tenant_id() -> Optional[str]:
    """Optional global default tenant (single-tenant fallback)."""
    return os.environ.get("DEFAULT_TENANT_ID") or None


def set_tenant_context(tenant_id: Optional[str], is_superuser: bool = False) -> None:
    """Set the tenant identity for the current execution context."""
    _tenant_id.set(tenant_id)
    _is_superuser.set(bool(is_superuser))


def get_tenant_context() -> Tuple[Optional[str], bool]:
    """Return (tenant_id, is_superuser) for the current context."""
    return _tenant_id.get(), _is_superuser.get()


def clear_tenant_context() -> None:
    """Reset to unset (call in finally / middleware teardown)."""
    _tenant_id.set(None)
    _is_superuser.set(False)


def resolve_tenant_id_for_session() -> Tuple[Optional[str], bool]:
    """
    Resolve the tenant identity to apply to a new DB session.

    Returns (tenant_id, is_superuser). When no context is set, falls back to
    the configured default. In strict mode a still-missing context raises
    (ADR-020 guard) so silent cross-tenant data bugs are caught in tests.
    """
    tid, sup = get_tenant_context()
    if tid is None:
        tid = get_default_tenant_id()
    if tid is None and strict_mode():
        raise RuntimeError(
            "Tenant context missing: set_tenant_context(tenant_id, is_superuser) "
            "must be called before querying tenant-scoped tables (ADR-020). "
            "Sessions without context either see no rows or the wrong tenant's rows."
        )
    return tid, sup


def require_tenant_context() -> Tuple[Optional[str], bool]:
    """
    Like ``resolve_tenant_id_for_session`` but ALWAYS raises when the context
    is missing (used directly by the isolation test's negative case).
    """
    tid, sup = get_tenant_context()
    if tid is None:
        tid = get_default_tenant_id()
    if tid is None:
        raise RuntimeError(
            "Tenant context missing: set_tenant_context(tenant_id, is_superuser) "
            "must be called before querying tenant-scoped tables (ADR-020)."
        )
    return tid, sup
