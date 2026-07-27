"""Merge crawler unique-constraints branch into main migration chain.

Revision ID: 035_merge_crawler_constraints
Revises: 034, 030_crawler_unique_constraints
Create Date: 2026-07-20

"""

from alembic import op
import sqlalchemy as sa

revision = "035_merge_crawler_constraints"
down_revision = ("034", "030_crawler_unique_constraints")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
