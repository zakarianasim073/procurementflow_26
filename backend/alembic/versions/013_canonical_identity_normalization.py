"""Add canonical identity and normalization tables.

Revision ID: 013_canonical_identity
Revises: 012_cdna_v2
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op


revision = "013_canonical_identity"
down_revision = "012_cdna_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS canonical_contractors (
            canonical_contractor_id TEXT PRIMARY KEY,
            canonical_name TEXT NOT NULL,
            display_name TEXT,
            is_joint_venture BOOLEAN NOT NULL DEFAULT FALSE,
            jv_member_count INTEGER NOT NULL DEFAULT 0,
            total_award_amount_bdt DOUBLE PRECISION NOT NULL DEFAULT 0,
            last_5yr_awarded_amount_bdt DOUBLE PRECISION NOT NULL DEFAULT 0,
            work_in_hand_bdt DOUBLE PRECISION NOT NULL DEFAULT 0,
            estimated_turnover_bdt DOUBLE PRECISION NOT NULL DEFAULT 0,
            tender_capacity_bdt DOUBLE PRECISION NOT NULL DEFAULT 0,
            total_bids INTEGER NOT NULL DEFAULT 0,
            total_wins INTEGER NOT NULL DEFAULT 0,
            win_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
            agencies JSONB NOT NULL DEFAULT '{}'::jsonb,
            districts JSONB NOT NULL DEFAULT '{}'::jsonb,
            work_type_mix JSONB NOT NULL DEFAULT '{}'::jsonb,
            reliability_score DOUBLE PRECISION NOT NULL DEFAULT 0,
            data_confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
            source_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
            rebuilt_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS canonical_contractor_aliases (
            alias_key TEXT PRIMARY KEY,
            canonical_contractor_id TEXT NOT NULL REFERENCES canonical_contractors(canonical_contractor_id) ON DELETE CASCADE,
            alias_name TEXT NOT NULL,
            normalized_alias TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'derived',
            confidence DOUBLE PRECISION NOT NULL DEFAULT 0.8,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS canonical_contractor_jv_members (
            jv_canonical_contractor_id TEXT NOT NULL REFERENCES canonical_contractors(canonical_contractor_id) ON DELETE CASCADE,
            member_canonical_contractor_id TEXT NOT NULL REFERENCES canonical_contractors(canonical_contractor_id) ON DELETE CASCADE,
            member_name TEXT NOT NULL,
            normalized_member_name TEXT NOT NULL,
            share_pct DOUBLE PRECISION,
            confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
            PRIMARY KEY (jv_canonical_contractor_id, member_canonical_contractor_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS canonical_tenders (
            canonical_package_key TEXT PRIMARY KEY,
            package_no TEXT,
            normalized_package_no TEXT,
            tender_id TEXT,
            title TEXT,
            agency_code TEXT,
            district TEXT,
            pe_office TEXT,
            estimated_cost_bdt DOUBLE PRECISION NOT NULL DEFAULT 0,
            source_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
            identity_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
            rebuilt_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS canonical_contracts (
            canonical_contract_id TEXT PRIMARY KEY,
            canonical_package_key TEXT NOT NULL REFERENCES canonical_tenders(canonical_package_key) ON DELETE CASCADE,
            canonical_contractor_id TEXT REFERENCES canonical_contractors(canonical_contractor_id) ON DELETE SET NULL,
            source_table TEXT NOT NULL,
            source_id TEXT NOT NULL,
            tender_id TEXT,
            package_no TEXT,
            title TEXT,
            agency_code TEXT,
            district TEXT,
            contractor_name TEXT,
            contract_date DATE,
            amount_original DOUBLE PRECISION NOT NULL DEFAULT 0,
            amount_normalized_bdt DOUBLE PRECISION NOT NULL DEFAULT 0,
            amount_unit TEXT NOT NULL DEFAULT 'bdt',
            amount_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
            amount_warning TEXT,
            status TEXT,
            is_ongoing BOOLEAN NOT NULL DEFAULT FALSE,
            progress_pct DOUBLE PRECISION NOT NULL DEFAULT 0,
            raw_ref JSONB NOT NULL DEFAULT '{}'::jsonb,
            rebuilt_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS amount_normalization_audit (
            id BIGSERIAL PRIMARY KEY,
            source_table TEXT NOT NULL,
            source_id TEXT NOT NULL,
            package_no TEXT,
            amount_original DOUBLE PRECISION NOT NULL DEFAULT 0,
            amount_normalized_bdt DOUBLE PRECISION NOT NULL DEFAULT 0,
            amount_unit TEXT NOT NULL DEFAULT 'bdt',
            confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
            warning TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_canonical_contractors_name ON canonical_contractors (canonical_name)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_canonical_contractors_capacity ON canonical_contractors (tender_capacity_bdt DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_canonical_aliases_contractor ON canonical_contractor_aliases (canonical_contractor_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_canonical_aliases_norm ON canonical_contractor_aliases (normalized_alias)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_canonical_tenders_package ON canonical_tenders (normalized_package_no)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_canonical_tenders_tender_id ON canonical_tenders (tender_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_canonical_contracts_contractor ON canonical_contracts (canonical_contractor_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_canonical_contracts_package ON canonical_contracts (canonical_package_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_canonical_contracts_amount ON canonical_contracts (amount_normalized_bdt DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_canonical_contracts_source ON canonical_contracts (source_table, source_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS amount_normalization_audit")
    op.execute("DROP TABLE IF EXISTS canonical_contracts")
    op.execute("DROP TABLE IF EXISTS canonical_tenders")
    op.execute("DROP TABLE IF EXISTS canonical_contractor_jv_members")
    op.execute("DROP TABLE IF EXISTS canonical_contractor_aliases")
    op.execute("DROP TABLE IF EXISTS canonical_contractors")
