"""Enforce tenant/RBAC context for RLS.

Revision ID: 011_enforce_tenant_rbac_context
Revises: 010_lifecycle_query_performance_indexes
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa


revision = "011_tenant_rbac"
down_revision = "010_lifecycle_perf"
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


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = :table
          AND column_name = :column
        """
    ), {"table": table, "column": column}).fetchall()
    return bool(rows)


def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    return bool(bind.dialect.has_table(bind, table))


def upgrade() -> None:
    if _table_exists("users"):
        if not _column_exists("users", "tenant_id"):
            op.add_column("users", sa.Column("tenant_id", sa.String(length=36), nullable=True))
        if not _column_exists("users", "role"):
            op.add_column("users", sa.Column("role", sa.String(length=50), nullable=False, server_default="viewer"))
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_users_tenant_id ON users (tenant_id)"))
        op.execute(sa.text("UPDATE users SET role = 'owner' WHERE is_superuser = true AND (role IS NULL OR role = 'viewer')"))

    for table in TENANT_TABLES:
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
                            OR current_setting('app.is_superuser', true) = 'true'
                            OR tenant_id = current_setting('app.tenant_id', true)
                        )
                        WITH CHECK (
                            tenant_id IS NULL
                            OR current_setting('app.is_superuser', true) = 'true'
                            OR tenant_id = current_setting('app.tenant_id', true)
                        )
                    $policy$;
                END IF;
            END
            $$;
            """
        ))


def downgrade() -> None:
    for table in TENANT_TABLES:
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
    if _table_exists("users"):
        op.execute(sa.text("DROP INDEX IF EXISTS ix_users_tenant_id"))
        if _column_exists("users", "role"):
            op.drop_column("users", "role")
        if _column_exists("users", "tenant_id"):
            op.drop_column("users", "tenant_id")
