"""Create pf_relationships table (Phase 4 - Relationship Engine).

Adds the explicit edge table for graph traversal across the normalized
pf_* schema. Each row is a typed, directed relationship between two
entities with confidence and metadata.

Also creates a materialized view pf_entity_graph for fast adjacency queries.

Revision ID: 020_relationship_engine
Revises: 019_normalized_schema
Create Date: 2026-07-07
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "020_relationship_engine"
down_revision = "019_normalized_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        -- Directed edge between two normalized entities
        CREATE TABLE IF NOT EXISTS pf_relationships (
            id BIGSERIAL PRIMARY KEY,
            source_type VARCHAR(50) NOT NULL,
            source_id BIGINT NOT NULL,
            target_type VARCHAR(50) NOT NULL,
            target_id BIGINT NOT NULL,
            relationship_type VARCHAR(50) NOT NULL,
            metadata JSONB,
            confidence NUMERIC(5,4) DEFAULT 1.0,
            discovered_by VARCHAR(50),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64)
        );
        """
    )

    # Indexes for graph traversal
    op.execute(
        "CREATE INDEX ix_pf_rel_source ON pf_relationships (source_type, source_id);"
    )
    op.execute(
        "CREATE INDEX ix_pf_rel_target ON pf_relationships (target_type, target_id);"
    )
    op.execute(
        "CREATE INDEX ix_pf_rel_type ON pf_relationships (relationship_type);"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_pf_rel_edge ON pf_relationships "
        "(source_type, source_id, target_type, target_id, relationship_type);"
    )
    op.execute(
        "CREATE INDEX ix_pf_rel_tgt_type ON pf_relationships (target_type, relationship_type);"
    )
    op.execute(
        "CREATE INDEX ix_pf_rel_src_type ON pf_relationships (source_type, relationship_type);"
    )

    # Trigger to auto-update updated_at
    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_pf_relationships_updated()
        RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS tgr_pf_relationships_updated ON pf_relationships;
        CREATE TRIGGER tgr_pf_relationships_updated
            BEFORE UPDATE ON pf_relationships
            FOR EACH ROW EXECUTE FUNCTION trg_pf_relationships_updated();
        """
    )

    # ── Materialized view: flattened adjacency for graph queries ──
    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS pf_entity_graph AS
        SELECT
            r.id AS relationship_id,
            r.source_type AS entity_type,
            r.source_id AS entity_id,
            r.target_type AS related_type,
            r.target_id AS related_id,
            r.relationship_type,
            r.confidence,
            r.created_at AS discovered_at
        FROM pf_relationships r
        WHERE NOT r.is_deleted
        UNION ALL
        SELECT
            r.id AS relationship_id,
            r.target_type AS entity_type,
            r.target_id AS entity_id,
            r.source_type AS related_type,
            r.source_id AS related_id,
            r.relationship_type || '_inverse' AS relationship_type,
            r.confidence,
            r.created_at AS discovered_at
        FROM pf_relationships r
        WHERE NOT r.is_deleted;
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX ix_pf_graph_uniq ON pf_entity_graph (relationship_id, entity_type, entity_id);"
    )
    op.execute(
        "CREATE INDEX ix_pf_graph_entity ON pf_entity_graph (entity_type, entity_id);"
    )
    op.execute(
        "CREATE INDEX ix_pf_graph_related ON pf_entity_graph (related_type, related_id);"
    )
    op.execute(
        "CREATE INDEX ix_pf_graph_type ON pf_entity_graph (entity_type, relationship_type);"
    )


def downgrade():
    op.execute("DROP MATERIALIZED VIEW IF EXISTS pf_entity_graph;")
    op.execute("DROP TRIGGER IF EXISTS tgr_pf_relationships_updated ON pf_relationships;")
    op.execute("DROP FUNCTION IF EXISTS trg_pf_relationships_updated;")
    op.execute("DROP TABLE IF EXISTS pf_relationships;")
