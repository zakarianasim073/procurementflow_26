"""Search and competitor performance indexes

Revision ID: 009_search_competitor_performance_indexes
Revises: 008_enterprise_audit_retention_rls
Create Date: 2026-06-30
"""

from alembic import op


revision = "009_search_perf"
down_revision = "008_enterprise"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_lifecycle_title_package_fts
        ON procurement_lifecycle
        USING gin (to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(package_no, '')))
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_lifecycle_agency_award_date
        ON procurement_lifecycle (agency_code, award_date DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_arv2_contractor_amount
        ON award_records_v2 (contractor_name, amount_bdt DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_arv2_district_amount
        ON award_records_v2 (district, amount_bdt DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_arv2_agency_amount
        ON award_records_v2 (agency_code, amount_bdt DESC)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_arv2_agency_amount")
    op.execute("DROP INDEX IF EXISTS idx_arv2_district_amount")
    op.execute("DROP INDEX IF EXISTS idx_arv2_contractor_amount")
    op.execute("DROP INDEX IF EXISTS idx_lifecycle_agency_award_date")
    op.execute("DROP INDEX IF EXISTS idx_lifecycle_title_package_fts")
