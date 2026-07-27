"""Add contractor_dna profile fields for JSON-to-DB migration.

W-004: Migrates pre-computed contractor DNA profiles from JSON files
into the contractor_dna table. Adds contractor_name, slug, and JSON
columns for per-agency breakdown and win probability data.

Revision ID: 031
Revises: 030_normalized_package_no
Create Date: 2026-07-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "031"
down_revision: Union[str, None] = "030_normalized_package_no"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("contractor_dna", sa.Column("contractor_name", sa.String(300), nullable=True, index=True))
    op.add_column("contractor_dna", sa.Column("slug", sa.String(300), nullable=True))
    op.add_column("contractor_dna", sa.Column("years_active", sa.JSON(), nullable=True))
    op.add_column("contractor_dna", sa.Column("procurement_type_breakdown", sa.JSON(), nullable=True))
    op.add_column("contractor_dna", sa.Column("agencies_json", sa.JSON(), nullable=True))
    op.add_column("contractor_dna", sa.Column("win_probability_json", sa.JSON(), nullable=True))
    op.add_column("contractor_dna", sa.Column("top_agency_wins", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("contractor_dna", "contractor_name")
    op.drop_column("contractor_dna", "slug")
    op.drop_column("contractor_dna", "years_active")
    op.drop_column("contractor_dna", "procurement_type_breakdown")
    op.drop_column("contractor_dna", "agencies_json")
    op.drop_column("contractor_dna", "win_probability_json")
    op.drop_column("contractor_dna", "top_agency_wins")
