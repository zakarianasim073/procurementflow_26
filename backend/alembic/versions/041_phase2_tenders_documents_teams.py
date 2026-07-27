"""Phase 2: Tender, Document, Team Management tables

Revision ID: 041
Revises: 040
Create Date: 2026-07-22 06:45:00.000000

DIVERGENCE — this file does not describe the live schema.

The phase2 tables were created directly from app/models/phase2.py while alembic
was unrunnable (two heads, see 007a_fix_data_corruption), so the database was
built from the models rather than from this migration. The two disagree:

  phase2_documents.document_type   live: varchar     here: ENUM documenttype
  phase2_tenders                   live: absent      here: created

phase2_tenders is unused — app/api/v2/tenders.py reads app.models.tender.Tender,
which maps to the pre-existing `tenders` table, not to phase2_tenders.

The revision was therefore stamped rather than executed. Reconciling this file
with the models is outstanding work: either the models adopt the enums, or this
migration is rewritten to match the models and phase2_tenders is dropped from
it. Do not run upgrade() against a database that already has these tables.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "041_phase2_tenders_documents_teams"
down_revision = "040_award_v2_gin_indexes"
branch_labels = None
depends_on = None


def upgrade():
    # The phase2 tables were created directly from the models before this
    # migration could run, so the enum types may already exist. postgres has no
    # CREATE TYPE ... IF NOT EXISTS, and create_table would abort on the
    # duplicate, so the types are created defensively here and the columns below
    # reference them with create_type=False.
    for name, values in (
        ("tenderstatus", ("live", "closed", "awarded", "cancelled")),
        ("documenttype", ("notice", "tds", "boq", "specification", "other")),
        ("teamrole", ("owner", "admin", "member", "viewer")),
    ):
        labels = ", ".join(f"'{v}'" for v in values)
        op.execute(
            f"""
            DO $$ BEGIN
                CREATE TYPE {name} AS ENUM ({labels});
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
            """
        )

    # Create Tender table
    op.create_table(
        'phase2_tenders',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tender_id', sa.String(100), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('agency', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('location', sa.String(255), nullable=False),
        sa.Column('estimated_value', sa.Float(), nullable=False),
        sa.Column('deadline', sa.DateTime(), nullable=False),
        sa.Column('status', postgresql.ENUM('live', 'closed', 'awarded', 'cancelled', name='tenderstatus', create_type=False), nullable=False),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tender_id'),
    )
    op.create_index('ix_phase2_tenders_agency', 'phase2_tenders', ['agency'])
    op.create_index('ix_phase2_tenders_deadline', 'phase2_tenders', ['deadline'])
    op.create_index('ix_phase2_tenders_status', 'phase2_tenders', ['status'])
    op.create_index('ix_phase2_tenders_tenant_deadline', 'phase2_tenders', ['tenant_id', 'deadline'])
    op.create_index('ix_phase2_tenders_tenant_status', 'phase2_tenders', ['tenant_id', 'status'])

    # Create Document table
    op.create_table(
        'phase2_documents',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('document_type', postgresql.ENUM('notice', 'tds', 'boq', 'specification', 'other', name='documenttype', create_type=False), nullable=False),
        sa.Column('tender_id', sa.String(36), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('extracted_data', sa.Text(), nullable=True),
        sa.Column('extraction_status', sa.String(50), nullable=False),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tender_id'], ['phase2_tenders.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_phase2_documents_document_type', 'phase2_documents', ['document_type'])
    op.create_index('ix_phase2_documents_tenant', 'phase2_documents', ['tenant_id'])
    op.create_index('ix_phase2_documents_tender_id', 'phase2_documents', ['tender_id'])
    op.create_index('ix_phase2_documents_tender_type', 'phase2_documents', ['tender_id', 'document_type'])

    # Create TeamMember table
    op.create_table(
        'phase2_team_members',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', postgresql.ENUM('owner', 'admin', 'member', 'viewer', name='teamrole', create_type=False), nullable=False),
        sa.Column('department', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('invited_at', sa.DateTime(), nullable=False),
        sa.Column('joined_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_phase2_team_members_email', 'phase2_team_members', ['email'])
    op.create_index('ix_phase2_team_members_tenant_active', 'phase2_team_members', ['tenant_id', 'is_active'])
    op.create_index('ix_phase2_team_members_tenant_email', 'phase2_team_members', ['tenant_id', 'email'])

    # Create Team table
    op.create_table(
        'phase2_teams',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('max_members', sa.Integer(), nullable=False),
        sa.Column('settings', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id'),
    )
    op.create_index('ix_phase2_teams_tenant_id', 'phase2_teams', ['tenant_id'])


def downgrade():
    op.drop_index('ix_phase2_teams_tenant_id', table_name='phase2_teams')
    op.drop_table('phase2_teams')
    op.drop_index('ix_phase2_team_members_tenant_email', table_name='phase2_team_members')
    op.drop_index('ix_phase2_team_members_tenant_active', table_name='phase2_team_members')
    op.drop_index('ix_phase2_team_members_email', table_name='phase2_team_members')
    op.drop_table('phase2_team_members')
    op.drop_index('ix_phase2_documents_tender_type', table_name='phase2_documents')
    op.drop_index('ix_phase2_documents_tender_id', table_name='phase2_documents')
    op.drop_index('ix_phase2_documents_tenant', table_name='phase2_documents')
    op.drop_index('ix_phase2_documents_document_type', table_name='phase2_documents')
    op.drop_table('phase2_documents')
    op.drop_index('ix_phase2_tenders_tenant_status', table_name='phase2_tenders')
    op.drop_index('ix_phase2_tenders_tenant_deadline', table_name='phase2_tenders')
    op.drop_index('ix_phase2_tenders_status', table_name='phase2_tenders')
    op.drop_index('ix_phase2_tenders_deadline', table_name='phase2_tenders')
    op.drop_index('ix_phase2_tenders_agency', table_name='phase2_tenders')
    op.drop_table('phase2_tenders')
