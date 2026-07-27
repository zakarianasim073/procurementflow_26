"""T-013 (API-01): boq_jobs table for async BOQ comparison offload.

Revision ID: 022_boq_jobs
Revises: 021_vector_search
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

revision = "022_boq_jobs"
down_revision = "021_vector_search"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "boq_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("comparison_id", sa.String(length=36), sa.ForeignKey("boq_comparisons.id"), nullable=True),
        sa.Column("result_meta", sa.JSON(), nullable=True),
        sa.Column("error", sa.String(length=2000), nullable=True),
        sa.Column("celery_task_id", sa.String(length=155), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_boq_jobs_user_id", "boq_jobs", ["user_id"])
    op.create_index("ix_boq_jobs_status", "boq_jobs", ["status"])
    op.create_index("ix_boq_jobs_user_created", "boq_jobs", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_boq_jobs_user_created", table_name="boq_jobs")
    op.drop_index("ix_boq_jobs_status", table_name="boq_jobs")
    op.drop_index("ix_boq_jobs_user_id", table_name="boq_jobs")
    op.drop_table("boq_jobs")
