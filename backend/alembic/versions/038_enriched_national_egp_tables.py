"""Create enriched NationalEGP landing tables.

These are raw, lossless stores of the improved enriched crawl at
H:\\procurementflow_crawl\\NationalEGP\\*_ENRICHED. Internal tables
(procurement_lifecycle, award_records_v2, app_records, econtract_execution)
are derived/enriched from these via scripts/import_enriched_national_egp.py.

Revision ID: 038_enriched_tables
"""
from alembic import op
import sqlalchemy as sa

revision = "038_enriched_tables"
down_revision = "037_award_lifecycle_trigram"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE TABLE IF NOT EXISTS enriched_app ("
        "id UUID PRIMARY KEY DEFAULT gen_random_uuid(), "
        "app_id TEXT UNIQUE, ministry TEXT, division TEXT, organization TEXT, "
        "pe_office TEXT, district TEXT, source_file TEXT, raw_json JSONB NOT NULL, "
        "fetched_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now())"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_enriched_app_app_id ON enriched_app (app_id)")

    op.execute(
        "CREATE TABLE IF NOT EXISTS enriched_awards ("
        "id UUID PRIMARY KEY DEFAULT gen_random_uuid(), "
        "tender_id TEXT, tenderer_id TEXT, package_no TEXT, agency TEXT, pe_name TEXT, "
        "pe_district TEXT, ministry_division TEXT, procurement_method TEXT, "
        "contract_value NUMERIC, date_notification_award TEXT, economic_operator TEXT, "
        "ref_no TEXT, package_name TEXT, beneficial_ownership JSONB, source_file TEXT, "
        "raw_json JSONB NOT NULL, fetched_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now())"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_enriched_awards_tender_id ON enriched_awards (tender_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_enriched_awards_package_no ON enriched_awards (package_no)")

    op.execute(
        "CREATE TABLE IF NOT EXISTS enriched_ecms ("
        "id UUID PRIMARY KEY DEFAULT gen_random_uuid(), "
        "cert_no TEXT, tender_id TEXT, package_no TEXT, package_name TEXT, pe_name TEXT, "
        "pe_office_name TEXT, organization_name TEXT, ministry_division TEXT, "
        "procurement_method TEXT, procurement_nature TEXT, contract_value NUMERIC, "
        "company_name TEXT, work_completion_status TEXT, beneficial_ownership JSONB, "
        "source TEXT, raw_json JSONB NOT NULL, fetched_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now())"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_enriched_ecms_tender_id ON enriched_ecms (tender_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_enriched_ecms_package_no ON enriched_ecms (package_no)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS enriched_ecms;")
    op.execute("DROP TABLE IF EXISTS enriched_awards;")
    op.execute("DROP TABLE IF EXISTS enriched_app;")
