"""Repair normalized_package_no keys mangled by migration 030.

Migration 030 applied its character-class filter before UPPER(), so lowercase
letters were deleted instead of folded:

    'LGED/GOBM/Bag/25-26/RW-51'  ->  'LGED/GOBM/B/25-26/RW-51'

Rows whose package_no contained lowercase therefore got a key that matches
nothing, silently dropping them from every ADR-016 join. On the current
database this affected 272,242 of 1,093,696 populated rows in
award_records_v2 (25%).

030's expression is fixed for fresh installs; this migration re-backfills
databases that already ran the broken version. It is idempotent — rows that
already hold the correct key are left untouched.

Created at: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa

revision = "042_repair_normalized_package_no"
down_revision = "041_phase2_tenders_documents_teams"
branch_labels = None
depends_on = None

TABLES = ("procurement_tenders", "app_records", "award_records_v2")


def _normalize_sql(col: str) -> str:
    """UPPER first, then strip — matches the Python normalize_package_no()."""
    return (
        f"REGEXP_REPLACE(REGEXP_REPLACE(UPPER({col}), '\\s+', '', 'g'), "
        f"'[^A-Z0-9/.\\-]', '', 'g')"
    )


def upgrade():
    norm = _normalize_sql("package_no")
    for table in TABLES:
        # Only rewrite rows that are actually wrong, so re-running is cheap and
        # correctly-populated tables are not churned.
        op.execute(
            f"""
            UPDATE {table}
               SET normalized_package_no = {norm}
             WHERE package_no IS NOT NULL
               AND package_no <> ''
               AND normalized_package_no IS DISTINCT FROM {norm}
            """
        )


def downgrade():
    # The previous values were corrupt; restoring them would reintroduce the
    # broken joins, so this is intentionally a no-op.
    pass
