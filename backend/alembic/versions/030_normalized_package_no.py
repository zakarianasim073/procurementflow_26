"""Add normalized_package_no columns for ADR-016 join consistency.

W-010: Adds normalized_package_no column to procurement_tenders,
app_records, and award_records_v2. Backfills from existing package_no
values using SQL-level normalization (UPPER + whitespace strip).

Created at: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa

revision = "030_normalized_package_no"
down_revision = "029_regulatory_compliance_engine"


def _normalize_sql(col: str) -> sa.sql.elements.TextClause:
    """Return a SQL expression that approximates normalize_package_no().

    This is intentionally simpler than the Python normalize_package_no() —
    it strips whitespace, uppercases, removes special chars except /.-,
    and rejects pure-numeric strings (6+ digits).

    UPPER() must be applied *before* the character-class filter. Filtering
    first deletes lowercase letters outright rather than folding them, so
    'LGED/GOBM/Bag/25-26/RW-51' collapsed to 'LGED/GOBM/B/25-26/RW-51' and no
    longer matched its uppercase twin. Both Python implementations
    (import_app_to_db.normalize_package_no and
    crawler.utils.helpers.normalize_package_no) uppercase first; this now
    agrees with them.
    """
    return sa.text(
        f"REGEXP_REPLACE(REGEXP_REPLACE(UPPER({col}), '\\s+', '', 'g'), '[^A-Z0-9/.\\-]', '', 'g')"
    )


def upgrade():
    # ── procurement_tenders ──
    op.add_column(
        "procurement_tenders",
        sa.Column("normalized_package_no", sa.String(300), nullable=True),
    )
    op.execute(
        f"UPDATE procurement_tenders SET normalized_package_no = {_normalize_sql('package_no')}"
    )
    # Non-destructive: rows whose package_no cannot be normalized keep a NULL
    # normalized_package_no (they simply won't participate in cross-table joins)
    # instead of being deleted.
    op.create_index("ix_pt_normalized_package", "procurement_tenders", ["normalized_package_no"])

    # ── app_records ──
    op.add_column(
        "app_records",
        sa.Column("normalized_package_no", sa.String(300), nullable=True),
    )
    op.execute(
        f"UPDATE app_records SET normalized_package_no = {_normalize_sql('package_no')} WHERE package_no IS NOT NULL"
    )
    op.create_index("ix_ar_normalized_package", "app_records", ["normalized_package_no"])

    # ── award_records_v2 ──
    op.add_column(
        "award_records_v2",
        sa.Column("normalized_package_no", sa.String(300), nullable=True),
    )
    op.execute(
        f"UPDATE award_records_v2 SET normalized_package_no = {_normalize_sql('package_no')} WHERE package_no IS NOT NULL"
    )
    op.create_index("ix_av2_normalized_package", "award_records_v2", ["normalized_package_no"])


def downgrade():
    op.drop_index("ix_pt_normalized_package", table_name="procurement_tenders")
    op.drop_index("ix_ar_normalized_package", table_name="app_records")
    op.drop_index("ix_av2_normalized_package", table_name="award_records_v2")
    op.drop_column("procurement_tenders", "normalized_package_no")
    op.drop_column("app_records", "normalized_package_no")
    op.drop_column("award_records_v2", "normalized_package_no")
