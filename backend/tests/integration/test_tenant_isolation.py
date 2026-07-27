"""ENT-01 — Tenant isolation proof (integration, self-contained).

Two layers of the isolation guarantee are validated:

1. **Context plumbing** (unit side, see ``test_tenant_context.py``): the
   ``app.core.tenant`` contextvar that ``TenantAwareAsyncSession`` turns into
   ``SET LOCAL app.tenant_id`` / ``app.is_superuser``.

2. **Policy logic** (this file): the *exact* RLS USING expression from
   ``alembic/versions/011_enforce_tenant_rbac_context.py`` is evaluated as a
   predicate and proven to scope rows per tenant (+ superuser override).

IMPORTANT PRODUCTION GAP (captured here, not hidden):
PostgreSQL bypasses RLS for superuser / table-owner roles unless the table is
``FORCE ROW LEVEL SECURITY``. Migration 011 uses ``ENABLE`` (not ``FORCE``), so
if the application connects as a superuser role, tenant isolation is *silently
not enforced* — every tenant sees every row. The app must connect as a
dedicated non-superuser role (or the migrations must use FORCE RLS) for this
policy to actually protect data. The tests below assert the policy behaviour
for both a scoped role and the superuser override so the gap is explicit.

No pre-existing table is required (the live DB schema is behind head), so the
test stands up its own TEMP table and tears it down on connection close.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

# Exact USING clause from migration 011 (the production policy).
_POLICY_PREDICATE = (
    "tenant_id IS NULL "
    "OR current_setting('app.is_superuser', true) = 'true' "
    "OR tenant_id = current_setting('app.tenant_id', true)"
)


async def _eval(conn, tenant_id, is_superuser):
    # asyncpg cannot parameterize SET LOCAL; values are fixed test literals.
    # None means "no tenant context set" -> reset to the (NULL) default.
    if tenant_id is None:
        await conn.execute(text("SET LOCAL app.tenant_id TO DEFAULT"))
    else:
        await conn.execute(text(f"SET LOCAL app.tenant_id = '{tenant_id}'"))
    if is_superuser is None:
        await conn.execute(text("SET LOCAL app.is_superuser TO DEFAULT"))
    else:
        await conn.execute(text(f"SET LOCAL app.is_superuser = '{is_superuser}'"))
    rows = await conn.execute(text(
        f"SELECT payload FROM test_tenant_iso WHERE ({_POLICY_PREDICATE}) ORDER BY payload"
    ))
    return {r[0] for r in rows.fetchall()}


async def _reset(conn):
    await conn.execute(text("SET LOCAL app.tenant_id TO DEFAULT"))
    await conn.execute(text("SET LOCAL app.is_superuser TO DEFAULT"))


@pytest.mark.asyncio
async def test_rls_policy_isolates_tenants():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        await conn.execute(text(
            "CREATE TEMP TABLE IF NOT EXISTS test_tenant_iso "
            "(id serial PRIMARY KEY, tenant_id text, payload text)"
        ))
        await conn.execute(text(
            "INSERT INTO test_tenant_iso (tenant_id, payload) VALUES "
            "('tenant-1', 't1-a'), ('tenant-1', 't1-b'), "
            "('tenant-2', 't2-a'), (NULL, 'null-a')"
        ))

        # Scoped tenant-1 sees only its rows + NULL-tenant rows.
        assert await _eval(conn, "tenant-1", "false") == {"t1-a", "t1-b", "null-a"}
        # Scoped tenant-2 never sees tenant-1's data.
        assert await _eval(conn, "tenant-2", "false") == {"t2-a", "null-a"}
        assert "t1-a" not in await _eval(conn, "tenant-2", "false")

        # Superuser override sees everything (this is the role that bypasses
        # plain ENABLE RLS in production -> must use FORCE RLS or a non-superuser
        # app role to keep tenants isolated).
        assert await _eval(conn, "tenant-1", "true") == {
            "t1-a", "t1-b", "t2-a", "null-a"
        }

        # No tenant context -> only NULL-tenant rows are visible.
        await _reset(conn)
        assert await _eval(conn, None, "false") == {"null-a"}

        await conn.execute(text("DROP TABLE IF EXISTS test_tenant_iso"))
    await engine.dispose()
