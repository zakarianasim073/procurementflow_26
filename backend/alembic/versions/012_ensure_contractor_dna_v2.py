"""Ensure contractor_dna_v2 exists for opening-report DNA.

Revision ID: 012_cdna_v2
Revises: 011_tenant_rbac
Create Date: 2026-07-01
"""
from alembic import op


revision = "012_cdna_v2"
down_revision = "011_tenant_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS contractor_dna_v2 (
            id VARCHAR(36) PRIMARY KEY,
            contractor_id VARCHAR(36) NOT NULL UNIQUE,
            contractor_name VARCHAR(300) NOT NULL,
            total_bids INTEGER DEFAULT 0,
            total_wins INTEGER DEFAULT 0,
            win_rate DOUBLE PRECISION DEFAULT 0.0,
            avg_discount DOUBLE PRECISION DEFAULT 0.0,
            discount_stddev DOUBLE PRECISION DEFAULT 0.0,
            avg_rank DOUBLE PRECISION DEFAULT 0.0,
            responsive_rate DOUBLE PRECISION DEFAULT 0.0,
            slt_rate DOUBLE PRECISION DEFAULT 0.0,
            non_responsive_rate DOUBLE PRECISION DEFAULT 0.0,
            agency_affinity JSONB DEFAULT '{}'::jsonb,
            zone_affinity JSONB DEFAULT '{}'::jsonb,
            project_type_affinity JSONB DEFAULT '{}'::jsonb,
            total_award_amount_bdt DOUBLE PRECISION DEFAULT 0.0,
            avg_award_amount_bdt DOUBLE PRECISION DEFAULT 0.0,
            nppi_score DOUBLE PRECISION DEFAULT 0.0,
            aggression_index DOUBLE PRECISION DEFAULT 0.0,
            reliability_index DOUBLE PRECISION DEFAULT 0.0,
            adaptation_score DOUBLE PRECISION DEFAULT 0.0,
            health_score DOUBLE PRECISION DEFAULT 0.0,
            last_rebuilt_at TIMESTAMP NULL,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_cdna_v2_contractor_id ON contractor_dna_v2 (contractor_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cdna_v2_name ON contractor_dna_v2 (contractor_name)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cdna_v2_win_rate_desc ON contractor_dna_v2 (win_rate DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cdna_v2_total_bids_desc ON contractor_dna_v2 (total_bids DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cdna_v2_agency_affinity ON contractor_dna_v2 USING gin (agency_affinity)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cdna_v2_zone_affinity ON contractor_dna_v2 USING gin (zone_affinity)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_cdna_v2_zone_affinity")
    op.execute("DROP INDEX IF EXISTS ix_cdna_v2_agency_affinity")
    op.execute("DROP INDEX IF EXISTS ix_cdna_v2_total_bids_desc")
    op.execute("DROP INDEX IF EXISTS ix_cdna_v2_win_rate_desc")
    op.execute("DROP INDEX IF EXISTS ix_cdna_v2_name")
    op.execute("DROP INDEX IF EXISTS ix_cdna_v2_contractor_id")
    op.execute("DROP TABLE IF EXISTS contractor_dna_v2")
