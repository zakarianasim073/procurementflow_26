"""SSO endpoints: OIDC and SAML configuration and login (T-037)."""

from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.db.base import get_async_session as get_db
from app.models.user import User
from app.models.sso import IdPConfig, IdPType, UserProvisioningPolicy
from app.models.enterprise import Tenant, TenantMember
from app.services.sso_service import SSOService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sso", tags=["sso"])


# Pydantic models
class ClaimMappingSchema(BaseModel):
    """Claim mapping configuration."""
    email: str = "email"
    name: str = "name"
    tenant: Optional[str] = "org_id"
    roles: str = "groups"


class RoleMappingSchema(BaseModel):
    """Role mapping configuration."""
    idp_group: str = Field(..., description="IdP group name")
    local_role: str = Field(..., description="Local role (admin, analyst, viewer)")


class OIDCConfigSchema(BaseModel):
    """OIDC-specific configuration."""
    discovery_url: str
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: list[str] = ["openid", "profile", "email"]


class SAMLConfigSchema(BaseModel):
    """SAML-specific configuration."""
    entity_id: str
    sso_url: str
    certificate: str
    metadata_url: Optional[str] = None


class IdPConfigCreateRequest(BaseModel):
    """Create or update IdP configuration."""
    name: str
    idp_type: IdPType
    enabled: bool = True
    provisioning_policy: UserProvisioningPolicy = UserProvisioningPolicy.JIT
    oidc_config: Optional[OIDCConfigSchema] = None
    saml_config: Optional[SAMLConfigSchema] = None
    claim_mappings: Optional[dict] = None
    role_mappings: Optional[dict] = None


class IdPConfigResponse(BaseModel):
    """IdP configuration response."""
    id: str
    tenant_id: str
    name: str
    idp_type: str
    enabled: bool
    provisioning_policy: str
    created_at: str
    updated_at: str


class OIDCCallbackRequest(BaseModel):
    """OIDC callback parameters."""
    code: str
    state: str
    error: Optional[str] = None
    error_description: Optional[str] = None


class SAMLCallbackRequest(BaseModel):
    """SAML callback parameters."""
    saml_response: str = Field(..., description="Base64-encoded SAML response")
    relay_state: Optional[str] = None


