"""007_package_identity_integrity

Revision ID: 007
Revises: 006
Create Date: 2026-06-30

Enforce package_no as the procurement business key and keep numeric e-GP
tender IDs in tender_id/source_tender_id columns only.
"""
from alembic import op


revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE app_records ADD COLUMN IF NOT EXISTS package_no VARCHAR(300)")
    op.execute("ALTER TABLE app_records ADD COLUMN IF NOT EXISTS pe_office VARCHAR(300)")
    op.execute(
        """
        UPDATE app_records a
        SET package_no = p.package_no
        FROM procurement_tenders p
        WHERE a.procurement_tender_id = p.id
          AND (a.package_no IS NULL OR a.package_no = '')
        """
    )

    # Nullable package columns can be safely cleared when they contain only
    # numeric e-GP IDs; the true ID remains available in tender_id fields.
    op.execute("UPDATE award_records_v2 SET package_no = NULL WHERE package_no ~ '^[0-9]{6,}$'")
    op.execute("UPDATE app_records SET package_no = NULL WHERE package_no ~ '^[0-9]{6,}$'")
    op.execute("UPDATE eexperience_completed SET package_no = NULL WHERE package_no ~ '^[0-9]{6,}$'")
    op.execute("UPDATE ecms_ongoing SET package_no = NULL WHERE package_no ~ '^[0-9]{6,}$'")
    op.execute("UPDATE econtract_execution SET package_no = NULL WHERE package_no ~ '^[0-9]{6,}$'")

    # Lifecycle package_no is non-null in the model; remove unusable numeric
    # rows and dedupe before enforcing uniqueness.
    op.execute("DELETE FROM procurement_lifecycle WHERE package_no ~ '^[0-9]{6,}$'")
    op.execute(
        """
        DELETE FROM procurement_lifecycle a
        USING procurement_lifecycle b
        WHERE a.package_no = b.package_no
          AND a.id <> b.id
          AND (
              COALESCE(a.updated_at, a.created_at) < COALESCE(b.updated_at, b.created_at)
              OR (
                  COALESCE(a.updated_at, a.created_at) = COALESCE(b.updated_at, b.created_at)
                  AND a.id < b.id
              )
          )
        """
    )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_lifecycle_package_no "
        "ON procurement_lifecycle (package_no)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_award_records_v2_package_no "
        "ON award_records_v2 (package_no)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_app_records_package_no "
        "ON app_records (package_no)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_procurement_tenders_package_no "
        "ON procurement_tenders (package_no)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_procurement_tenders_package_no")
    op.execute("DROP INDEX IF EXISTS idx_app_records_package_no")
    op.execute("DROP INDEX IF EXISTS idx_award_records_v2_package_no")
    op.execute("DROP INDEX IF EXISTS uq_lifecycle_package_no")
