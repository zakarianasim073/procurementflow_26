"""ENT-01 — Tenant context mechanism (unit, no DB).

Validates the foundation of multi-tenant isolation: the contextvar plumbing in
``app.core.tenant`` that the ``TenantAwareAsyncSession`` after_begin hook
consumes to issue ``SET LOCAL app.tenant_id`` / ``app.is_superuser``. If this
contract breaks, every RLS policy silently mis-scopes and tenants leak data.

Mirrors ADR-020 / SEC-02 guarantees:
* A missing context raises in strict mode (CI guard).
* A configured default tenant is used when no explicit context is set.
* superuser flag is carried alongside the tenant id.
"""
from __future__ import annotations

import os

import pytest

from app.core import tenant as tenant_mod
from app.core.tenant import (
    clear_tenant_context,
    get_tenant_context,
    require_tenant_context,
    resolve_tenant_id_for_session,
    set_tenant_context,
    strict_mode,
)


@pytest.fixture(autouse=True)
def _clean_context():
    clear_tenant_context()
    yield
    clear_tenant_context()


def test_set_and_get_roundtrip():
    set_tenant_context("tenant-a", is_superuser=True)
    tid, sup = get_tenant_context()
    assert tid == "tenant-a"
    assert sup is True


def test_clear_resets():
    set_tenant_context("tenant-b")
    clear_tenant_context()
    tid, sup = get_tenant_context()
    assert tid is None
    assert sup is False


def test_resolve_uses_explicit_context():
    set_tenant_context("tenant-c", is_superuser=False)
    tid, sup = resolve_tenant_id_for_session()
    assert tid == "tenant-c"
    assert sup is False


def test_resolve_falls_back_to_default_tenant(monkeypatch):
    monkeypatch.setenv("DEFAULT_TENANT_ID", "default-tenant")
    monkeypatch.delenv("TENANT_CONTEXT_REQUIRED", raising=False)
    monkeypatch.setattr(tenant_mod, "_environment", lambda: "development")
    clear_tenant_context()
    tid, sup = resolve_tenant_id_for_session()
    assert tid == "default-tenant"
    assert sup is False


def test_strict_mode_raises_without_context(monkeypatch):
    monkeypatch.setenv("TENANT_CONTEXT_REQUIRED", "1")
    monkeypatch.delenv("DEFAULT_TENANT_ID", raising=False)
    clear_tenant_context()
    assert strict_mode() is True
    with pytest.raises(RuntimeError):
        resolve_tenant_id_for_session()


def test_require_tenant_context_always_raises_without_context(monkeypatch):
    monkeypatch.delenv("DEFAULT_TENANT_ID", raising=False)
    clear_tenant_context()
    with pytest.raises(RuntimeError):
        require_tenant_context()


def test_strict_mode_off_in_development(monkeypatch):
    monkeypatch.delenv("TENANT_CONTEXT_REQUIRED", raising=False)
    monkeypatch.setattr(tenant_mod, "_environment", lambda: "development")
    assert strict_mode() is False
