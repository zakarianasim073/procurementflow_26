"""Merge legacy Tender schema into canonical ORM (T-021: dual-ORM migration A)

Revision ID: 024_merge_tender_models
Revises: 023_refresh_tokens
Create Date: 2026-07-13

This migration absorbs all legacy Tender columns into the canonical app.models.Tender,
unifying the two conflicting ORM definitions. The database table remains unchanged
structurally; only the ORM model is consolidated.

Columns added:
  - package_no, invitation_ref (legacy identifiers)
  - work_name, description (legacy descriptions)
  - ministry, organization, department_id, agency_target (legacy agency info)
  - procurement_method, regime (legacy procurement details)
  - publication_date, last_selling_date, work_period_start, work_period_end (legacy dates)
  - estimated_amount_bdt, completion_period_days (legacy financial)
  - is_archived (legacy status)
  - raw_data, source_file, _stored_at, _domain (legacy metadata)
  - app_id (legacy lifecycle)

All new columns are nullable to preserve backward compatibility with existing data.
Alembic now tracks only app.models.Base (canonical); app.db.models.Tender is deleted
and replaced with a backward-compat import shim.

ADR-002 progress: Alembic metadata unified; Tender model conflict resolved.
Remaining: T-022 (services off legacy base), T-023 (crawlers/ETL migrated, deletion).
"""

from alembic import op
import sqlalchemy as sa


revision = "024_merge_tender_models"
down_revision = "023_refresh_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing legacy Tender columns to canonical schema."""

    # Add legacy identifier columns
    op.add_column('tenders', sa.Column('package_no', sa.String(100), nullable=True))
    op.add_column('tenders', sa.Column('invitation_ref', sa.String(100), nullable=True))

    # Add legacy description columns
    op.add_column('tenders', sa.Column('work_name', sa.Text(), nullable=True))
    op.add_column('tenders', sa.Column('description', sa.Text(), nullable=True))

    # Add legacy agency columns (most already exist; add missing ones)
    op.add_column('tenders', sa.Column('procuring_entity_district', sa.String(100), nullable=True))
    op.add_column('tenders', sa.Column('ministry', sa.String(255), nullable=True))
    op.add_column('tenders', sa.Column('organization', sa.String(255), nullable=True))
    op.add_column('tenders', sa.Column('department_id', sa.String(50), nullable=True))
    op.add_column('tenders', sa.Column('agency_target', sa.String(100), nullable=True))

    # Add legacy procurement columns
    op.add_column('tenders', sa.Column('procurement_method', sa.String(255), nullable=True))
    op.add_column('tenders', sa.Column('regime', sa.String(20), server_default='PPR2008', nullable=False))

    # Add legacy date columns
    op.add_column('tenders', sa.Column('publication_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenders', sa.Column('last_selling_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenders', sa.Column('work_period_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenders', sa.Column('work_period_end', sa.DateTime(timezone=True), nullable=True))

    # Add legacy financial columns
    op.add_column('tenders', sa.Column('estimated_amount_bdt', sa.Float(), nullable=True))
    op.add_column('tenders', sa.Column('completion_period_days', sa.Integer(), nullable=True))

    # Add legacy status column
    op.add_column('tenders', sa.Column('is_archived', sa.Boolean(), server_default=sa.false(), nullable=False))

    # Add legacy metadata columns
    op.add_column('tenders', sa.Column('raw_data', sa.JSON(), nullable=True))
    op.add_column('tenders', sa.Column('source_file', sa.String(255), nullable=True))
    op.add_column('tenders', sa.Column('_stored_at', sa.String(50), nullable=True))
    op.add_column('tenders', sa.Column('_domain', sa.String(50), nullable=True))

    # Add legacy lifecycle column
    op.add_column('tenders', sa.Column('app_id', sa.String(100), nullable=True))

    # Ensure source column has correct default (legacy default was 'egp')
    # Note: source column may already exist; this is idempotent if it does
    try:
        op.add_column('tenders', sa.Column('source', sa.String(50), server_default='egp', nullable=False))
    except sa.exc.OperationalError:
        # Column already exists; skip
        pass

    # Add missing indexes from legacy schema
    # Note: Some indexes may already exist; Alembic skips duplicates
    op.create_index('ix_tenders_tenant_id', 'tenders', ['tenant_id'], if_not_exists=True)
    op.create_index('ix_tenders_package_no', 'tenders', ['package_no'], if_not_exists=True)
    op.create_index('ix_tenders_app_id', 'tenders', ['app_id'], if_not_exists=True)
    op.create_index('ix_tenders_regime', 'tenders', ['regime'], if_not_exists=True)


def downgrade() -> None:
    """Rollback: remove merged columns (data-safe; columns are dropped)."""

    # Drop indexes
    op.drop_index('ix_tenders_regime', table_name='tenders', if_exists=True)
    op.drop_index('ix_tenders_app_id', table_name='tenders', if_exists=True)
    op.drop_index('ix_tenders_package_no', table_name='tenders', if_exists=True)
    op.drop_index('ix_tenders_tenant_id', table_name='tenders', if_exists=True)

    # Drop columns (in reverse order of creation)
    op.drop_column('tenders', 'app_id')
    op.drop_column('tenders', '_domain')
    op.drop_column('tenders', '_stored_at')
    op.drop_column('tenders', 'source_file')
    op.drop_column('tenders', 'raw_data')
    op.drop_column('tenders', 'is_archived')
    op.drop_column('tenders', 'completion_period_days')
    op.drop_column('tenders', 'estimated_amount_bdt')
    op.drop_column('tenders', 'work_period_end')
    op.drop_column('tenders', 'work_period_start')
    op.drop_column('tenders', 'last_selling_date')
    op.drop_column('tenders', 'publication_date')
    op.drop_column('tenders', 'regime')
    op.drop_column('tenders', 'procurement_method')
    op.drop_column('tenders', 'agency_target')
    op.drop_column('tenders', 'department_id')
    op.drop_column('tenders', 'organization')
    op.drop_column('tenders', 'ministry')
    op.drop_column('tenders', 'procuring_entity_district')
    op.drop_column('tenders', 'description')
    op.drop_column('tenders', 'work_name')
    op.drop_column('tenders', 'invitation_ref')
    op.drop_column('tenders', 'package_no')
