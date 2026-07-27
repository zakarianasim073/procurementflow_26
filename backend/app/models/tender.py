"""Tender models"""

from sqlalchemy import String, Text, ForeignKey, JSON, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, Dict, Any
import enum
from datetime import datetime

from .base import Base, TimestampMixin, UUIDMixin


class TenderStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    LIVE = "live"
    AWARDED = "awarded"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class DocumentType(str, enum.Enum):
    NOTICE = "notice"
    TDS = "tds"
    TDS_2 = "tds_2"
    BOQ = "boq"
    SOR = "sor"
    TEMPLATE_DOCX = "template_docx"
    TEMPLATE_XLSX = "template_xlsx"
    OTHER = "other"


class Tender(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "tenders"

    # Tenant context (multi-tenancy, nullable for backward compatibility with legacy data)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Owner/User context (canonical API model)
    owner_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )

    # Core identifiers
    tender_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    package_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    invitation_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Description
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    work_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Agency info
    procuring_entity: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    procuring_entity_district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    division: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ministry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    organization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    department_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    agency_target: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Procurement details
    procurement_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    procurement_method: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="egp", nullable=False)

    # Regime (PPR2008 or PPR2025)
    regime: Mapped[str] = mapped_column(String(20), default="PPR2008", nullable=False, index=True)

    # Dates
    publication_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    closing_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    opening_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_selling_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    work_period_start: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    work_period_end: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Financial
    estimated_cost: Mapped[Optional[float]] = mapped_column(nullable=True)
    estimated_amount_bdt: Mapped[Optional[float]] = mapped_column(nullable=True)
    tender_security: Mapped[Optional[float]] = mapped_column(nullable=True)
    completion_period_days: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Status
    # PostgreSQL 17 stores this column as the native ``tenderstatus`` enum
    # whose labels are the Enum member names (ACTIVE, DRAFT, ...). Mapping it
    # as VARCHAR makes asyncpg reject inserts/updates with a datatype mismatch.
    status: Mapped[TenderStatus] = mapped_column(
        SQLEnum(TenderStatus, name="tenderstatus", create_type=False),
        default=TenderStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    is_archived: Mapped[bool] = mapped_column(default=False)

    # SOR/Comparison (canonical API fields)
    sor_agency: Mapped[str] = mapped_column(String(20), default="BWDB", nullable=False)
    zone: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    extracted_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    comparison_results: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Raw data & metadata
    raw_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    source_file: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    _stored_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    _domain: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Lifecycle
    app_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Relationships
    owner: Mapped[Optional["User"]] = relationship("User", back_populates="tenders", foreign_keys=[owner_id])
    documents: Mapped[List["TenderDocument"]] = relationship(
        "TenderDocument", back_populates="tender", lazy="selectin", cascade="all, delete-orphan"
    )
    boq_items: Mapped[List["BOQItem"]] = relationship(
        "BOQItem", back_populates="tender", lazy="selectin", cascade="all, delete-orphan"
    )
    # opening_reports: legacy relationship (OpeningReport in app.db.models only)

    # Indexes (covering legacy + canonical queries)
    __table_args__ = (
        Index("ix_tenders_owner_status", "owner_id", "status"),
        Index("ix_tenders_tender_id", "tender_id"),
        Index("ix_tenders_agency", "procuring_entity"),
        Index("ix_tenders_opening_date", "opening_date"),
    )

    def __repr__(self) -> str:
        display_title = self.title or self.work_name or "unknown"
        return f"<Tender {self.tender_id}: {str(display_title)[:50]}>"


class TenderDocument(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "tender_documents"

    tender_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenders.id"), nullable=False, index=True
    )
    doc_type: Mapped[DocumentType] = mapped_column(
        SQLEnum(DocumentType), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(default=0, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    tender: Mapped["Tender"] = relationship("Tender", back_populates="documents")

    # Indexes
    __table_args__ = (
        Index("ix_tender_docs_tender_type", "tender_id", "doc_type"),
    )

    def __repr__(self) -> str:
        return f"<TenderDocument {self.doc_type}: {self.filename}>"
