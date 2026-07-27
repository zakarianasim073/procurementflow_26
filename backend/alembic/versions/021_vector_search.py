"""Create pf_document_embeddings table (Phase 12 - Vector Search).

NOTE: pgvector extension is NOT installed on the target PostgreSQL 17
instance, so embeddings are stored as native `float[]` arrays and
cosine similarity is computed in Python (or via SQL array math). This
keeps the feature functional without requiring a pgvector install.

If pgvector becomes available later, the embedding column can be
altered to type `vector(384)` and the ivfflat index added.

Revision ID: 021_vector_search
Revises: 020_relationship_engine
Create Date: 2026-07-07
"""
from __future__ import annotations

from alembic import op


revision = "021_vector_search"
down_revision = "020_relationship_engine"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pf_document_embeddings (
            id BIGSERIAL PRIMARY KEY,
            entity_type VARCHAR(50) NOT NULL,
            entity_id BIGINT NOT NULL,
            doc_type VARCHAR(50),
            text_content TEXT,
            embedding FLOAT[] NOT NULL,
            metadata JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_pf_emb_entity ON pf_document_embeddings (entity_type, entity_id);"
    )
    op.execute(
        "CREATE INDEX ix_pf_emb_type ON pf_document_embeddings (doc_type);"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_pf_emb_entity_doc ON pf_document_embeddings (entity_type, entity_id, doc_type);"
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS pf_document_embeddings;")
