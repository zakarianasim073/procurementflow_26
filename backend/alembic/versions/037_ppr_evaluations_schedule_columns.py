"""Add legacy Schedule 4/5/6 columns to ppr_evaluations (model-DB drift fix)

The PPREvaluation model (merged in 024) declares schedule_* columns that were
never added to the live table, breaking every SELECT on the model
(e.g. /executive/report 500).

Revision ID: 037_ppr_eval_schedule_cols
Revises: 036_search_upgrade
Create Date: 2026-07-20
"""

from alembic import op

revision = "037_ppr_eval_schedule_cols"
down_revision = "036_search_upgrade"
branch_labels = None
depends_on = None

_COLS = [
    ("schedule_type", "VARCHAR(50)"),
    ("schedule_label", "VARCHAR(255)"),
    ("criteria", "TEXT"),
    ("total_marks", "DOUBLE PRECISION"),
    ("max_marks", "DOUBLE PRECISION"),
    ("percentage", "DOUBLE PRECISION"),
    ("passed", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("raw_data", "JSON"),
    ("agent_result_id", "VARCHAR(36)"),
]


def upgrade() -> None:
    for name, ddl in _COLS:
        op.execute(f"ALTER TABLE ppr_evaluations ADD COLUMN IF NOT EXISTS {name} {ddl}")


def downgrade() -> None:
    for name, _ in reversed(_COLS):
        op.execute(f"ALTER TABLE ppr_evaluations DROP COLUMN IF EXISTS {name}")
