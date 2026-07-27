"""Merge award-lifecycle trigram branch + finish remaining GIN indexes.

037_award_lifecycle_trigram (idx_award_records_contractor_trgm,
idx_lifecycle_title_trgm) was left as an orphan branch off 036_search_upgrade —
its indexes were already built directly against the DB but never folded into
the applied alembic chain. This merges that branch with the main line and adds
the two GIN indexes 036 deferred and never came back for:

  * idx_award_records_v2_fts   — FTS GIN on award_records_v2, matching the
    exact tsvector expression SearchService.search_awards() queries
    (title || contractor_name || procuring_entity), so the planner can use it.
  * idx_award_records_v2_contractor_trgm — trigram GIN on contractor_name for
    the ILIKE contractor/district filters in the same query.
  * idx_contractors_fts — FTS GIN on contractors.contractor_name, matching
    SearchService.search_contractors()'s tsvector expression (36 already has
    trigram only, not the FTS-matching expression index).

All three tables now have enough disk headroom (38 GB free vs. 22.5 GB when
036 deferred this work). Built CONCURRENTLY to avoid locking 998K/40K-row
tables during index creation.
"""

from alembic import op
from sqlalchemy import text

revision = "040_award_v2_gin_indexes"
down_revision = ("039_merge_ppr_eval_enriched", "037_award_lifecycle_trigram")
branch_labels = None
depends_on = None

_STATEMENTS_UP = [
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_award_records_v2_fts
    ON public.award_records_v2
    USING gin (
        to_tsvector('simple',
            coalesce(title,'') || ' ' ||
            coalesce(contractor_name,'') || ' ' ||
            coalesce(procuring_entity,'')
        )
    )
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_award_records_v2_contractor_trgm
    ON public.award_records_v2
    USING gin (contractor_name gin_trgm_ops)
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contractors_fts
    ON public.contractors
    USING gin (to_tsvector('simple', coalesce(contractor_name,'')))
    """,
]

_STATEMENTS_DOWN = [
    "DROP INDEX CONCURRENTLY IF EXISTS idx_contractors_fts",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_award_records_v2_contractor_trgm",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_award_records_v2_fts",
]


def _run_concurrent_ddl(statements):
    # CREATE/DROP INDEX CONCURRENTLY must run outside a transaction block.
    bind = op.get_bind()
    engine = bind.engine
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        for stmt in statements:
            conn.execute(text(stmt))


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    _run_concurrent_ddl(_STATEMENTS_UP)


def downgrade() -> None:
    _run_concurrent_ddl(_STATEMENTS_DOWN)
