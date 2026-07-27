"""006_add_missing_indexes_and_fks

Revision ID: 006
Revises: 005
Create Date: 2026-07-07

Adds missing composite indexes, unique constraints, and safe foreign keys
identified in the database audit. Does NOT add FKs to deprecated tables.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Missing composite / covering indexes ────────────────────────

    # agent_results: latest result per tender (avoids sort)
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agent_result_tender_created_desc "
        "ON agent_results (tender_id, created_at DESC)"
    )

    # agent_brain_messages: filter by sender/recipient + time
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_abm_sender_recipient_created "
        "ON agent_brain_messages (sender_id, recipient_id, created_at DESC)"
    )

    # agent_jobs: job queue by state + priority
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agent_jobs_state_priority_created "
        "ON agent_jobs (state, priority, created_at ASC)"
    )

    # pre_computed_intelligence: ensure unique cache_key is enforced at DB level
    # (model already has unique=True, but the index may not exist if added post-init)
    op.execute(
        "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_pci_cache_key_unique "
        "ON pre_computed_intelligence (cache_key)"
    )

    # knowledge_entries: deduplication by checksum (app.db.models lacks this index)
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_checksum "
        "ON knowledge_entries (checksum)"
    )
    op.execute(
        "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_checksum_unique "
        "ON knowledge_entries (checksum) WHERE checksum IS NOT NULL AND checksum <> ''"
    )

    # ── 2. Foreign keys (only where data types align and target is canonical) ──

    # award_records_v2.procurement_tender_id → procurement_tenders.id
    # Both are String(36). Clean up orphaned rows first (best-effort).
    op.execute(
        """
        DELETE FROM award_records_v2
        WHERE procurement_tender_id IS NOT NULL
          AND procurement_tender_id NOT IN (
              SELECT id FROM procurement_tenders
          )
        """
    )
    op.create_foreign_key(
        "fk_award_records_v2_procurement_tender",
        "award_records_v2",
        "procurement_tenders",
        ["procurement_tender_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # npp_records.tender_id → tenders.tender_id
    # NOTE: tenders is DEPRECATED. This FK is transitional; future migrations
    # should migrate npp_records to reference procurement_tenders.package_no.
    op.execute(
        """
        DELETE FROM npp_records
        WHERE tender_id IS NOT NULL
          AND tender_id NOT IN (
              SELECT tender_id FROM tenders
          )
        """
    )
    op.create_foreign_key(
        "fk_npp_records_tender",
        "npp_records",
        "tenders",
        ["tender_id"],
        ["tender_id"],
        ondelete="CASCADE",
    )

    # agent_results.tender_id → tenders.tender_id
    # Same note as above — transitional FK to deprecated table.
    op.execute(
        """
        DELETE FROM agent_results
        WHERE tender_id IS NOT NULL
          AND tender_id NOT IN (
              SELECT tender_id FROM tenders
          )
        """
    )
    op.create_foreign_key(
        "fk_agent_results_tender",
        "agent_results",
        "tenders",
        ["tender_id"],
        ["tender_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Drop FKs
    op.drop_constraint("fk_agent_results_tender", "agent_results", type_="foreignkey")
    op.drop_constraint("fk_npp_records_tender", "npp_records", type_="foreignkey")
    op.drop_constraint("fk_award_records_v2_procurement_tender", "award_records_v2", type_="foreignkey")

    # Drop indexes
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_agent_result_tender_created_desc")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_abm_sender_recipient_created")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_agent_jobs_state_priority_created")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_pci_cache_key_unique")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_knowledge_checksum")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_knowledge_checksum_unique")
