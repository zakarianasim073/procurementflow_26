"""SSO configuration models: OIDC and SAML (T-037)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List
from enum import Enum

from sqlalchemy import Boolean, DateTime, Index, JSON, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IdPType(str, Enum):
    """Identity provider type."""
    OIDC = "oidc"
    SAML = "saml"


class UserProvisioningPolicy(str, Enum):
    """How to handle unknown users during SSO login."""
    REJECT = "reject"  # Reject login if user doesn't exist (strict)
    JIT = "jit"  # Just-in-time provision new user (lenient)


class IdPConfig(Base):
    """Identity provider configuration per tenant (OIDC or SAML)."""

    __tablename__ = "idp_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g., "Azure AD", "Keycloak"
    idp_type: Mapped[IdPType] = mapped_column(String(50), nullable=False)

    # Common fields
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    provisioning_policy: Mapped[UserProvisioningPolicy] = mapped_column(
        String(50), default=UserProvisioningPolicy.JIT, nullable=False
    )

    # OIDC-specific
    oidc_discovery_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    oidc_client_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    oidc_client_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Encrypted in practice
    oidc_redirect_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    oidc_scopes: Mapped[List[str]] = mapped_column(JSON, default=lambda: ["openid", "profile", "email"], nullable=False)

    # SAML-specific
    saml_entity_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    saml_sso_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    saml_certificate: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    saml_metadata_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Claim mapping: how to extract tenant + role + email from IdP claims
    claim_mappings: Mapped[Dict] = mapped_column(
        JSON,
        default=lambda: {
            "email": "email",  # IdP claim → user email
            "name": "name",    # IdP claim → user full name
            "tenant": "org_id",  # IdP claim → tenant ID (if multi-tenant IdP)
            "roles": "groups",  # IdP claim → role list
        },
        nullable=False
    )

    # Advanced: role mapping (IdP group → local role)
    role_mappings: Mapped[Dict[str, str]] = mapped_column(
        JSON,
        default=lambda: {
            "IdP_Admins": "admin",
            "IdP_Analysts": "analyst",
            "IdP_Viewers": "viewer",
        },
        nullable=False
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_idp_configs_tenant_id", "tenant_id"),
        Index("ix_idp_configs_enabled", "enabled"),
    )


class SSOSession(Base):
    """Track SSO sessions for logout and state management."""

    __tablename__ = "sso_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    idp_config_id: Mapped[str] = mapped_column(String(36), ForeignKey("idp_configs.id"), nullable=False)

    # OIDC/SAML state management
    state: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # OAuth state param (OIDC)
    nonce: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Nonce (OIDC)
    session_index: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # SessionIndex (SAML)

    # IdP identifiers
    idp_subject_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)  # IdP's unique user ID
    idp_name_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # SAML NameID

    # Session lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    logged_out_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_sso_sessions_user_tenant", "user_id", "tenant_id"),
        Index("ix_sso_sessions_expires", "expires_at"),
    )
