"""005_add_performance_indexes_and_contractor_dna_v2

Revision ID: 005
Revises: 004
Create Date: 2026-06-29

Performance indexes for 'latest record' queries and
contractor_dna_v2 table for full DNA profiles.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Performance indexes for ORDER BY created_at DESC LIMIT 1 ──────
    # These prevent sequential scans on large tables.

    # BOQ comparisons — used in /executive/report
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_boq_comparisons_created_at_desc "
        "ON boq_comparisons (created_at DESC)"
    )

    # PPR evaluations — used in /executive/report and /ppr2025/evaluate/*
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ppr_eval_created_at_desc "
        "ON ppr_evaluations (created_at DESC)"
    )

    # Award records — used by competitor and win probability agents
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_arv2_date_desc "
        "ON award_records_v2 (award_date DESC)"
    )

    # Procurement lifecycle — used for NPP analytics
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_lifecycle_agency_npp "
        "ON procurement_lifecycle (agency_code, npp_ratio) "
        "WHERE npp_ratio BETWEEN 0.05 AND 1.5 AND data_source = 'matched'"
    )

    # ── contractor_dna_v2: full DNA profile table ──────────────────────
    op.create_table(
        "contractor_dna_v2",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("contractor_id", sa.String(36), nullable=False, unique=True, index=True),
        sa.Column("contractor_name", sa.String(300), nullable=False, index=True),
        # Bidding behaviour
        sa.Column("total_bids", sa.Integer(), default=0),
        sa.Column("total_wins", sa.Integer(), default=0),
        sa.Column("win_rate", sa.Float(), default=0.0),
        sa.Column("avg_discount", sa.Float(), default=0.0),
        sa.Column("discount_stddev", sa.Float(), default=0.0),
        # Ranking & responsiveness
        sa.Column("avg_rank", sa.Float(), default=0.0),
        sa.Column("responsive_rate", sa.Float(), default=0.0),
        sa.Column("slt_rate", sa.Float(), default=0.0),
        sa.Column("non_responsive_rate", sa.Float(), default=0.0),
        # Agency / zone affinity (JSON maps)
        sa.Column("agency_affinity", sa.JSON(), default=dict),
        sa.Column("zone_affinity", sa.JSON(), default=dict),
        sa.Column("project_type_affinity", sa.JSON(), default=dict),
        # Financial
        sa.Column("total_award_amount_bdt", sa.Float(), default=0.0),
        sa.Column("avg_award_amount_bdt", sa.Float(), default=0.0),
        # Intelligence indices
        sa.Column("nppi_score", sa.Float(), default=0.0),
        sa.Column("aggression_index", sa.Float(), default=0.0),
        sa.Column("reliability_index", sa.Float(), default=0.0),
        sa.Column("adaptation_score", sa.Float(), default=0.0),
        sa.Column("health_score", sa.Float(), default=0.0),
        # Meta
        sa.Column("last_rebuilt_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index(
        "ix_cdna_v2_contractor_id", "contractor_dna_v2", ["contractor_id"]
    )
    op.create_index(
        "ix_cdna_v2_win_rate_desc", "contractor_dna_v2", ["win_rate"]
    )


def downgrade() -> None:
    op.drop_table("contractor_dna_v2")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_boq_comparisons_created_at_desc")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_ppr_eval_created_at_desc")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_arv2_date_desc")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_lifecycle_agency_npp")
