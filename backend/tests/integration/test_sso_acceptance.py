"""ENT-02 acceptance: OIDC remains fail-closed until verification is implemented.

Drives the real API (`/api/v2/sso/oidc/init` -> `/api/v2/sso/oidc/callback`)
against a transaction-isolated DB session and asserts that unverified callback
values cannot issue a local session.
"""
from __future__ import annotations

import uuid

import httpx
import pytest
import pytest_asyncio

from app.db.base import get_async_session
from app.main import app
from app.models.sso import IdPConfig, IdPType, UserProvisioningPolicy
from app.models.enterprise import Tenant


@pytest_asyncio.fixture
async def client(db_session):
    """Test client whose DB dependency is overridden with the isolated session.

    The SSO router is loaded by the app lifespan in production; mount it here
    so the deferred routes exist for the test.
    """
    from app.api.v2.sso import router as sso_router

    if not any(getattr(r, "path", "") == "/api/v2/sso/oidc/init" for r in app.routes):
        app.include_router(sso_router, prefix="/api/v2")

    async def _override():
        yield db_session

    app.dependency_overrides[get_async_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def pilot_tenant(db_session):
    """Pilot tenant with seeded RBAC roles."""
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name="Pilot Tenant",
        slug=f"pilot-{uuid.uuid4().hex[:6]}",
        plan="enterprise",
    )
    db_session.add(tenant)
    await db_session.commit()
    from app.services.rbac_service import RBACService

    await RBACService.initialize_permissions(db_session)
    await RBACService.initialize_system_roles(db_session, tenant.id)
    return tenant


@pytest_asyncio.fixture
async def pilot_idp(db_session, pilot_tenant):
    """OIDC IdP config for the pilot tenant."""
    config = IdPConfig(
        id=str(uuid.uuid4()),
        tenant_id=pilot_tenant.id,
        name="Pilot Okta",
        idp_type=IdPType.OIDC,
        enabled=True,
        provisioning_policy=UserProvisioningPolicy.JIT,
        oidc_discovery_url="https://pilot.okta.com/.well-known/openid-configuration",
        oidc_client_id="pilot-client-id",
        oidc_client_secret="pilot-secret",
        oidc_redirect_uri="http://localhost:3000/sso/oidc/callback",
        oidc_scopes=["openid", "profile", "email"],
        claim_mappings={"email": "email", "name": "name", "roles": "groups"},
        role_mappings={"IdP_Team": "analyst", "Pilot_Admins": "admin"},
    )
    db_session.add(config)
    await db_session.commit()
    return config


@pytest.mark.asyncio
async def test_oidc_login_acceptance(client, db_session, pilot_tenant, pilot_idp):
    """OIDC initialization works, but an unverified callback cannot issue tokens."""
    # 1) Init -> authorization URL carries client_id, state, nonce
    init = await client.post(
        "/api/v2/sso/oidc/init",
        params={"idp_id": pilot_idp.id, "tenant_id": pilot_tenant.id},
    )
    assert init.status_code == 200
    init_body = init.json()
    assert "authorization_url" in init_body and "state" in init_body and "nonce" in init_body
    assert pilot_idp.oidc_client_id in init_body["authorization_url"]
    assert init_body["state"] and init_body["nonce"]

    # 2) Callback remains unavailable until code/state/token verification exists
    cb = await client.post(
        "/api/v2/sso/oidc/callback",
        params={"tenant_id": pilot_tenant.id},
        json={"code": "auth-code", "state": init_body["state"]},
    )
    assert cb.status_code == 503
    assert cb.json()["detail"] == "SSO authentication is not available"
