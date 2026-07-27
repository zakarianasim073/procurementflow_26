"""Create crawler framework tables (crawl_jobs, raw_crawl_data, etc.)

This migration creates the 6 core tables for the enterprise crawler
framework at backend/crawler/database/models.py:

  - crawl_jobs         — Crawl job tracking (per-plugin run)
  - raw_crawl_data     — Raw JSON payload storage (dual-path with JSONL)
  - crawl_checkpoints  — Checkpoint/resume state
  - crawl_documents    — Downloaded document metadata (PDF/ZIP paths)
  - crawl_change_log   — Change detection history
  - crawl_errors       — Crawl error log

Revision ID: 017_crawl_framework_tables
Revises: 016_hot_query_indexes
Create Date: 2026-07-07
"""
from __future__ import annotations

from alembic import op


revision = "017_crawl_framework_tables"
down_revision = "016_hot_query_indexes"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        -- Raw crawl data table
        CREATE TABLE IF NOT EXISTS raw_crawl_data (
            id BIGSERIAL PRIMARY KEY,
            table_name VARCHAR(100) NOT NULL,
            source VARCHAR(100) NOT NULL,
            data JSONB NOT NULL,
            data_hash VARCHAR(64),
            crawled_at TIMESTAMPTZ DEFAULT NOW(),
            processed BOOLEAN DEFAULT FALSE,
            processed_at TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS ix_raw_data_table ON raw_crawl_data(table_name);
        CREATE INDEX IF NOT EXISTS ix_raw_data_source ON raw_crawl_data(source);
        CREATE INDEX IF NOT EXISTS ix_raw_data_crawled ON raw_crawl_data(crawled_at);
        CREATE INDEX IF NOT EXISTS ix_raw_data_hash ON raw_crawl_data(data_hash);

        -- Crawl jobs for tracking
        CREATE TABLE IF NOT EXISTS crawl_jobs (
            id BIGSERIAL PRIMARY KEY,
            plugin VARCHAR(100) NOT NULL,
            run_id VARCHAR(50) UNIQUE NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            started_at TIMESTAMPTZ,
            finished_at TIMESTAMPTZ,
            pages_done INT DEFAULT 0,
            items_done INT DEFAULT 0,
            items_skipped INT DEFAULT 0,
            items_failed INT DEFAULT 0,
            error TEXT,
            config JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_crawl_jobs_plugin ON crawl_jobs(plugin);
        CREATE INDEX IF NOT EXISTS ix_crawl_jobs_status ON crawl_jobs(status);

        -- Checkpoints for resume capability
        CREATE TABLE IF NOT EXISTS crawl_checkpoints (
            id BIGSERIAL PRIMARY KEY,
            plugin VARCHAR(100) NOT NULL,
            checkpoint_key VARCHAR(200) NOT NULL,
            data JSONB NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(plugin, checkpoint_key)
        );
        CREATE INDEX IF NOT EXISTS ix_checkpoint_plugin ON crawl_checkpoints(plugin);

        -- Documents downloaded
        CREATE TABLE IF NOT EXISTS crawl_documents (
            id BIGSERIAL PRIMARY KEY,
            tender_id VARCHAR(50) NOT NULL,
            doc_type VARCHAR(50) NOT NULL,
            filename VARCHAR(255) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            file_size BIGINT DEFAULT 0,
            file_hash VARCHAR(64),
            source_url TEXT,
            minio_path VARCHAR(500),
            downloaded_at TIMESTAMPTZ DEFAULT NOW(),
            metadata JSONB
        );
        CREATE INDEX IF NOT EXISTS ix_doc_tender_id ON crawl_documents(tender_id);
        CREATE INDEX IF NOT EXISTS ix_doc_type ON crawl_documents(doc_type);

        -- Change log for version history
        CREATE TABLE IF NOT EXISTS crawl_change_log (
            id BIGSERIAL PRIMARY KEY,
            table_name VARCHAR(100) NOT NULL,
            record_id VARCHAR(100),
            change_type VARCHAR(20) NOT NULL,
            previous_data JSONB,
            new_data JSONB,
            changed_fields JSONB,
            detected_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_change_log_table ON crawl_change_log(table_name);
        CREATE INDEX IF NOT EXISTS ix_change_log_time ON crawl_change_log(detected_at);

        -- Error tracking
        CREATE TABLE IF NOT EXISTS crawl_errors (
            id BIGSERIAL PRIMARY KEY,
            run_id VARCHAR(50),
            plugin VARCHAR(100) NOT NULL,
            error_type VARCHAR(100) NOT NULL,
            error_message TEXT NOT NULL,
            url TEXT,
            traceback TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_error_plugin ON crawl_errors(plugin);
        CREATE INDEX IF NOT EXISTS ix_error_type ON crawl_errors(error_type);
        """
    )


def downgrade():
    op.execute(
        """
        DROP TABLE IF EXISTS crawl_errors;
        DROP TABLE IF EXISTS crawl_change_log;
        DROP TABLE IF EXISTS crawl_documents;
        DROP TABLE IF EXISTS crawl_checkpoints;
        DROP TABLE IF EXISTS crawl_jobs;
        DROP TABLE IF EXISTS raw_crawl_data;
        """
    )
