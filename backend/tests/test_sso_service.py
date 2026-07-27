"""T-037: SSO service tests (OIDC, SAML, provisioning, claims mapping)."""

from __future__ import annotations

import uuid
import pytest
from datetime import datetime, timezone, timedelta

from app.models.sso import IdPConfig, SSOSession, IdPType, UserProvisioningPolicy
from app.models.user import User
from app.models.enterprise import Tenant
from app.services.sso_service import (
    SSOService,
    InvalidClaimsError,
    UserNotFoundError,
)


@pytest.fixture()
async def tenant(db_session):
    """Create a test tenant with seeded RBAC roles (mirrors production provisioning)."""
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name="Test Tenant",
        slug=f"test-{uuid.uuid4().hex[:6]}",
        plan="pro",
    )
    db_session.add(tenant)
    await db_session.commit()
    # SSO provisioning requires the standard tenant roles to exist.
    from app.services.rbac_service import RBACService

    await RBACService.initialize_permissions(db_session)
    await RBACService.initialize_system_roles(db_session, tenant.id)
    return tenant


@pytest.fixture()
async def oidc_config(db_session, tenant):
    """Create OIDC IdP configuration."""
    config = IdPConfig(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        name="Okta OIDC",
        idp_type=IdPType.OIDC,
        enabled=True,
        provisioning_policy=UserProvisioningPolicy.JIT,
        oidc_discovery_url="https://dev-12345.okta.com/.well-known/openid-configuration",
        oidc_client_id="test-client-id",
        oidc_client_secret="test-client-secret",
        oidc_redirect_uri="http://localhost:3000/sso/oidc/callback",
        oidc_scopes=["openid", "profile", "email"],
        claim_mappings={
            "email": "email",
            "name": "name",
            "roles": "groups",
        },
        role_mappings={
            "Okta_Admins": "admin",
            "Okta_Analysts": "analyst",
            "Okta_Viewers": "viewer",
        },
    )
    db_session.add(config)
    await db_session.commit()
    return config


@pytest.fixture()
async def saml_config(db_session, tenant):
    """Create SAML IdP configuration."""
    config = IdPConfig(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        name="Azure AD SAML",
        idp_type=IdPType.SAML,
        enabled=True,
        provisioning_policy=UserProvisioningPolicy.REJECT,
        saml_entity_id="https://sts.windows.net/12345/",
        saml_sso_url="https://login.microsoftonline.com/12345/saml2",
        saml_certificate="MIIC...",
        saml_metadata_url="https://login.microsoftonline.com/12345/federationmetadata/2007-06/federationmetadata.xml",
        claim_mappings={
            "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
            "name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
            "roles": "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups",
        },
        role_mappings={
            "Azure_Admins": "admin",
            "Azure_Analysts": "analyst",
        },
    )
    db_session.add(config)
    await db_session.commit()
    return config


class TestSSOServiceBasics:
    """Test SSO service utility methods."""

    def test_generate_oidc_state_is_unique(self):
        """State tokens should be unique."""
        state1 = SSOService.generate_oidc_state()
        state2 = SSOService.generate_oidc_state()
        assert state1 != state2
        assert len(state1) > 20
        assert len(state2) > 20

    def test_generate_nonce_is_unique(self):
        """Nonce tokens should be unique."""
        nonce1 = SSOService.generate_nonce()
        nonce2 = SSOService.generate_nonce()
        assert nonce1 != nonce2
        assert len(nonce1) > 20


