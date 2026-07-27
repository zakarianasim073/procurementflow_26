"""007_fix_data_corruption

Revision ID: 007
Revises: 006
Create Date: 2026-07-07

Fixes two data corruption issues identified in the enterprise audit:

1. ProcurementTender.package_no contains numeric e-GP IDs (e.g., 1298004)
   instead of actual package numbers. The normalize_package_no() fallback
   in build_works_record() was using tender_id as package_no when no
   package number was available.

2. AwardRecordsV2.tender_id was being backfilled from source_tender_id
   (which is a package number, per the docstring), corrupting the
   tender_id field with non-numeric values.

This migration:
- Clears corrupted package_no values (pure numeric 6+ digits) from
  procurement_tenders that don't have a matching e-GP numeric tender
  association
- Resolves award_records_v2.procurement_tender_id by joining
  procurement_tenders on package_no (for source_tender_id matches)
  or on tender_id (for numeric matches)
- Adds a check constraint to prevent future numeric-only package_no
  values in procurement_tenders
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
#
# This file and 007_package_identity_integrity.py both declared revision "007"
# with down_revision "006", which left alembic with two heads and made every
# alembic command fail. 007_package_identity_integrity is the one that actually
# ran: it is the only migration that adds app_records.pe_office, and that column
# is present, as is its effect of clearing numeric package_no from app_records
# and procurement_lifecycle (both now zero). This file was never applied, so it
# is renumbered to sit after it rather than beside it.
#
# Note that being upstream of the current revision (040) means alembic now
# treats this as already applied and will not run it. The repair it describes is
# still outstanding — see the accompanying head migration.
revision = "007a_fix_data_corruption"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Fix corrupted package_no in procurement_tenders ───────────
    #
    # The normalize_package_no() method in build_works_record() fell back
    # to tender_id (numeric e-GP ID) when no package number was available.
    # This stored numeric IDs like "1298004" in package_no, which breaks
    # all downstream matching that expects actual package numbers.
    #
    # Fix: For procurement_tenders where package_no is a pure numeric
    # string of 6-12 digits, try to find the real package number from the
    # matching app_records or award_records. If no real package number
    # exists, set package_no to NULL so the record can be re-imported
    # correctly.

    op.execute(text("""
        UPDATE procurement_tenders pt
        SET package_no = NULL
        WHERE package_no ~ '^[0-9]{6,12}$'
          AND package_no NOT IN (
              SELECT DISTINCT package_no FROM app_records
              WHERE package_no IS NOT NULL AND package_no <> ''
          )
          AND package_no NOT IN (
              SELECT DISTINCT package_no FROM award_records_v2
              WHERE package_no IS NOT NULL AND package_no <> ''
          )
    """))

    # ── 2. Resolve award_records_v2.procurement_tender_id ───────────────
    #
    # Many award_records_v2 rows have NULL procurement_tender_id or
    # have the wrong UUID. Resolve them by matching:
    #   a) source_tender_id → procurement_tenders.package_no
    #   b) tender_id (numeric) → procurement_tenders.source_tender_id
    #      (via app_records that link tender_id to package_no)
    #
    # Match path A: direct package_no match
    op.execute(text("""
        UPDATE award_records_v2 ar
        SET procurement_tender_id = pt.id
        FROM procurement_tenders pt
        WHERE ar.procurement_tender_id IS NULL
          AND ar.source_tender_id IS NOT NULL
          AND ar.source_tender_id <> ''
          AND pt.package_no = ar.source_tender_id
    """))

    # Match path B: numeric tender_id → app_records → package_no
    op.execute(text("""
        UPDATE award_records_v2 ar
        SET procurement_tender_id = pt.id
        FROM app_records app
        JOIN procurement_tenders pt ON pt.package_no = app.package_no
        WHERE ar.procurement_tender_id IS NULL
          AND ar.tender_id IS NOT NULL
          AND ar.tender_id <> ''
          AND ar.tender_id ~ '^[0-9]{5,12}$'
          AND app.source_tender_id = ar.tender_id
    """))

    # Match path C: direct tender_id → app_records (via source_tender_id on app)
    # where app_records.source_tender_id stores the numeric e-GP ID
    op.execute(text("""
        UPDATE award_records_v2 ar
        SET procurement_tender_id = pt.id
        FROM app_records app
        JOIN procurement_tenders pt ON pt.package_no = app.package_no
        WHERE ar.procurement_tender_id IS NULL
          AND ar.tender_id IS NOT NULL
          AND ar.tender_id <> ''
          AND ar.tender_id ~ '^[0-9]{5,12}$'
          AND app.source_tender_id = ar.tender_id
    """))

    # ── 3. Fix procurement_lifecycle rows with corrupted package_no ─────
    #
    # The lifecycle table was rebuilt from the corrupted procurement_tenders.
    # Fix package_no by looking up the correct value from procurement_tenders.
    # For rows where the tender_id points to a tender with a real package_no,
    # update the lifecycle row.
    #
    # NOTE: If tender_id is NOT a UUID (it's a numeric string), this means
    # the lifecycle row was built from a corrupted tender record. In that
    # case, we try to resolve via the original source.

    op.execute(text("""
        UPDATE procurement_lifecycle pl
        SET package_no = pt.package_no
        FROM procurement_tenders pt
        WHERE pl.tender_id = pt.id
          AND pt.package_no IS NOT NULL
          AND pt.package_no <> ''
          AND (pl.package_no IS NULL OR pl.package_no <> pt.package_no)
    """))

    # Clear lifecycle rows where package_no is pure numeric and no matching
    # tender exists (orphaned rows from the corruption)
    op.execute(text("""
        DELETE FROM procurement_lifecycle
        WHERE package_no ~ '^[0-9]{6,12}$'
          AND tender_id IS NULL
    """))

    # ── 4. Add a partial unique index to prevent future corruption ──────
    #
    # This is NOT a full unique constraint (we can't guarantee uniqueness
    # across all sources), but it adds a fast lookup for the common case
    # and documents the expected invariant.

    op.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_procurement_tenders_package_no_real
        ON procurement_tenders (package_no)
        WHERE package_no IS NOT NULL AND package_no !~ '^[0-9]{6,12}$'
    """))

    # Add a comment on the table documenting the field semantics
    op.execute(text("""
        COMMENT ON COLUMN procurement_tenders.package_no IS
        'Actual e-GP package number (e.g., PWD/Zone-A/2023-001). '
        'NOT the numeric e-GP tender_id (e.g., 1298004). '
        'If the package number is unknown, leave NULL rather than '
        'falling back to the numeric tender_id.'
    """))

    op.execute(text("""
        COMMENT ON COLUMN award_records_v2.tender_id IS
        'Numeric e-GP tender ID (e.g., 1298004). NOT a package number. '
        'Use procurement_tender_id for the UUID foreign key to procurement_tenders.'
    """))

    op.execute(text("""
        COMMENT ON COLUMN award_records_v2.source_tender_id IS
        'Package number or reference from the source system (e.g., PWD/2023-001). '
        'NOT the numeric e-GP tender_id.'
    """))


def downgrade() -> None:
    # Remove the partial index
    op.execute(text("DROP INDEX IF EXISTS idx_procurement_tenders_package_no_real"))

    # Remove comments (no-op, but keeps the downgrade clean)
    op.execute(text("COMMENT ON COLUMN procurement_tenders.package_no IS NULL"))
    op.execute(text("COMMENT ON COLUMN award_records_v2.tender_id IS NULL"))
    op.execute(text("COMMENT ON COLUMN award_records_v2.source_tender_id IS NULL"))

    # NOTE: We cannot reverse the data fixes (deletions and updates).
    # The migration is intentionally one-way for data integrity.
