"""ENT-03: tamper-evident audit trail (hash chain + append-only enforcement).

Adds previous_hash/entry_hash columns to audit_logs and a BEFORE UPDATE/DELETE
trigger that forbids mutating audit rows, making the log truly append-only for
PPR/government compliance.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '033'
down_revision = '032'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "audit_logs",
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "audit_logs",
        sa.Column("entry_hash", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_audit_entry_hash", "audit_logs", ["entry_hash"])

    # Append-only enforcement: any UPDATE or DELETE on an audit row is rejected.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION reject_audit_mutate()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only; updates and deletes are forbidden'
                USING ERRCODE = '42501';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS audit_logs_append_only ON audit_logs;
        CREATE TRIGGER audit_logs_append_only
            BEFORE UPDATE OR DELETE ON audit_logs
            FOR EACH ROW EXECUTE FUNCTION reject_audit_mutate();
        """
    )


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS audit_logs_append_only ON audit_logs;")
    op.execute("DROP FUNCTION IF EXISTS reject_audit_mutate();")
    op.drop_index("ix_audit_entry_hash", table_name="audit_logs")
    op.drop_column("audit_logs", "entry_hash")
    op.drop_column("audit_logs", "previous_hash")
