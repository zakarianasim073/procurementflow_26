"""Create normalized procurement intelligence schema (Phase 3).

`pf_*` tables form the canonical, queryable layer populated by the crawler
from raw_crawl_data. Namespaced `pf_` to avoid collision with the existing
legacy/agent tables (tenders, documents, organizations, users, tenants, etc.).

This revision also MERGES the two pre-existing branches
(017_crawl_framework_tables and 018_boq_object_keys) into a single head.

Revision ID: 019_normalized_schema
Revises: 017_crawl_framework_tables, 018_boq_object_keys
Create Date: 2026-07-07
"""
from __future__ import annotations

from alembic import op


revision = "019_normalized_schema"
down_revision = ("017_crawl_framework_tables", "018_boq_object_keys")
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        -- Ministries (self-referencing hierarchy)
        CREATE TABLE IF NOT EXISTS pf_ministries (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            code VARCHAR(50),
            parent_ministry_id BIGINT REFERENCES pf_ministries(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64),
            UNIQUE (code)
        );
        CREATE INDEX IF NOT EXISTS ix_pf_ministry_name ON pf_ministries(name);

        -- Geographic divisions
        CREATE TABLE IF NOT EXISTS pf_divisions (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64),
            UNIQUE (name)
        );

        -- Locations (district / upazila under division)
        CREATE TABLE IF NOT EXISTS pf_locations (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            division_id BIGINT REFERENCES pf_divisions(id),
            district VARCHAR(100),
            upazila VARCHAR(100),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64)
        );
        CREATE INDEX IF NOT EXISTS ix_pf_location_district ON pf_locations(district);
        CREATE INDEX IF NOT EXISTS ix_pf_location_division ON pf_locations(division_id);

        -- Organizations under ministries
        CREATE TABLE IF NOT EXISTS pf_organizations (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            ministry_id BIGINT REFERENCES pf_ministries(id),
            org_type VARCHAR(50),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64)
        );
        CREATE INDEX IF NOT EXISTS ix_pf_org_ministry ON pf_organizations(ministry_id);

        -- Procuring entities
        CREATE TABLE IF NOT EXISTS pf_procuring_entities (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(300) NOT NULL,
            organization_id BIGINT REFERENCES pf_organizations(id),
            office VARCHAR(200),
            location_id BIGINT REFERENCES pf_locations(id),
            agency_code VARCHAR(20),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64),
            UNIQUE (name, organization_id)
        );
        CREATE INDEX IF NOT EXISTS ix_pf_pe_agency ON pf_procuring_entities(agency_code);
        CREATE INDEX IF NOT EXISTS ix_pf_pe_location ON pf_procuring_entities(location_id);

        -- APP (Annual Procurement Plan) -- created BEFORE projects/packages
        CREATE TABLE IF NOT EXISTS pf_apps (
            id BIGSERIAL PRIMARY KEY,
            app_id VARCHAR(50) NOT NULL,
            title VARCHAR(400),
            ministry_id BIGINT REFERENCES pf_ministries(id),
            procuring_entity_id BIGINT REFERENCES pf_procuring_entities(id),
            financial_year VARCHAR(20),
            total_budget NUMERIC(18,2),
            status VARCHAR(50),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64),
            UNIQUE (app_id, financial_year)
        );
        CREATE INDEX IF NOT EXISTS ix_pf_app_pe ON pf_apps(procuring_entity_id);

        -- Tenders (core entity) -- created BEFORE projects/packages
        CREATE TABLE IF NOT EXISTS pf_tenders (
            id BIGSERIAL PRIMARY KEY,
            tender_id VARCHAR(50) NOT NULL,
            package_no VARCHAR(100),
            app_id BIGINT REFERENCES pf_apps(id),
            procuring_entity_id BIGINT REFERENCES pf_procuring_entities(id),
            title TEXT,
            invitation_ref VARCHAR(100),
            status VARCHAR(50),
            publish_date VARCHAR(50),
            closing_date VARCHAR(50),
            publish_datetime TIMESTAMPTZ,
            closing_datetime TIMESTAMPTZ,
            document_price NUMERIC(18,2),
            category VARCHAR(50),
            procurement_nature VARCHAR(50),
            procurement_type VARCHAR(50),
            procurement_method VARCHAR(50),
            pe_office VARCHAR(200),
            district VARCHAR(100),
            agency_code VARCHAR(20),
            source_url TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64),
            UNIQUE (tender_id, package_no)
        );
        CREATE INDEX IF NOT EXISTS ix_pf_tender_pe ON pf_tenders(procuring_entity_id);
        CREATE INDEX IF NOT EXISTS ix_pf_tender_agency ON pf_tenders(agency_code);
        CREATE INDEX IF NOT EXISTS ix_pf_tender_closing ON pf_tenders(closing_datetime);
        CREATE INDEX IF NOT EXISTS ix_pf_tender_status ON pf_tenders(status);

        -- Projects
        CREATE TABLE IF NOT EXISTS pf_projects (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(400) NOT NULL,
            procuring_entity_id BIGINT REFERENCES pf_procuring_entities(id),
            app_id BIGINT REFERENCES pf_apps(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64)
        );
        CREATE INDEX IF NOT EXISTS ix_pf_project_pe ON pf_projects(procuring_entity_id);

        -- Packages (bridge APP <-> Tender)
        CREATE TABLE IF NOT EXISTS pf_packages (
            id BIGSERIAL PRIMARY KEY,
            package_no VARCHAR(100) NOT NULL,
            app_id BIGINT REFERENCES pf_apps(id),
            tender_id BIGINT REFERENCES pf_tenders(id),
            title VARCHAR(400),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64),
            UNIQUE (package_no, app_id)
        );
        CREATE INDEX IF NOT EXISTS ix_pf_pkg_tender ON pf_packages(tender_id);

        -- Lots
        CREATE TABLE IF NOT EXISTS pf_lots (
            id BIGSERIAL PRIMARY KEY,
            tender_id BIGINT NOT NULL REFERENCES pf_tenders(id),
            lot_no VARCHAR(100),
            description TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64)
        );
        CREATE INDEX IF NOT EXISTS ix_pf_lot_tender ON pf_lots(tender_id);

        -- Documents (normalized layer; framework downloads tracked in crawl_documents)
        CREATE TABLE IF NOT EXISTS pf_documents (
            id BIGSERIAL PRIMARY KEY,
            tender_id VARCHAR(50),
            doc_type VARCHAR(50) NOT NULL,
            filename VARCHAR(255) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            file_size BIGINT DEFAULT 0,
            file_hash VARCHAR(64),
            source_url TEXT,
            minio_path VARCHAR(500),
            downloaded_at TIMESTAMPTZ DEFAULT NOW(),
            metadata JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64)
        );
        CREATE INDEX IF NOT EXISTS ix_pf_doc_tender ON pf_documents(tender_id);
        CREATE INDEX IF NOT EXISTS ix_pf_doc_type ON pf_documents(doc_type);

        -- Companies (contractors / winners)
        CREATE TABLE IF NOT EXISTS pf_companies (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(400) NOT NULL,
            registration_no VARCHAR(100),
            address TEXT,
            district VARCHAR(100),
            contact VARCHAR(100),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64),
            UNIQUE (registration_no)
        );
        CREATE INDEX IF NOT EXISTS ix_pf_company_name ON pf_companies(name);
        CREATE INDEX IF NOT EXISTS ix_pf_company_district ON pf_companies(district);

        -- Awards
        CREATE TABLE IF NOT EXISTS pf_awards (
            id BIGSERIAL PRIMARY KEY,
            award_id VARCHAR(50),
            tender_id VARCHAR(50),
            package_no VARCHAR(100),
            company_id BIGINT REFERENCES pf_companies(id),
            procuring_entity_id BIGINT REFERENCES pf_procuring_entities(id),
            title TEXT,
            award_date VARCHAR(50),
            award_datetime TIMESTAMPTZ,
            contract_value NUMERIC(18,2),
            status VARCHAR(50),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64)
        );
        CREATE INDEX IF NOT EXISTS ix_pf_award_company ON pf_awards(company_id);
        CREATE INDEX IF NOT EXISTS ix_pf_award_tender ON pf_awards(tender_id);
        CREATE INDEX IF NOT EXISTS ix_pf_award_pe ON pf_awards(procuring_entity_id);

        -- Experience (eExperience records)
        CREATE TABLE IF NOT EXISTS pf_experience (
            id BIGSERIAL PRIMARY KEY,
            experience_id VARCHAR(50),
            company_id BIGINT REFERENCES pf_companies(id),
            project_name TEXT,
            procuring_entity_id BIGINT REFERENCES pf_procuring_entities(id),
            contract_value NUMERIC(18,2),
            completion_date VARCHAR(50),
            completion_datetime TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64)
        );
        CREATE INDEX IF NOT EXISTS ix_pf_exp_company ON pf_experience(company_id);
        CREATE INDEX IF NOT EXISTS ix_pf_exp_pe ON pf_experience(procuring_entity_id);

        -- Debarments
        CREATE TABLE IF NOT EXISTS pf_debarments (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT REFERENCES pf_companies(id),
            company_name VARCHAR(400),
            authority VARCHAR(200),
            reason TEXT,
            start_date VARCHAR(50),
            end_date VARCHAR(50),
            status VARCHAR(50),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64)
        );
        CREATE INDEX IF NOT EXISTS ix_pf_deb_company ON pf_debarments(company_id);

        -- Categories (CPV / works categories)
        CREATE TABLE IF NOT EXISTS pf_categories (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            code VARCHAR(50),
            parent_id BIGINT REFERENCES pf_categories(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            version INT NOT NULL DEFAULT 1,
            tenant_id BIGINT,
            source VARCHAR(100),
            data_hash VARCHAR(64),
            UNIQUE (code)
        );
        """
    )


def downgrade():
    op.execute(
        """
        DROP TABLE IF EXISTS pf_categories;
        DROP TABLE IF EXISTS pf_debarments;
        DROP TABLE IF EXISTS pf_experience;
        DROP TABLE IF EXISTS pf_awards;
        DROP TABLE IF EXISTS pf_companies;
        DROP TABLE IF EXISTS pf_documents;
        DROP TABLE IF EXISTS pf_lots;
        DROP TABLE IF EXISTS pf_packages;
        DROP TABLE IF EXISTS pf_projects;
        DROP TABLE IF EXISTS pf_tenders;
        DROP TABLE IF EXISTS pf_apps;
        DROP TABLE IF EXISTS pf_procuring_entities;
        DROP TABLE IF EXISTS pf_organizations;
        DROP TABLE IF EXISTS pf_locations;
        DROP TABLE IF EXISTS pf_divisions;
        DROP TABLE IF EXISTS pf_ministries;
        """
    )
