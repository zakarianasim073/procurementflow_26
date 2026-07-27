"""Create the reviewed ProcureFlow clean-install schema baseline.

Revision ID: 20260727_clean_baseline
Revises:
Create Date: 2026-07-27
"""

from pathlib import Path

from alembic import op


revision = "20260727_clean_baseline"
down_revision = None
branch_labels = ("clean_install",)
depends_on = None

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "baseline" / "20260727_head.sql"


def upgrade() -> None:
    schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(schema_sql)


def downgrade() -> None:
    raise RuntimeError(
        "The clean baseline is not downgraded in place. Restore the pre-migration "
        "PostgreSQL backup or recreate the empty database."
    )
