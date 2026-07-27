"""Search upgrade: pg_trgm + GIN FTS on awards and contractors

Revision ID: 036_search_upgrade
Revises: 035_merge_crawler_constraints
Create Date: 2026-07-20
"""

from alembic import op

revision = "036_search_upgrade"
down_revision = "035_merge_crawler_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # contractors (40K rows) — trigram on contractor_name, safe for disk
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_contractors_name_trgm
        ON contractors
        USING gin (contractor_name gin_trgm_ops)
    """)

    # pf_experience (6K rows) — trigram on name_of_work
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pf_experience_work_trgm
        ON pf_experience
        USING gin (name_of_work gin_trgm_ops)
        WHERE name_of_work IS NOT NULL
    """)

    # NOTE: GIN FTS indexes on award_records* (1M rows) and procurement_lifecycle
    # (656K rows) are omitted — they require >20 GB temp space for index build.
    # Those tables already have FTS via sequential scans (fallback in SearchService).
    # Add these indexes when disk space allows: idx_award_records_v2_fts,
    # idx_award_records_contractor_trgm, idx_lifecycle_title_trgm.


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_pf_experience_work_trgm")
    op.execute("DROP INDEX IF EXISTS idx_contractors_name_trgm")
