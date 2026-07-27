"""Add performance indexes for T-018.

Adds 44 indexes across 12 tables:
- 33 single-column indexes (FK, tenant_id, common filters)
- 8 composite indexes (multi-column lookups)
- 3 full-text search indexes
"""

revision = "027"
down_revision = "026_sso_idp_config_sessions"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    """Add performance indexes."""

    # ── Single-column indexes ────────────────────────────────────────────

    # users table
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_is_active", "users", ["is_active"])

    # tenants table
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)
    op.create_index("ix_tenants_plan", "tenants", ["plan"])
    op.create_index("ix_tenants_is_active", "tenants", ["is_active"])

    # tenant_members table
    op.create_index("ix_tenant_members_tenant_id", "tenant_members", ["tenant_id"])
    op.create_index("ix_tenant_members_user_id", "tenant_members", ["user_id"])
    op.create_index("ix_tenant_members_role_id", "tenant_members", ["role_id"])

    # roles table
    op.create_index("ix_roles_tenant_id", "roles", ["tenant_id"])
    op.create_index("ix_roles_is_system", "roles", ["is_system"])

    # permissions table
    op.create_index("ix_permissions_resource", "permissions", ["resource"])
    op.create_index("ix_permissions_action", "permissions", ["action"])

    # client_subscriptions table
    op.create_index("ix_client_subscriptions_tenant_id", "client_subscriptions", ["tenant_id"])
    op.create_index("ix_client_subscriptions_status", "client_subscriptions", ["status"])

    # audit_events table
    op.create_index("ix_audit_events_tenant_id", "audit_events", ["tenant_id"])
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    # webhook_subscriptions table
    op.create_index("ix_webhook_subscriptions_tenant_id", "webhook_subscriptions", ["tenant_id"])
    op.create_index("ix_webhook_subscriptions_is_active", "webhook_subscriptions", ["is_active"])

    # idp_configs table
    op.create_index("ix_idp_configs_tenant_id", "idp_configs", ["tenant_id"])
    op.create_index("ix_idp_configs_enabled", "idp_configs", ["enabled"])

    # sso_sessions table
    op.create_index("ix_sso_sessions_user_id", "sso_sessions", ["user_id"])
    op.create_index("ix_sso_sessions_tenant_id", "sso_sessions", ["tenant_id"])
    op.create_index("ix_sso_sessions_expires_at", "sso_sessions", ["expires_at"])

    # procurement_tenders table
    op.create_index("ix_procurement_tenders_agency_code", "procurement_tenders", ["agency_code"])
    op.create_index("ix_procurement_tenders_zone_id", "procurement_tenders", ["zone_id"])
    op.create_index("ix_procurement_tenders_created_at", "procurement_tenders", ["created_at"])

    # tender_awards table
    op.create_index("ix_tender_awards_tender_id", "tender_awards", ["tender_id"])
    op.create_index("ix_tender_awards_contractor_id", "tender_awards", ["contractor_id"])
    op.create_index("ix_tender_awards_award_date", "tender_awards", ["award_date"])

    # contractor_profiles table
    op.create_index("ix_contractor_profiles_contractor_id", "contractor_profiles", ["contractor_id"])
    op.create_index("ix_contractor_profiles_completion_rate", "contractor_profiles", ["completion_rate_pct"])

    # ── Composite indexes (multi-column) ────────────────────────────────

    op.create_index(
        "ix_tenant_members_tenant_user",
        "tenant_members",
        ["tenant_id", "user_id"],
    )
    op.create_index(
        "ix_tenant_members_tenant_role",
        "tenant_members",
        ["tenant_id", "role_id"],
    )
    op.create_index(
        "ix_audit_events_tenant_created",
        "audit_events",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_audit_events_actor_created",
        "audit_events",
        ["actor_id", "created_at"],
    )
    op.create_index(
        "ix_webhook_subscriptions_tenant_type",
        "webhook_subscriptions",
        ["tenant_id", "event_type"],
    )
    op.create_index(
        "ix_sso_sessions_user_tenant",
        "sso_sessions",
        ["user_id", "tenant_id"],
    )
    op.create_index(
        "ix_procurement_tenders_agency_zone",
        "procurement_tenders",
        ["agency_code", "zone_id"],
    )
    op.create_index(
        "ix_tender_awards_tender_contractor",
        "tender_awards",
        ["tender_id", "contractor_id"],
    )

    # ── Full-text search indexes ────────────────────────────────────────

    # Only add if table has the columns
    try:
        op.execute(
            "CREATE INDEX ix_procurement_tenders_title_fts ON procurement_tenders "
            "USING GIN(to_tsvector('english', title))"
        )
    except Exception:
        pass  # Column may not exist or DB doesn't support GIN

    try:
        op.execute(
            "CREATE INDEX ix_procurement_tenders_description_fts ON procurement_tenders "
            "USING GIN(to_tsvector('english', description))"
        )
    except Exception:
        pass

    try:
        op.execute(
            "CREATE INDEX ix_contractor_profiles_name_fts ON contractor_profiles "
            "USING GIN(to_tsvector('english', contractor_name))"
        )
    except Exception:
        pass


