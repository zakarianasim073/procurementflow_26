"""SSO service: OIDC and SAML login flows (T-037)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Tuple
import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sso import IdPConfig, SSOSession, IdPType, UserProvisioningPolicy
from app.models.user import User
from app.models.enterprise import TenantMember, Role
from app.core.security import create_token, decode_token
from app.services.rbac_service import RBACService

logger = logging.getLogger(__name__)


class SSOError(Exception):
    """Base SSO error."""
    pass


class InvalidClaimsError(SSOError):
    """Invalid or missing claims from IdP."""
    pass


class UserNotFoundError(SSOError):
    """User not found and provisioning policy is REJECT."""
    pass


class SSOService:
    """Handle OIDC and SAML authentication flows."""

    @staticmethod
    async def get_idp_config(
        db: AsyncSession,
        tenant_id: str,
        idp_id: Optional[str] = None,
    ) -> Optional[IdPConfig]:
        """Get IdP config for tenant (optionally specific IdP)."""
        query = select(IdPConfig).where(
            (IdPConfig.tenant_id == tenant_id) & (IdPConfig.enabled == True)
        )
        if idp_id:
            query = query.where(IdPConfig.id == idp_id)
        return await db.scalar(query)

    @staticmethod
    async def list_idp_configs(
        db: AsyncSession,
        tenant_id: str,
    ) -> list[IdPConfig]:
        """List all enabled IdP configs for tenant."""
        result = await db.execute(
            select(IdPConfig).where(
                (IdPConfig.tenant_id == tenant_id) & (IdPConfig.enabled == True)
            )
        )
        return result.scalars().all()

    @staticmethod
    def generate_oidc_state() -> str:
        """Generate OIDC state parameter (CSRF protection)."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_nonce() -> str:
        """Generate OIDC nonce (replay protection)."""
        return secrets.token_urlsafe(32)

    @staticmethod
    async def extract_claims(
        db: AsyncSession,
        idp_config: IdPConfig,
        raw_claims: Dict,
    ) -> Dict:
        """Extract and map IdP claims to app fields.

        Uses claim_mappings from IdP config to extract:
        - email
        - name
        - tenant (if multi-tenant)
        - roles (if present)
        """
        mappings = idp_config.claim_mappings or {}

        extracted = {
            "email": raw_claims.get(mappings.get("email", "email"), "").strip(),
            "name": raw_claims.get(mappings.get("name", "name"), "").strip(),
            "idp_subject_id": raw_claims.get("sub", raw_claims.get("Subject")),  # Standard claims
        }

        # Extract roles if present
        roles_claim = mappings.get("roles", "groups")
        raw_roles = raw_claims.get(roles_claim, [])
        if isinstance(raw_roles, str):
            raw_roles = [raw_roles]
        extracted["raw_roles"] = raw_roles or []

        if not extracted["email"]:
            raise InvalidClaimsError("Missing or empty email claim")
        if not extracted["idp_subject_id"]:
            raise InvalidClaimsError("Missing subject claim")

        return extracted

    @staticmethod
    async def map_roles(
        idp_config: IdPConfig,
        raw_roles: list[str],
    ) -> list[str]:
        """Map IdP roles to local roles using config role_mappings.

        Example:
        - IdP returns: ["IdP_Admins", "IdP_Team"]
        - role_mappings: {"IdP_Admins": "admin", "IdP_Team": "analyst"}
        - Returns: ["admin", "analyst"]
        """
        role_mappings = idp_config.role_mappings or {}
        mapped = []

        for raw_role in raw_roles:
            local_role = role_mappings.get(raw_role)
            if local_role:
                mapped.append(local_role)
            else:
                # Fallback: use raw role name if no mapping
                mapped.append(raw_role.lower())

        return mapped or ["viewer"]  # Default to viewer if no roles

    @staticmethod
    async def provision_or_login_user(
        db: AsyncSession,
        tenant_id: str,
        idp_config: IdPConfig,
        extracted_claims: Dict,
    ) -> Tuple[User, bool]:
        """Provision new user or return existing user based on SSO claims.

        Returns: (user, is_new_provision)
        """
        email = extracted_claims["email"]
        idp_subject_id = extracted_claims["idp_subject_id"]

        # Check if user exists
        user = await db.scalar(
            select(User).where(User.email == email)
        )

        if user:
            # User exists: return (don't provision)
            return user, False

        # User doesn't exist
        if idp_config.provisioning_policy == UserProvisioningPolicy.REJECT:
            raise UserNotFoundError(f"User {email} not found and provisioning is REJECT")

        # JIT provisioning: create new user
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            full_name=extracted_claims.get("name"),
            tenant_id=tenant_id,
            hashed_password="sso",  # Placeholder; no local password for SSO users
            is_active=True,
        )
        db.add(user)
        await db.flush()

        # Add to tenant with default role (viewer)
        await RBACService.add_tenant_member(db, tenant_id, user.id, "viewer")

        logger.info(f"Provisioned new SSO user: {email} via {idp_config.idp_type.value}")
        return user, True

    @staticmethod
    async def create_sso_session(
        db: AsyncSession,
        user_id: str,
        tenant_id: str,
        idp_config_id: str,
        idp_subject_id: str,
        state: Optional[str] = None,
        nonce: Optional[str] = None,
        session_index: Optional[str] = None,
        expires_in_hours: int = 24,
    ) -> SSOSession:
        """Create SSO session record for logout tracking."""
        session = SSOSession(
            user_id=user_id,
            tenant_id=tenant_id,
            idp_config_id=idp_config_id,
            idp_subject_id=idp_subject_id,
            state=state,
            nonce=nonce,
            session_index=session_index,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
        )
        db.add(session)
        await db.flush()
        return session

    @staticmethod
    async def get_sso_session(
        db: AsyncSession,
        session_id: str,
    ) -> Optional[SSOSession]:
        """Get SSO session by ID."""
        return await db.scalar(
            select(SSOSession).where(SSOSession.id == session_id)
        )

    @staticmethod
    async def logout_sso_session(
        db: AsyncSession,
        session_id: str,
    ) -> bool:
        """Mark SSO session as logged out."""
        session = await SSOService.get_sso_session(db, session_id)
        if not session:
            return False

        session.logged_out_at = datetime.now(timezone.utc)
        await db.commit()
        return True

    @staticmethod
    async def complete_sso_login(
        db: AsyncSession,
        tenant_id: str,
        idp_config: IdPConfig,
        raw_claims: Dict,
    ) -> Dict:
        """Complete SSO login flow: extract claims → provision/fetch user → create session → return JWT.

        Returns: {
            'access_token': str,
            'refresh_token': str,
            'user': {...},
            'sso_session_id': str,
            'is_new_user': bool,
        }
        """
        # Extract and validate claims
        extracted = await SSOService.extract_claims(db, idp_config, raw_claims)

        # Provision or get user
        user, is_new = await SSOService.provision_or_login_user(
            db, tenant_id, idp_config, extracted
        )

        # Map roles and update user's role in tenant if needed
        mapped_roles = await SSOService.map_roles(idp_config, extracted.get("raw_roles", []))
        if mapped_roles and "viewer" not in mapped_roles:  # Don't downgrade from existing role
            primary_role = mapped_roles[0]
            await RBACService.change_user_role(db, tenant_id, user.id, primary_role)

        # Create SSO session for logout tracking
        sso_session = await SSOService.create_sso_session(
            db,
            user.id,
            tenant_id,
            idp_config.id,
            extracted["idp_subject_id"],
        )

        # Generate JWT tokens (same as local login)
        from app.services.refresh_token_service import issue_refresh_token

        access_token = create_token(
            user.id,
            user.plan.value if user.plan else "free",
            tenant_id=tenant_id,
        )
        refresh_token = await issue_refresh_token(db, user.id, tenant_id)
        await db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "tenant_id": tenant_id,
            },
            "sso_session_id": sso_session.id,
            "is_new_user": is_new,
        }
