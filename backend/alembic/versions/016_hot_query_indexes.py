"""Add indexes for hot query patterns identified by seq-scan audit (T-002).

Evidence (pg_stat_user_tables, 2026-07-07):
- contractor_execution_history (374K rows) had only its PK; per-contractor
  lookups (advanced_analytics, advanced_intelligence, capacity_risk) seq-scanned
  the whole table — 1,059 ms baseline for a single contractor_name filter.
- contractor_capacity / contractor_finance (36K rows each) had only their PK;
  tender_matching and advanced_intelligence join both on contractor_name
  per request.
- contractor_execution_history.package_no is joined against award_records_v2
  (advanced_analytics) — package_no is the universal join key (ADR-016).
- experience_certificate_registry (108K rows) is filtered by contractor_name
  in advanced_analytics and tender_matching; only id/certificate_no indexed.

Indexes are created CONCURRENTLY (no table locks on live traffic), which
requires running outside a transaction — hence the autocommit_block.

Revision ID: 016_hot_query_indexes
Revises: 015_staging_canonical_outputs
Create Date: 2026-07-07
"""
from __future__ import annotations

from alembic import op


revision = "016_hot_query_indexes"
down_revision = "015_staging_canonical_outputs"
branch_labels = None
depends_on = None

INDEXES = (
    ("ix_contractor_execution_history_contractor_name", "contractor_execution_history", "contractor_name"),
    ("ix_contractor_execution_history_agency_code", "contractor_execution_history", "agency_code"),
    ("ix_contractor_capacity_contractor_name", "contractor_capacity", "contractor_name"),
    ("ix_contractor_finance_contractor_name", "contractor_finance", "contractor_name"),
    ("ix_contractor_execution_history_package_no", "contractor_execution_history", "package_no"),
    ("ix_experience_certificate_registry_contractor_name", "experience_certificate_registry", "contractor_name"),
)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for name, table, column in INDEXES:
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} ON {table} ({column})"
            )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name, _table, _column in INDEXES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
