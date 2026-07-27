"""Add SSO IdP configuration and session tables (T-037)."""

from alembic import op
import sqlalchemy as sa

revision = "026_sso_idp_config_sessions"
down_revision = "025_rbac_roles_permissions"


def upgrade():
    """Create idp_configs and sso_sessions tables."""
    # IdP configuration table
    op.create_table(
        "idp_configs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("idp_type", sa.String(50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("provisioning_policy", sa.String(50), nullable=False, server_default="jit"),
        # OIDC fields
        sa.Column("oidc_discovery_url", sa.String(500), nullable=True),
        sa.Column("oidc_client_id", sa.String(255), nullable=True),
        sa.Column("oidc_client_secret", sa.Text(), nullable=True),
        sa.Column("oidc_redirect_uri", sa.String(500), nullable=True),
        sa.Column("oidc_scopes", sa.JSON(), nullable=False, server_default='["openid", "profile", "email"]'),
        # SAML fields
        sa.Column("saml_entity_id", sa.String(500), nullable=True),
        sa.Column("saml_sso_url", sa.String(500), nullable=True),
        sa.Column("saml_certificate", sa.Text(), nullable=True),
        sa.Column("saml_metadata_url", sa.String(500), nullable=True),
        # Claim and role mappings
        sa.Column("claim_mappings", sa.JSON(), nullable=False, server_default='{}'),
        sa.Column("role_mappings", sa.JSON(), nullable=False, server_default='{}'),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ),
    )
    op.create_index("ix_idp_configs_tenant_id", "idp_configs", ["tenant_id"])
    op.create_index("ix_idp_configs_enabled", "idp_configs", ["enabled"])

    # SSO session tracking table
    op.create_table(
        "sso_sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("idp_config_id", sa.String(36), nullable=False),
        # OIDC/SAML state management
        sa.Column("state", sa.String(255), nullable=True),
        sa.Column("nonce", sa.String(255), nullable=True),
        sa.Column("session_index", sa.String(255), nullable=True),
        # IdP identifiers
        sa.Column("idp_subject_id", sa.String(255), nullable=False),
        sa.Column("idp_name_id", sa.String(255), nullable=True),
        # Session lifecycle
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("logged_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ),
        sa.ForeignKeyConstraint(["idp_config_id"], ["idp_configs.id"], ),
        sa.UniqueConstraint("idp_subject_id", name="uq_sso_sessions_idp_subject_id"),
    )
    op.create_index("ix_sso_sessions_user_tenant", "sso_sessions", ["user_id", "tenant_id"])
    op.create_index("ix_sso_sessions_expires", "sso_sessions", ["expires_at"])


def downgrade():
    """Drop SSO tables."""
    op.drop_table("sso_sessions")
    op.drop_table("idp_configs")