def downgrade():
    """Remove performance indexes."""

    # Single-column indexes
    op.drop_index("ix_users_tenant_id")
    op.drop_index("ix_users_email")
    op.drop_index("ix_users_is_active")
    op.drop_index("ix_tenants_slug")
    op.drop_index("ix_tenants_plan")
    op.drop_index("ix_tenants_is_active")
    op.drop_index("ix_tenant_members_tenant_id")
    op.drop_index("ix_tenant_members_user_id")
    op.drop_index("ix_tenant_members_role_id")
    op.drop_index("ix_roles_tenant_id")
    op.drop_index("ix_roles_is_system")
    op.drop_index("ix_permissions_resource")
    op.drop_index("ix_permissions_action")
    op.drop_index("ix_client_subscriptions_tenant_id")
    op.drop_index("ix_client_subscriptions_status")
    op.drop_index("ix_audit_events_tenant_id")
    op.drop_index("ix_audit_events_actor_id")
    op.drop_index("ix_audit_events_created_at")
    op.drop_index("ix_webhook_subscriptions_tenant_id")
    op.drop_index("ix_webhook_subscriptions_is_active")
    op.drop_index("ix_idp_configs_tenant_id")
    op.drop_index("ix_idp_configs_enabled")
    op.drop_index("ix_sso_sessions_user_id")
    op.drop_index("ix_sso_sessions_tenant_id")
    op.drop_index("ix_sso_sessions_expires_at")
    op.drop_index("ix_procurement_tenders_agency_code")
    op.drop_index("ix_procurement_tenders_zone_id")
    op.drop_index("ix_procurement_tenders_created_at")
    op.drop_index("ix_tender_awards_tender_id")
    op.drop_index("ix_tender_awards_contractor_id")
    op.drop_index("ix_tender_awards_award_date")
    op.drop_index("ix_contractor_profiles_contractor_id")
    op.drop_index("ix_contractor_profiles_completion_rate")

    # Composite indexes
    op.drop_index("ix_tenant_members_tenant_user")
    op.drop_index("ix_tenant_members_tenant_role")
    op.drop_index("ix_audit_events_tenant_created")
    op.drop_index("ix_audit_events_actor_created")
    op.drop_index("ix_webhook_subscriptions_tenant_type")
    op.drop_index("ix_sso_sessions_user_tenant")
    op.drop_index("ix_procurement_tenders_agency_zone")
    op.drop_index("ix_tender_awards_tender_contractor")

    # Full-text indexes
    op.drop_index("ix_procurement_tenders_title_fts", table_name="procurement_tenders")
    op.drop_index("ix_procurement_tenders_description_fts", table_name="procurement_tenders")
    op.drop_index("ix_contractor_profiles_name_fts", table_name="contractor_profiles")
