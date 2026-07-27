"""Normalized Procurement Intelligence schema (Phase 3).

These `pf_*` tables are the canonical, queryable layer populated by the crawler
from raw_crawl_data. They use BIGINT surrogate keys for join performance at
scale (millions of tenders/awards), with audit fields, soft delete, versioning
and a tenant_id for future multi-tenant SaaS.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from decimal import Decimal

from sqlalchemy import (
    Column, String, Integer, BigInteger, Numeric, DateTime, Text, JSON,
    Boolean, Index, UniqueConstraint, ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .models import Base


# Audit mixin columns shared by every normalized table
def _audit_columns() -> tuple:
    return (
        Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
        Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False),
        Column("is_deleted", Boolean, default=False, nullable=False),
        Column("version", Integer, default=1, nullable=False),
        Column("tenant_id", BigInteger, nullable=True),
        Column("source", String(100), nullable=True),
        Column("data_hash", String(64), nullable=True),
    )


class PfMinistry(Base):
    __tablename__ = "pf_ministries"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    parent_ministry_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_ministries.id"), nullable=True)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (
        UniqueConstraint("code", name="uq_pf_ministry_code"),
        Index("ix_pf_ministry_name", "name"),
    )


class PfDivision(Base):
    __tablename__ = "pf_divisions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (UniqueConstraint("name", name="uq_pf_division_name"),)


class PfLocation(Base):
    __tablename__ = "pf_locations"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    division_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_divisions.id"), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    upazila: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (
        Index("ix_pf_location_district", "district"),
        Index("ix_pf_location_division", "division_id"),
    )


class PfOrganization(Base):
    __tablename__ = "pf_organizations"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ministry_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_ministries.id"), nullable=True)
    org_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (Index("ix_pf_org_ministry", "ministry_id"),)


class PfProcuringEntity(Base):
    __tablename__ = "pf_procuring_entities"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_organizations.id"), nullable=True)
    office: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_locations.id"), nullable=True)
    agency_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (
        UniqueConstraint("name", "organization_id", name="uq_pf_pe_name_org"),
        Index("ix_pf_pe_agency", "agency_code"),
        Index("ix_pf_pe_location", "location_id"),
    )


class PfProject(Base):
    __tablename__ = "pf_projects"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(400), nullable=False)
    procuring_entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_procuring_entities.id"), nullable=True)
    app_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_apps.id"), nullable=True)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (Index("ix_pf_project_pe", "procuring_entity_id"),)


class PfApp(Base):
    """Annual Procurement Plan entry (APP)."""
    __tablename__ = "pf_apps"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    app_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    ministry_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_ministries.id"), nullable=True)
    procuring_entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_procuring_entities.id"), nullable=True)
    financial_year: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    total_budget: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (
        UniqueConstraint("app_id", "financial_year", name="uq_pf_app_id_year"),
        Index("ix_pf_app_pe", "procuring_entity_id"),
    )


class PfPackage(Base):
    __tablename__ = "pf_packages"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    package_no: Mapped[str] = mapped_column(String(100), nullable=False)
    app_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_apps.id"), nullable=True)
    tender_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_tenders.id"), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (
        UniqueConstraint("package_no", "app_id", name="uq_pf_pkg_no_app"),
        Index("ix_pf_pkg_tender", "tender_id"),
    )


class PfTender(Base):
    __tablename__ = "pf_tenders"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tender_id: Mapped[str] = mapped_column(String(50), nullable=False)
    package_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    app_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_apps.id"), nullable=True)
    procuring_entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_procuring_entities.id"), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    invitation_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    publish_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    closing_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    publish_datetime: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    closing_datetime: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    document_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    procurement_nature: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    procurement_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    procurement_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    pe_office: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    agency_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (
        UniqueConstraint("tender_id", "package_no", name="uq_pf_tender_id_pkg"),
        Index("ix_pf_tender_pe", "procuring_entity_id"),
        Index("ix_pf_tender_agency", "agency_code"),
        Index("ix_pf_tender_closing", "closing_datetime"),
        Index("ix_pf_tender_status", "status"),
    )


class PfLot(Base):
    __tablename__ = "pf_lots"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tender_id: Mapped[int] = mapped_column(ForeignKey("pf_tenders.id"), nullable=False)
    lot_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (Index("ix_pf_lot_tender", "tender_id"),)


class PfDocument(Base):
    __tablename__ = "pf_documents"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tender_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    minio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    downloaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    doc_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON, nullable=True)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (
        Index("ix_pf_doc_tender", "tender_id"),
        Index("ix_pf_doc_type", "doc_type"),
    )


class PfCompany(Base):
    __tablename__ = "pf_companies"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(400), nullable=False)
    registration_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (
        UniqueConstraint("registration_no", name="uq_pf_company_reg"),
        Index("ix_pf_company_name", "name"),
        Index("ix_pf_company_district", "district"),
    )


class PfAward(Base):
    __tablename__ = "pf_awards"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    award_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tender_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    package_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_companies.id"), nullable=True)
    procuring_entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_procuring_entities.id"), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    award_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    award_datetime: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    contract_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (
        Index("ix_pf_award_company", "company_id"),
        Index("ix_pf_award_tender", "tender_id"),
        Index("ix_pf_award_pe", "procuring_entity_id"),
    )


class PfExperience(Base):
    __tablename__ = "pf_experience"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    experience_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_companies.id"), nullable=True)
    project_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    procuring_entity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_procuring_entities.id"), nullable=True)
    contract_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    completion_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    completion_datetime: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (
        Index("ix_pf_exp_company", "company_id"),
        Index("ix_pf_exp_pe", "procuring_entity_id"),
    )


class PfDebarment(Base):
    __tablename__ = "pf_debarments"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_companies.id"), nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    authority: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (Index("ix_pf_deb_company", "company_id"),)


class PfCategory(Base):
    __tablename__ = "pf_categories"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pf_categories.id"), nullable=True)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (UniqueConstraint("code", name="uq_pf_category_code"),)


class PfRelationship(Base):
    """Explicit directed edge between two normalized entities.

    Enables graph traversal without N+1 FK joins. Each row is a
    typed, directed relationship with optional metadata payload.
    """
    __tablename__ = "pf_relationships"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rel_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), default=1.0)
    discovered_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at = _audit_columns()[0]
    updated_at = _audit_columns()[1]
    is_deleted = _audit_columns()[2]
    version = _audit_columns()[3]
    tenant_id = _audit_columns()[4]
    source = _audit_columns()[5]
    data_hash = _audit_columns()[6]
    __table_args__ = (
        Index("ix_pf_rel_source", "source_type", "source_id"),
        Index("ix_pf_rel_target", "target_type", "target_id"),
        Index("ix_pf_rel_type", "relationship_type"),
        UniqueConstraint(
            "source_type", "source_id", "target_type", "target_id", "relationship_type",
            name="uq_pf_rel_edge",
        ),
    )


# Expose the list for alembic / metadata binding
NORMALIZED_MODELS = [
    PfMinistry, PfDivision, PfLocation, PfOrganization, PfProcuringEntity,
    PfProject, PfApp, PfPackage, PfTender, PfLot, PfDocument, PfCompany,
    PfAward, PfExperience, PfDebarment, PfCategory, PfRelationship,
]
