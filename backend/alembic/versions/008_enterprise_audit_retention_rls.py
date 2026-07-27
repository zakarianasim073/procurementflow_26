"""Enterprise audit, retention, webhook indexes, and tenant RLS

Revision ID: 008_enterprise
Revises: 007
Create Date: 2026-06-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "008_enterprise"
down_revision = "007a_fix_data_corruption"
branch_labels = None
depends_on = None


TENANT_TABLES = [
    "users",
    "tenders",
    "awards",
    "opening_reports",
    "agent_results",
    "agent_jobs",
    "knowledge_entries",
    "webhook_subscriptions",
    "audit_logs",
    "data_retention_policies",
    "archived_records",
]


def _create_webhook_tables_if_missing() -> None:
    op.execute(sa.text(
        """
        CREATE TABLE IF NOT EXISTS webhook_subscriptions (
            id VARCHAR(36) PRIMARY KEY,
            tenant_id VARCHAR(36),
            url TEXT NOT NULL,
            secret VARCHAR(255),
            event_types JSONB DEFAULT '[]'::jsonb,
            event_filter TEXT,
            is_active BOOLEAN NOT NULL DEFAULT true,
            is_verified BOOLEAN NOT NULL DEFAULT false,
            success_count INTEGER NOT NULL DEFAULT 0,
            failure_count INTEGER NOT NULL DEFAULT 0,
            last_status VARCHAR(20),
            last_delivered_at TIMESTAMPTZ,
            last_error TEXT,
            max_retries INTEGER NOT NULL DEFAULT 3,
            retry_interval_seconds INTEGER NOT NULL DEFAULT 60,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by VARCHAR(36)
        )
        """
    ))
    op.execute(sa.text(
        """
        CREATE TABLE IF NOT EXISTS webhook_delivery_logs (
            id VARCHAR(36) PRIMARY KEY,
            subscription_id VARCHAR(36) NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            event_id VARCHAR(100),
            payload JSONB,
            payload_size_bytes INTEGER NOT NULL DEFAULT 0,
            status_code INTEGER,
            response_body TEXT,
            response_time_ms INTEGER NOT NULL DEFAULT 0,
            attempt_number INTEGER NOT NULL DEFAULT 1,
            error_message TEXT,
            stack_trace TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    ))


def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    return bool(bind.dialect.has_table(bind, table))


def _enable_rls_if_possible(table: str) -> None:
    op.execute(sa.text(
        f"""
        DO $$
        BEGIN
            IF to_regclass('{table}') IS NOT NULL
               AND EXISTS (
                   SELECT 1 FROM information_schema.columns
                   WHERE table_schema = current_schema()
                     AND table_name = '{table}'
                     AND column_name = 'tenant_id'
               )
            THEN
                EXECUTE 'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY';
                EXECUTE 'DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}';
                EXECUTE $policy$
                    CREATE POLICY tenant_isolation_{table} ON {table}
                    USING (
                        tenant_id IS NULL
                        OR current_setting('app.tenant_id', true) = ''
                        OR tenant_id = current_setting('app.tenant_id', true)
                    )
                    WITH CHECK (
                        tenant_id IS NULL
                        OR current_setting('app.tenant_id', true) = ''
                        OR tenant_id = current_setting('app.tenant_id', true)
                    )
                $policy$;
            END IF;
        END
        $$;
        """
    ))


def _disable_rls_if_possible(table: str) -> None:
    op.execute(sa.text(
        f"""
        DO $$
        BEGIN
            IF to_regclass('{table}') IS NOT NULL THEN
                EXECUTE 'DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}';
                EXECUTE 'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY';
            END IF;
        END
        $$;
        """
    ))


def upgrade() -> None:
    _create_webhook_tables_if_missing()

    if not _table_exists("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("tenant_id", sa.String(length=36), nullable=True),
            sa.Column("actor_id", sa.String(length=36), nullable=True),
            sa.Column("actor_type", sa.String(length=50), nullable=False, server_default="user"),
            sa.Column("action", sa.String(length=120), nullable=False),
            sa.Column("resource_type", sa.String(length=100), nullable=True),
            sa.Column("resource_id", sa.String(length=120), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="success"),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("request_id", sa.String(length=64), nullable=True),
            sa.Column("trace_id", sa.String(length=64), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_audit_logs_tenant_id ON audit_logs (tenant_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_id ON audit_logs (actor_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_audit_logs_resource_type ON audit_logs (resource_type)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_audit_logs_resource_id ON audit_logs (resource_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_audit_logs_request_id ON audit_logs (request_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_audit_logs_trace_id ON audit_logs (trace_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_audit_tenant_created ON audit_logs (tenant_id, created_at)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_audit_resource ON audit_logs (resource_type, resource_id)"))

    if not _table_exists("data_retention_policies"):
        op.create_table(
            "data_retention_policies",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("tenant_id", sa.String(length=36), nullable=True),
            sa.Column("resource_type", sa.String(length=100), nullable=False),
            sa.Column("retention_days", sa.Integer(), nullable=False),
            sa.Column("archive_before_delete", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_by", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_data_retention_policies_tenant_id ON data_retention_policies (tenant_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_data_retention_policies_resource_type ON data_retention_policies (resource_type)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_retention_policy_lookup ON data_retention_policies (tenant_id, resource_type, is_active)"))

    if not _table_exists("archived_records"):
        op.create_table(
            "archived_records",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("tenant_id", sa.String(length=36), nullable=True),
            sa.Column("source_table", sa.String(length=120), nullable=False),
            sa.Column("source_id", sa.String(length=120), nullable=False),
            sa.Column("resource_type", sa.String(length=100), nullable=False),
            sa.Column("record_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("delete_after", sa.DateTime(timezone=True), nullable=True),
        )
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_records_tenant_id ON archived_records (tenant_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_records_source_table ON archived_records (source_table)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_records_source_id ON archived_records (source_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_records_resource_type ON archived_records (resource_type)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_records_delete_after ON archived_records (delete_after)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_records_tenant_resource ON archived_records (tenant_id, resource_type, archived_at)"))

    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_webhook_logs_event ON webhook_delivery_logs (event_type, created_at)"
    ))

    for table in TENANT_TABLES:
        _enable_rls_if_possible(table)


def downgrade() -> None:
    for table in reversed(TENANT_TABLES):
        _disable_rls_if_possible(table)

    op.execute(sa.text("DROP INDEX IF EXISTS ix_webhook_logs_event"))
    op.drop_table("archived_records")
    op.drop_table("data_retention_policies")
    op.drop_table("audit_logs")
