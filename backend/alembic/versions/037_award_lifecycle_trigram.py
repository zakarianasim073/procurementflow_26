"""ENT-08 (search): trigram GIN indexes on the two large deferred tables.

The 036_search_upgrade migration added trigram GIN indexes on the small tables
(``contractors.contractor_name``, ``pf_experience.name_of_work``) and
*deliberately deferred* the two large tables, noting they need disk for the
index build:
  * ``award_records.contractor_name``  (~998K rows, 1.45 GB)
  * ``procurement_lifecycle.title``     (~658K rows, 1.30 GB)

This migration adds exactly those two, using the index names anticipated in
036's TODO (``idx_award_records_contractor_trgm``, ``idx_lifecycle_title_trgm``)
so the work is consistent and re-runnable.

``pg_trgm`` is already installed (see 036). The indexes are built
``CONCURRENTLY`` to avoid a long write lock on the multi-million-row tables.
``CREATE INDEX CONCURRENTLY`` cannot run inside a transaction block, so the DDL
is issued on an autocommit branch of the migration connection (SQLAlchemy's
documented pattern for concurrent DDL).
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "037_award_lifecycle_trigram"
down_revision = "036_search_upgrade"
branch_labels = None
depends_on = None

# (index_name, table, column, where_clause_or_None)
TRGM_INDEXES = [
    (
        "idx_award_records_contractor_trgm",
        "award_records",
        "contractor_name",
        None,
    ),
    (
        "idx_lifecycle_title_trgm",
        "procurement_lifecycle",
        "title",
        "title IS NOT NULL",
    ),
]


def _run_concurrent_ddl(statements):
    # CREATE INDEX CONCURRENTLY must run outside a transaction block.
    # Alembic's migration connection is already in a transaction (autobegin),
    # so open a fresh engine connection and run the DDL in AUTOCOMMIT mode.
    bind = op.get_bind()
    engine = bind.engine
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        for stmt in statements:
            conn.execute(text(stmt))


def upgrade():
    statements = []
    for idx_name, table, column, where in TRGM_INDEXES:
        ddl = (
            f'CREATE INDEX CONCURRENTLY IF NOT EXISTS "{idx_name}" '
            f'ON public."{table}" USING gin ("{column}" gin_trgm_ops)'
        )
        if where:
            ddl += f" WHERE ({where})"
        statements.append(ddl)
    _run_concurrent_ddl(statements)


def downgrade():
    statements = [
        f'DROP INDEX CONCURRENTLY IF EXISTS "{idx_name}"'
        for idx_name, _t, _c, _w in TRGM_INDEXES
    ]
    _run_concurrent_ddl(statements)
