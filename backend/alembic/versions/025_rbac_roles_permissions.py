"""T-035 (ENT-01a): RBAC tables — permissions, roles, tenant members.

Revision ID: 025_rbac_roles_permissions
Revises: 024_merge_tender_models
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa

revision = "025_rbac_roles_permissions"
down_revision = "024_merge_tender_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Permissions table: granular resource:action permissions
    op.create_table(
        "permissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("resource", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_permissions_resource_action", "permissions", ["resource", "action"])

    # Roles table: role with set of permission IDs (JSON list)
    op.create_table(
        "roles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=True, index=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_system", sa.Boolean, default=False, nullable=False),
        sa.Column("permission_ids", sa.JSON, default=list, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_roles_tenant_id", "roles", ["tenant_id"])
    op.create_index("ix_roles_name", "roles", ["name"])

    # TenantMember table: user + tenant + role membership
    op.create_table(
        "tenant_members",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("role_id", sa.String(length=36), sa.ForeignKey("roles.id"), nullable=False, index=True),
        sa.Column("is_owner", sa.Boolean, default=False, nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_tenant_members_user_tenant", "tenant_members", ["user_id", "tenant_id"])
    op.create_index("ix_tenant_members_tenant_role", "tenant_members", ["tenant_id", "role_id"])


def downgrade() -> None:
    op.drop_index("ix_tenant_members_tenant_role", table_name="tenant_members")
    op.drop_index("ix_tenant_members_user_tenant", table_name="tenant_members")
    op.drop_table("tenant_members")
    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_index("ix_roles_tenant_id", table_name="roles")
    op.drop_table("roles")
    op.drop_index("ix_permissions_resource_action", table_name="permissions")
    op.drop_table("permissions")
