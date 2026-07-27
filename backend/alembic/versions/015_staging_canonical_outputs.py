"""Add staging and named canonical intelligence output tables.

Revision ID: 015_staging_canonical_outputs
Revises: 014_raw_repair_queue
Create Date: 2026-07-05
"""
from __future__ import annotations

from alembic import op


revision = "015_staging_canonical_outputs"
down_revision = "014_raw_repair_queue"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name in ("staging_awards", "staging_app_packages", "staging_ecms_ongoing", "staging_econtracts"):
        op.execute(f"""
            CREATE TABLE IF NOT EXISTS {name} (
                staging_id TEXT PRIMARY KEY,
                raw_id TEXT REFERENCES raw_json_documents(raw_id) ON DELETE SET NULL,
                source_family TEXT NOT NULL,
                source_path TEXT,
                package_no TEXT,
                normalized_package_no TEXT,
                tender_id TEXT,
                title TEXT,
                agency_code TEXT,
                district TEXT,
                pe_office TEXT,
                contractor_name TEXT,
                amount_raw TEXT,
                amount_normalized_bdt DOUBLE PRECISION NOT NULL DEFAULT 0,
                amount_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
                source_date DATE,
                confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
                raw_payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                parsed_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{name}_package ON {name} (normalized_package_no)")
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{name}_tender ON {name} (tender_id)")
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{name}_agency ON {name} (agency_code)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS canonical_awards (
            canonical_award_id TEXT PRIMARY KEY,
            canonical_contract_id TEXT REFERENCES canonical_contracts(canonical_contract_id) ON DELETE CASCADE,
            canonical_package_key TEXT NOT NULL,
            canonical_contractor_id TEXT,
            package_no TEXT,
            tender_id TEXT,
            title TEXT,
            agency_code TEXT,
            district TEXT,
            contractor_name TEXT,
            award_date DATE,
            award_amount_bdt DOUBLE PRECISION NOT NULL DEFAULT 0,
            confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
            source_ref JSONB NOT NULL DEFAULT '{}'::jsonb,
            rebuilt_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS canonical_app_packages (
            canonical_app_id TEXT PRIMARY KEY,
            canonical_package_key TEXT NOT NULL,
            package_no TEXT,
            tender_id TEXT,
            title TEXT,
            agency_code TEXT,
            district TEXT,
            pe_office TEXT,
            financial_year TEXT,
            estimated_cost_bdt DOUBLE PRECISION NOT NULL DEFAULT 0,
            confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
            source_ref JSONB NOT NULL DEFAULT '{}'::jsonb,
            rebuilt_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS canonical_contractor_dna (
            canonical_contractor_id TEXT PRIMARY KEY REFERENCES canonical_contractors(canonical_contractor_id) ON DELETE CASCADE,
            contractor_name TEXT,
            normalized_name TEXT,
            aliases JSONB NOT NULL DEFAULT '[]'::jsonb,
            jv_members JSONB NOT NULL DEFAULT '[]'::jsonb,
            total_awarded_5yr_bdt DOUBLE PRECISION NOT NULL DEFAULT 0,
            annual_turnover_estimate_bdt DOUBLE PRECISION NOT NULL DEFAULT 0,
            work_in_hand_bdt DOUBLE PRECISION NOT NULL DEFAULT 0,
            available_capacity_bdt DOUBLE PRECISION NOT NULL DEFAULT 0,
            tender_capacity_bdt DOUBLE PRECISION NOT NULL DEFAULT 0,
            total_bids INTEGER NOT NULL DEFAULT 0,
            total_wins INTEGER NOT NULL DEFAULT 0,
            win_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
            late_delivery_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
            on_time_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
            top_agencies JSONB NOT NULL DEFAULT '[]'::jsonb,
            top_districts JSONB NOT NULL DEFAULT '[]'::jsonb,
            work_type_mix JSONB NOT NULL DEFAULT '{}'::jsonb,
            reliability_score DOUBLE PRECISION NOT NULL DEFAULT 0,
            financial_strength_score DOUBLE PRECISION NOT NULL DEFAULT 0,
            capacity_score DOUBLE PRECISION NOT NULL DEFAULT 0,
            competition_score DOUBLE PRECISION NOT NULL DEFAULT 0,
            overall_dna_score DOUBLE PRECISION NOT NULL DEFAULT 0,
            data_confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
            rebuilt_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_canonical_awards_package ON canonical_awards (canonical_package_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_canonical_awards_contractor ON canonical_awards (canonical_contractor_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_canonical_app_packages_package ON canonical_app_packages (canonical_package_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_canonical_dna_capacity ON canonical_contractor_dna (tender_capacity_bdt DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS canonical_contractor_dna")
    op.execute("DROP TABLE IF EXISTS canonical_app_packages")
    op.execute("DROP TABLE IF EXISTS canonical_awards")
    for name in ("staging_econtracts", "staging_ecms_ongoing", "staging_app_packages", "staging_awards"):
        op.execute(f"DROP TABLE IF EXISTS {name}")
