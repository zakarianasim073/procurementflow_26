"""Lifecycle query performance indexes.

Revision ID: 010_lifecycle_query_performance_indexes
Revises: 009_search_competitor_performance_indexes
Create Date: 2026-07-01
"""
from alembic import op


revision = "010_lifecycle_perf"
down_revision = "009_search_perf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pl_award_date_package "
        "ON procurement_lifecycle (award_date DESC NULLS LAST, package_no)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pl_agency_zone_award "
        "ON procurement_lifecycle (agency_code, zone_name, award_date DESC NULLS LAST)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_procurement_tenders_package_no "
        "ON procurement_tenders (package_no)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_app_records_procurement_tender_id "
        "ON app_records (procurement_tender_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_live_tender_sources_procurement_tender_id "
        "ON live_tender_sources (procurement_tender_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_award_records_v2_procurement_tender_id "
        "ON award_records_v2 (procurement_tender_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_opening_reports_tender_id "
        "ON opening_reports (tender_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_opening_reports_tender_id")
    op.execute("DROP INDEX IF EXISTS ix_award_records_v2_procurement_tender_id")
    op.execute("DROP INDEX IF EXISTS ix_live_tender_sources_procurement_tender_id")
    op.execute("DROP INDEX IF EXISTS ix_app_records_procurement_tender_id")
    op.execute("DROP INDEX IF EXISTS ix_procurement_tenders_package_no")
    op.execute("DROP INDEX IF EXISTS ix_pl_agency_zone_award")
    op.execute("DROP INDEX IF EXISTS ix_pl_award_date_package")
