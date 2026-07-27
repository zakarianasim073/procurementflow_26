"""Add raw JSON preservation and canonical repair queue.

Revision ID: 014_raw_repair_queue
Revises: 013_canonical_identity
Create Date: 2026-07-05
"""
from __future__ import annotations

from alembic import op


revision = "014_raw_repair_queue"
down_revision = "013_canonical_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS raw")
    op.execute("CREATE SCHEMA IF NOT EXISTS staging")
    op.execute("CREATE SCHEMA IF NOT EXISTS canonical")
    op.execute("CREATE SCHEMA IF NOT EXISTS intelligence")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_import_batches (
            batch_id TEXT PRIMARY KEY,
            source_root TEXT NOT NULL,
            file_count INTEGER NOT NULL DEFAULT 0,
            record_count BIGINT NOT NULL DEFAULT 0,
            total_bytes BIGINT NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'started',
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            finished_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_json_documents (
            raw_id TEXT PRIMARY KEY,
            batch_id TEXT REFERENCES raw_import_batches(batch_id) ON DELETE SET NULL,
            source_family TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_index INTEGER NOT NULL DEFAULT 0,
            source_size_bytes BIGINT NOT NULL DEFAULT 0,
            source_mtime TIMESTAMPTZ,
            record_key TEXT,
            package_no TEXT,
            tender_id TEXT,
            contractor_name TEXT,
            amount_raw TEXT,
            raw_payload JSONB NOT NULL,
            payload_sha256 TEXT NOT NULL,
            imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (source_path, source_index, payload_sha256)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS canonical_identity_repair_queue (
            repair_id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            entity_key TEXT NOT NULL,
            source_table TEXT NOT NULL,
            source_id TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
            severity TEXT NOT NULL DEFAULT 'medium',
            status TEXT NOT NULL DEFAULT 'open',
            suggested_action TEXT,
            evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            resolved_at TIMESTAMPTZ,
            UNIQUE (entity_type, source_table, source_id, issue_type)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_raw_json_family ON raw_json_documents (source_family)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_raw_json_package ON raw_json_documents (package_no)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_raw_json_tender ON raw_json_documents (tender_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_raw_json_hash ON raw_json_documents (payload_sha256)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_repair_queue_status ON canonical_identity_repair_queue (status, severity)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_repair_queue_entity ON canonical_identity_repair_queue (entity_type, entity_key)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS canonical_identity_repair_queue")
    op.execute("DROP TABLE IF EXISTS raw_json_documents")
    op.execute("DROP TABLE IF EXISTS raw_import_batches")
    op.execute("DROP SCHEMA IF EXISTS intelligence")
    op.execute("DROP SCHEMA IF EXISTS canonical")
    op.execute("DROP SCHEMA IF EXISTS staging")
    op.execute("DROP SCHEMA IF EXISTS raw")
