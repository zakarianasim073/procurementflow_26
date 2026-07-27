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
    # The reviewed pg_dump contains literal percent characters in stored
    # function bodies. Execute it through psycopg2's raw cursor so SQLAlchemy
    # does not interpret those characters as parameter markers.
    connection = op.get_bind().connection.driver_connection
    with connection.cursor() as cursor:
        for extension in ("vector", "pg_trgm", '"uuid-ossp"'):
            cursor.execute(f"CREATE EXTENSION IF NOT EXISTS {extension}")
        # Remove the three reviewed extension statements from the dump body.
        # PostgreSQL parses a multi-statement query before executing it, so the
        # vector type must exist before the body containing vector(384) parses.
        schema_body = schema_sql.split("\n\n", 1)[1]
        cursor.execute(schema_body)
        # pg_dump deliberately clears search_path while restoring qualified
        # objects. Restore Alembic's expected path before it records the head.
        cursor.execute("SET search_path TO public")


def downgrade() -> None:
    raise RuntimeError(
        "The clean baseline is not downgraded in place. Restore the pre-migration "
        "PostgreSQL backup or recreate the empty database."
    )