class SSOLoginResponse(BaseModel):
    """SSO login response with tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict
    sso_session_id: str
    is_new_user: bool


# Endpoints


@router.post("/idp-configs", response_model=IdPConfigResponse)
async def create_idp_config(
    request_data: IdPConfigCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create IdP configuration for tenant (admin only)."""
    # Verify user is tenant owner
    tenant = await db.scalar(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Check user is owner (simplified; use RBAC in production)
    member = await db.scalar(
        select(TenantMember).where(
            (TenantMember.tenant_id == current_user.tenant_id)
            & (TenantMember.user_id == current_user.id)
        )
    )
    if not member or not member.is_owner:
        raise HTTPException(status_code=403, detail="Only tenant owners can manage IdP configs")

    # Validate configuration based on type
    if request_data.idp_type == IdPType.OIDC:
        if not request_data.oidc_config:
            raise HTTPException(status_code=400, detail="OIDC config required for OIDC type")
        oidc = request_data.oidc_config

        idp = IdPConfig(
            tenant_id=current_user.tenant_id,
            name=request_data.name,
            idp_type=IdPType.OIDC,
            enabled=request_data.enabled,
            provisioning_policy=request_data.provisioning_policy,
            oidc_discovery_url=oidc.discovery_url,
            oidc_client_id=oidc.client_id,
            oidc_client_secret=oidc.client_secret,
            oidc_redirect_uri=oidc.redirect_uri,
            oidc_scopes=oidc.scopes,
            claim_mappings=request_data.claim_mappings or {},
            role_mappings=request_data.role_mappings or {},
        )
    elif request_data.idp_type == IdPType.SAML:
        if not request_data.saml_config:
            raise HTTPException(status_code=400, detail="SAML config required for SAML type")
        saml = request_data.saml_config

        idp = IdPConfig(
            tenant_id=current_user.tenant_id,
            name=request_data.name,
            idp_type=IdPType.SAML,
            enabled=request_data.enabled,
            provisioning_policy=request_data.provisioning_policy,
            saml_entity_id=saml.entity_id,
            saml_sso_url=saml.sso_url,
            saml_certificate=saml.certificate,
            saml_metadata_url=saml.metadata_url,
            claim_mappings=request_data.claim_mappings or {},
            role_mappings=request_data.role_mappings or {},
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported IdP type")

    db.add(idp)
    await db.commit()
    await db.refresh(idp)

    logger.info(f"Created IdP config: {request_data.name} for tenant {current_user.tenant_id}")
    return {
        "id": idp.id,
        "tenant_id": idp.tenant_id,
        "name": idp.name,
        "idp_type": idp.idp_type.value,
        "enabled": idp.enabled,
        "provisioning_policy": idp.provisioning_policy.value,
        "created_at": idp.created_at.isoformat() if idp.created_at else None,
        "updated_at": idp.updated_at.isoformat() if idp.updated_at else None,
    }


@router.get("/idp-configs", response_model=list[IdPConfigResponse])
async def list_idp_configs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List IdP configurations for tenant."""
    configs = await SSOService.list_idp_configs(db, current_user.tenant_id)
    return [
        {
            "id": cfg.id,
            "tenant_id": cfg.tenant_id,
            "name": cfg.name,
            "idp_type": cfg.idp_type.value,
            "enabled": cfg.enabled,
            "provisioning_policy": cfg.provisioning_policy.value,
            "created_at": cfg.created_at.isoformat(),
            "updated_at": cfg.updated_at.isoformat(),
        }
        for cfg in configs
    ]


@router.get("/idp-configs/{idp_id}", response_model=IdPConfigResponse)
async def get_idp_config(
    idp_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get IdP configuration details."""
    config = await db.scalar(
        select(IdPConfig).where(
            (IdPConfig.id == idp_id) & (IdPConfig.tenant_id == current_user.tenant_id)
        )
    )
    if not config:
        raise HTTPException(status_code=404, detail="IdP config not found")

    return {
        "id": config.id,
        "tenant_id": config.tenant_id,
        "name": config.name,
        "idp_type": config.idp_type.value,
        "enabled": config.enabled,
        "provisioning_policy": config.provisioning_policy.value,
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat(),
    }


@router.post("/oidc/init")
async def oidc_init(
    idp_id: str,
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Initialize OIDC login flow (return authorization URL)."""
    idp = await SSOService.get_idp_config(db, tenant_id, idp_id)
    if not idp or idp.idp_type != IdPType.OIDC:
        raise HTTPException(status_code=404, detail="OIDC config not found")

    state = SSOService.generate_oidc_state()
    nonce = SSOService.generate_nonce()

    # In production, store state/nonce in Redis or DB for validation
    # For now, return them to client for callback validation
    return {
        "state": state,
        "nonce": nonce,
        "authorization_url": f"{idp.oidc_discovery_url}/authorize?client_id={idp.oidc_client_id}&redirect_uri={idp.oidc_redirect_uri}&response_type=code&scope={'+'.join(idp.oidc_scopes)}&state={state}&nonce={nonce}",
    }


@router.post("/oidc/callback", response_model=SSOLoginResponse)
async def oidc_callback(
    request_data: OIDCCallbackRequest,
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """OIDC callback handler (exchange code for tokens)."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="SSO authentication is not available",
    )


@router.post("/saml/acs", response_model=SSOLoginResponse)
async def saml_acs(
    request_data: SAMLCallbackRequest,
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """SAML Assertion Consumer Service (callback handler)."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="SSO authentication is not available",
    )


@router.post("/logout")
async def sso_logout(
    sso_session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Logout from SSO session."""
    success = await SSOService.logout_sso_session(db, sso_session_id)
    if not success:
        raise HTTPException(status_code=404, detail="SSO session not found")

    return {"message": "Logged out successfully"}
