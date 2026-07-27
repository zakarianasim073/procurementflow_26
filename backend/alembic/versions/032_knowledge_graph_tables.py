"""Create knowledge graph tables with pgvector embeddings and RLS.

W-015: Migrate knowledge graph from in-memory NetworkX to PostgreSQL.
Tables: knowledge_nodes, knowledge_edges, knowledge_embeddings
All tables tenant-scoped with RLS policies.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '032'
down_revision = '031'
branch_labels = None
depends_on = None


def upgrade():
    # Note: pgvector extension requires server-side installation. For production deployments,
    # run: CREATE EXTENSION IF NOT EXISTS vector; and alter the embedding column to vector type.
    # For now, use TEXT to store embeddings as JSON-serialized arrays for portability.

    # knowledge_nodes table
    op.create_table(
        'knowledge_nodes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('node_type', sa.String(50), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=False),
        sa.Column('label', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('meta_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_knowledge_nodes_type_external_id', 'knowledge_nodes', ['node_type', 'external_id'])
    op.create_index('ix_knowledge_nodes_tenant_id', 'knowledge_nodes', ['tenant_id'])

    # knowledge_edges table
    op.create_table(
        'knowledge_edges',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_node_id', sa.UUID(), nullable=False),
        sa.Column('target_node_id', sa.UUID(), nullable=False),
        sa.Column('edge_type', sa.String(50), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('meta_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['source_node_id'], ['knowledge_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_node_id'], ['knowledge_nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_knowledge_edges_source_target', 'knowledge_edges', ['source_node_id', 'target_node_id'])
    # target_node_id needs its own leading index: FK CASCADE checks on node delete
    # and get_incoming_edges() both filter by it alone.
    op.create_index('ix_knowledge_edges_target', 'knowledge_edges', ['target_node_id'])
    op.create_index('ix_knowledge_edges_type', 'knowledge_edges', ['edge_type'])
    op.create_index('ix_knowledge_edges_tenant_id', 'knowledge_edges', ['tenant_id'])

    # knowledge_embeddings table
    op.create_table(
        'knowledge_embeddings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('node_id', sa.UUID(), nullable=False),
        sa.Column('embedding', sa.Text(), nullable=False),
        sa.Column('embedding_model', sa.String(255), nullable=False, server_default='sentence-transformers/all-MiniLM-L6-v2'),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['node_id'], ['knowledge_nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_knowledge_embeddings_node_id', 'knowledge_embeddings', ['node_id'])
    op.create_index('ix_knowledge_embeddings_model', 'knowledge_embeddings', ['embedding_model'])
    op.create_index('ix_knowledge_embeddings_tenant_id', 'knowledge_embeddings', ['tenant_id'])

    # RLS policies (ADR-007, SEC-02)
    op.execute("""
        ALTER TABLE knowledge_nodes ENABLE ROW LEVEL SECURITY;
        CREATE POLICY knowledge_nodes_tenant_isolation ON knowledge_nodes
            USING (tenant_id = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
    """)

    op.execute("""
        ALTER TABLE knowledge_edges ENABLE ROW LEVEL SECURITY;
        CREATE POLICY knowledge_edges_tenant_isolation ON knowledge_edges
            USING (tenant_id = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
    """)

    op.execute("""
        ALTER TABLE knowledge_embeddings ENABLE ROW LEVEL SECURITY;
        CREATE POLICY knowledge_embeddings_tenant_isolation ON knowledge_embeddings
            USING (tenant_id = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
    """)


def downgrade():
    op.drop_index('ix_knowledge_embeddings_tenant_id')
    op.drop_index('ix_knowledge_embeddings_model')
    op.drop_index('ix_knowledge_embeddings_node_id')
    op.drop_table('knowledge_embeddings')

    op.drop_index('ix_knowledge_edges_tenant_id')
    op.drop_index('ix_knowledge_edges_type')
    op.drop_index('ix_knowledge_edges_target')
    op.drop_index('ix_knowledge_edges_source_target')
    op.drop_table('knowledge_edges')

    op.drop_index('ix_knowledge_nodes_tenant_id')
    op.drop_index('ix_knowledge_nodes_type_external_id')
    op.drop_table('knowledge_nodes')
