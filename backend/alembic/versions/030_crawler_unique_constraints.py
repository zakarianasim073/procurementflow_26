"""Crawler: unique constraints + missing pf_experience columns.

Fixes two categories of bugs:

1. Missing UNIQUE constraints on pf_awards / pf_debarments / pf_experience /
   pf_documents caused the normalizer ON CONFLICT (id) clause to be dead code
   (id is a BIGSERIAL PK never supplied by INSERT), silently inserting duplicate
   rows instead of updating changed records on re-crawl.

2. pf_experience was missing 26 columns that the normalizer already attempts to
   insert, causing every experience upsert to fail with "column X does not exist".

Revision ID: 030_crawler_unique_constraints
Revises: 029_regulatory_compliance_engine
"""
from __future__ import annotations

from alembic import op

revision = "030_crawler_unique_constraints"
down_revision = "029_regulatory_compliance_engine"
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: add missing columns to pf_experience
    op.execute(
        """
        ALTER TABLE pf_experience
            ADD COLUMN IF NOT EXISTS tender_id           VARCHAR(50),
            ADD COLUMN IF NOT EXISTS tender_ref_no       VARCHAR(200),
            ADD COLUMN IF NOT EXISTS package_no          VARCHAR(200),
            ADD COLUMN IF NOT EXISTS package_name        TEXT,
            ADD COLUMN IF NOT EXISTS name_of_work        TEXT,
            ADD COLUMN IF NOT EXISTS contract_no         VARCHAR(200),
            ADD COLUMN IF NOT EXISTS contract_start_date VARCHAR(50),
            ADD COLUMN IF NOT EXISTS contract_end_date   VARCHAR(50),
            ADD COLUMN IF NOT EXISTS work_completion_status VARCHAR(50),
            ADD COLUMN IF NOT EXISTS procurement_nature  VARCHAR(50),
            ADD COLUMN IF NOT EXISTS procurement_method  VARCHAR(50),
            ADD COLUMN IF NOT EXISTS work_category       VARCHAR(200),
            ADD COLUMN IF NOT EXISTS tender_type         VARCHAR(50),
            ADD COLUMN IF NOT EXISTS physical_progress   NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS financial_progress  NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS experience_cert_no  VARCHAR(200),
            ADD COLUMN IF NOT EXISTS pe_office_name      VARCHAR(400),
            ADD COLUMN IF NOT EXISTS organization_name   VARCHAR(400),
            ADD COLUMN IF NOT EXISTS pe_officer_name     VARCHAR(400),
            ADD COLUMN IF NOT EXISTS ministry_division   VARCHAR(400),
            ADD COLUMN IF NOT EXISTS company_name        VARCHAR(400),
            ADD COLUMN IF NOT EXISTS is_jvca             VARCHAR(10),
            ADD COLUMN IF NOT EXISTS remarks             TEXT,
            ADD COLUMN IF NOT EXISTS comments_by_pe      TEXT,
            ADD COLUMN IF NOT EXISTS date_physical_progress  VARCHAR(50),
            ADD COLUMN IF NOT EXISTS date_financial_progress VARCHAR(50),
            ADD COLUMN IF NOT EXISTS tender_publication_date VARCHAR(50),
            ADD COLUMN IF NOT EXISTS details             JSONB;
        """
    )

    # Step 2: backfill — deduplicate BEFORE creating unique indexes
    op.execute(
        """
        WITH dup_awards AS (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY tender_id, package_no, company_id
                ORDER BY id DESC
            ) AS rn
            FROM pf_awards
            WHERE tender_id IS NOT NULL AND company_id IS NOT NULL AND NOT is_deleted
        )
        UPDATE pf_awards SET is_deleted = TRUE
        WHERE id IN (SELECT id FROM dup_awards WHERE rn > 1);
        """
    )
    op.execute(
        """
        WITH dup_docs AS (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY tender_id, doc_type, filename
                ORDER BY id DESC
            ) AS rn
            FROM pf_documents
            WHERE NOT is_deleted
        )
        UPDATE pf_documents SET is_deleted = TRUE
        WHERE id IN (SELECT id FROM dup_docs WHERE rn > 1);
        """
    )
    op.execute(
        """
        WITH dup_exp AS (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY company_id, project_name
                ORDER BY id DESC
            ) AS rn
            FROM pf_experience
            WHERE company_id IS NOT NULL AND project_name IS NOT NULL AND NOT is_deleted
        )
        UPDATE pf_experience SET is_deleted = TRUE
        WHERE id IN (SELECT id FROM dup_exp WHERE rn > 1);
        """
    )
    op.execute(
        """
        WITH dup_deb AS (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY company_id, company_name
                ORDER BY id DESC
            ) AS rn
            FROM pf_debarments
            WHERE company_id IS NOT NULL AND company_name IS NOT NULL AND NOT is_deleted
        )
        UPDATE pf_debarments SET is_deleted = TRUE
        WHERE id IN (SELECT id FROM dup_deb WHERE rn > 1);
        """
    )

    # Step 3: now safe to create unique indexes
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_pf_exp_tender
            ON pf_experience(tender_id) WHERE tender_id IS NOT NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_pf_awards_with_package
            ON pf_awards(tender_id, package_no, company_id)
            WHERE tender_id IS NOT NULL AND company_id IS NOT NULL
              AND package_no IS NOT NULL AND NOT is_deleted;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_pf_awards_no_package
            ON pf_awards(tender_id, company_id)
            WHERE tender_id IS NOT NULL AND company_id IS NOT NULL
              AND package_no IS NULL AND NOT is_deleted;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_pf_documents_natural_key
            ON pf_documents(tender_id, doc_type, filename)
            WHERE NOT is_deleted;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_pf_experience_natural_key
            ON pf_experience(company_id, project_name)
            WHERE company_id IS NOT NULL AND project_name IS NOT NULL
              AND NOT is_deleted;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_pf_debarments_natural_key
            ON pf_debarments(company_id, company_name)
            WHERE company_id IS NOT NULL AND company_name IS NOT NULL
              AND NOT is_deleted;
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS uq_pf_awards_with_package;
        DROP INDEX IF EXISTS uq_pf_awards_no_package;
        DROP INDEX IF EXISTS uq_pf_documents_natural_key;
        DROP INDEX IF EXISTS uq_pf_experience_natural_key;
        DROP INDEX IF EXISTS uq_pf_debarments_natural_key;
        DROP INDEX IF EXISTS ix_pf_exp_tender;
        """
    )