class TestClaimExtraction:
    """Test claim extraction and mapping."""

    @pytest.mark.asyncio
    async def test_extract_claims_with_standard_mapping(self, db_session, oidc_config):
        """Extract claims using default OIDC claim names."""
        raw_claims = {
            "sub": "user-123",
            "email": "user@example.com",
            "name": "John Doe",
            "groups": ["Okta_Admins"],
        }

        extracted = await SSOService.extract_claims(db_session, oidc_config, raw_claims)

        assert extracted["email"] == "user@example.com"
        assert extracted["name"] == "John Doe"
        assert extracted["idp_subject_id"] == "user-123"
        assert extracted["raw_roles"] == ["Okta_Admins"]

    @pytest.mark.asyncio
    async def test_extract_claims_with_custom_mapping(self, db_session, saml_config):
        """Extract claims using custom SAML claim mappings."""
        raw_claims = {
            "Subject": "saml-user-456",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": "saml@example.com",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": "SAML User",
            "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups": ["Azure_Admins"],
        }

        extracted = await SSOService.extract_claims(db_session, saml_config, raw_claims)

        assert extracted["email"] == "saml@example.com"
        assert extracted["name"] == "SAML User"
        assert extracted["idp_subject_id"] == "saml-user-456"
        assert extracted["raw_roles"] == ["Azure_Admins"]

    @pytest.mark.asyncio
    async def test_extract_claims_missing_email_raises(self, db_session, oidc_config):
        """Missing email claim should raise InvalidClaimsError."""
        raw_claims = {
            "sub": "user-123",
            "name": "John Doe",
        }

        with pytest.raises(InvalidClaimsError):
            await SSOService.extract_claims(db_session, oidc_config, raw_claims)

    @pytest.mark.asyncio
    async def test_extract_claims_missing_subject_raises(self, db_session, oidc_config):
        """Missing subject claim should raise InvalidClaimsError."""
        raw_claims = {
            "email": "user@example.com",
            "name": "John Doe",
        }

        with pytest.raises(InvalidClaimsError):
            await SSOService.extract_claims(db_session, oidc_config, raw_claims)


class TestRoleMapping:
    """Test role mapping from IdP to local roles."""

    @pytest.mark.asyncio
    async def test_map_roles_with_configured_mappings(self, oidc_config):
        """Map IdP roles to local roles using config."""
        raw_roles = ["Okta_Admins", "Okta_Analysts"]
        mapped = await SSOService.map_roles(oidc_config, raw_roles)
        assert set(mapped) == {"admin", "analyst"}

    @pytest.mark.asyncio
    async def test_map_roles_fallback_to_raw_role_name(self, oidc_config):
        """Unmapped roles fallback to lowercased raw name."""
        raw_roles = ["Unknown_Role"]
        mapped = await SSOService.map_roles(oidc_config, raw_roles)
        assert "unknown_role" in mapped

    @pytest.mark.asyncio
    async def test_map_empty_roles_defaults_to_viewer(self, oidc_config):
        """Empty role list defaults to viewer."""
        mapped = await SSOService.map_roles(oidc_config, [])
        assert mapped == ["viewer"]


