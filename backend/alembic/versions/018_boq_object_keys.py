"""T-010 (INF-02): object-store keys on boq_comparisons.

Revision ID: 018_boq_object_keys
Revises: 016_hot_query_indexes
"""
from alembic import op
import sqlalchemy as sa

revision = "018_boq_object_keys"
down_revision = "016_hot_query_indexes"
branch_labels = None
depends_on = None

COLUMNS = ("upload_object_key", "excel_object_key", "docx_object_key")


def upgrade() -> None:
    for col in COLUMNS:
        op.add_column("boq_comparisons", sa.Column(col, sa.String(500), nullable=True))


def downgrade() -> None:
    for col in COLUMNS:
        op.drop_column("boq_comparisons", col)
