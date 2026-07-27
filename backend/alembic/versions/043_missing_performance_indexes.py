"""Add missing performance indexes for hot query paths.

Targets:
- knowledge_entries: composite (entry_type, tender_id) — most common query
- contractor_dna: indexes on win_rate, health_score, preferred_agency
- app_records: category and status indexes

Created at: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa

revision = "043_missing_performance_indexes"
down_revision = "042_repair_normalized_package_no"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # knowledge_entries: composite index for type+tender query
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_knowledge_type_tender "
        "ON knowledge_entries (entry_type, tender_id)"
    )

    # contractor_dna: indexes for filtering/sorting
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_contractor_dna_win_rate "
        "ON contractor_dna (win_rate DESC) WHERE win_rate IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_contractor_dna_health_score "
        "ON contractor_dna (health_score DESC) WHERE health_score IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_contractor_dna_preferred_agency "
        "ON contractor_dna (preferred_agency) WHERE preferred_agency IS NOT NULL"
    )

    # app_records: category and status for filtering
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_app_records_category "
        "ON app_records (category) WHERE category IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_app_records_status "
        "ON app_records (status) WHERE status IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index("idx_knowledge_type_tender", table_name="knowledge_entries")
    op.drop_index("idx_contractor_dna_win_rate", table_name="contractor_dna")
    op.drop_index("idx_contractor_dna_health_score", table_name="contractor_dna")
    op.drop_index("idx_contractor_dna_preferred_agency", table_name="contractor_dna")
    op.drop_index("idx_app_records_category", table_name="app_records")
    op.drop_index("idx_app_records_status", table_name="app_records")