class TestUserProvisioning:
    """Test user provisioning on SSO login."""

    @pytest.mark.asyncio
    async def test_existing_user_not_re_provisioned(self, db_session, tenant, oidc_config):
        """Login with existing user should not provision."""
        # Create existing user
        user = User(
            id=str(uuid.uuid4()),
            email="existing@example.com",
            full_name="Existing User",
            tenant_id=tenant.id,
            hashed_password="hash",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()

        extracted = {
            "email": "existing@example.com",
            "name": "Still Existing",
            "idp_subject_id": "idp-123",
            "raw_roles": [],
        }

        returned_user, is_new = await SSOService.provision_or_login_user(
            db_session, tenant.id, oidc_config, extracted
        )

        assert returned_user.id == user.id
        assert is_new is False

    @pytest.mark.asyncio
    async def test_jit_provisioning_creates_new_user(self, db_session, tenant, oidc_config):
        """JIT policy should create new user on login."""
        extracted = {
            "email": "newuser@example.com",
            "name": "New User",
            "idp_subject_id": "idp-456",
            "raw_roles": [],
        }

        user, is_new = await SSOService.provision_or_login_user(
            db_session, tenant.id, oidc_config, extracted
        )

        assert is_new is True
        assert user.email == "newuser@example.com"
        assert user.full_name == "New User"
        assert user.tenant_id == tenant.id

    @pytest.mark.asyncio
    async def test_reject_policy_raises_on_unknown_user(self, db_session, tenant, saml_config):
        """REJECT policy should raise on unknown user."""
        extracted = {
            "email": "unknown@example.com",
            "name": "Unknown User",
            "idp_subject_id": "idp-789",
            "raw_roles": [],
        }

        with pytest.raises(UserNotFoundError):
            await SSOService.provision_or_login_user(
                db_session, tenant.id, saml_config, extracted
            )


@pytest.fixture()
async def user(db_session, tenant):
    """Create a real User row (sso_sessions.user_id is a FK to users)."""
    from app.models.user import User

    u = User(
        id=str(uuid.uuid4()),
        email=f"user-{uuid.uuid4().hex[:6]}@example.com",
        full_name="Test User",
        tenant_id=tenant.id,
        hashed_password="hash",
        is_active=True,
    )
    db_session.add(u)
    await db_session.commit()
    return u


class TestSSOSession:
    """Test SSO session lifecycle."""

    @pytest.mark.asyncio
    async def test_create_sso_session(self, db_session, tenant, user, oidc_config):
        """Create SSO session with proper lifecycle."""
        idp_config_id = oidc_config.id
        idp_subject_id = "idp-user-123"

        session = await SSOService.create_sso_session(
            db_session,
            user.id,
            tenant.id,
            idp_config_id,
            idp_subject_id,
            state="state-123",
            nonce="nonce-456",
            expires_in_hours=24,
        )

        assert session.user_id == user.id
        assert session.tenant_id == tenant.id
        assert session.idp_config_id == idp_config_id
        assert session.idp_subject_id == idp_subject_id
        assert session.state == "state-123"
        assert session.nonce == "nonce-456"
        assert session.logged_out_at is None
        assert session.expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_get_sso_session(self, db_session, tenant, user, oidc_config):
        """Retrieve SSO session by ID."""
        idp_config_id = oidc_config.id

        session = await SSOService.create_sso_session(
            db_session,
            user.id,
            tenant.id,
            idp_config_id,
            "idp-subject",
        )

        retrieved = await SSOService.get_sso_session(db_session, session.id)
        assert retrieved.id == session.id
        assert retrieved.user_id == user.id

    @pytest.mark.asyncio
    async def test_logout_sso_session(self, db_session, tenant, user, oidc_config):
        """Mark SSO session as logged out."""
        idp_config_id = oidc_config.id

        session = await SSOService.create_sso_session(
            db_session,
            user.id,
            tenant.id,
            idp_config_id,
            "idp-subject",
        )

        success = await SSOService.logout_sso_session(db_session, session.id)
        assert success is True

        retrieved = await SSOService.get_sso_session(db_session, session.id)
        assert retrieved.logged_out_at is not None

    @pytest.mark.asyncio
    async def test_logout_nonexistent_session_returns_false(self, db_session):
        """Logout nonexistent session returns False."""
        success = await SSOService.logout_sso_session(db_session, "nonexistent-id")
        assert success is False


class TestCompleteSSLogin:
    """Test complete SSO login flow integration."""

    @pytest.mark.asyncio
    async def test_complete_oidc_login_new_user(self, db_session, tenant, oidc_config):
        """Complete OIDC flow for new user: extract → provision → session → tokens."""
        raw_claims = {
            "sub": "okta-user-123",
            "email": "newoidc@example.com",
            "name": "OIDC User",
            "groups": ["Okta_Analysts"],
        }

        result = await SSOService.complete_sso_login(db_session, tenant.id, oidc_config, raw_claims)

        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
        assert result["user"]["email"] == "newoidc@example.com"
        assert result["is_new_user"] is True
        assert "sso_session_id" in result

    @pytest.mark.asyncio
    async def test_complete_saml_login_existing_user(self, db_session, tenant, saml_config):
        """Complete SAML flow for existing user."""
        # Create existing user
        user = User(
            id=str(uuid.uuid4()),
            email="existing@example.com",
            full_name="Existing User",
            tenant_id=tenant.id,
            hashed_password="hash",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        # complete_sso_login maps IdP groups -> local role via change_user_role,
        # which requires the user to already be a tenant member.
        from app.services.rbac_service import RBACService

        await RBACService.add_tenant_member(db_session, tenant.id, user.id, "viewer")

        raw_claims = {
            "Subject": "azure-user-456",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": "existing@example.com",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": "Existing User",
            "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups": ["Azure_Admins"],
        }

        result = await SSOService.complete_sso_login(db_session, tenant.id, saml_config, raw_claims)

        assert result["user"]["id"] == user.id
        assert result["is_new_user"] is False
        assert "sso_session_id" in result

    @pytest.mark.asyncio
    async def test_complete_login_reject_policy_unknown_user(self, db_session, tenant, saml_config):
        """REJECT policy should fail on unknown user during complete login."""
        raw_claims = {
            "Subject": "unknown-user",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": "unknown@example.com",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": "Unknown",
            "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups": [],
        }

        with pytest.raises(UserNotFoundError):
            await SSOService.complete_sso_login(db_session, tenant.id, saml_config, raw_claims)
