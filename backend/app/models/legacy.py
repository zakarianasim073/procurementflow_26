"""Legacy-only models ported from app.db.models.

These tables have no canonical equivalent and are preserved for backward
compatibility with existing data. No new code should depend on these models.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, JSON, Numeric, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    """Legacy tender documents (NIT, TDS, BOQ, Drawings, etc.).

    Serves the e-GP document extraction pipeline. Distinct from the canonical
    TenderDocument model which manages uploaded user documents.
    """

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tender_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    doc_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    doc_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ocr_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ocr_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_mapped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mapping_errors: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_documents_tender_id", "tender_id"),
    )

    def __repr__(self) -> str:
        return f"<Document {self.id}: {self.doc_type}>"


class Lifecycle(Base):
    """APP to Tender to Award lifecycle matching."""

    __tablename__ = "lifecycle"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    app_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    tender_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    award_tender_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    match_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    variance_amount: Mapped[Optional[float]] = mapped_column(nullable=True)
    variance_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lifecycle_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_lifecycle_app_id", "app_id"),
        Index("ix_lifecycle_tender_id", "tender_id"),
        Index("ix_lifecycle_award_tender_id", "award_tender_id"),
    )

    def __repr__(self) -> str:
        return f"<Lifecycle {self.id}>"


class Ruleset(Base):
    """Versioned rulesets for PPR and compliance evaluation."""

    __tablename__ = "rulesets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ruleset_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    rules: Mapped[dict] = mapped_column(JSON, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_rulesets_tenant_id", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<Ruleset {self.name} v{self.version}>"


class PPRSchedule(Base):
    """PPR Schedule evaluation results."""

    __tablename__ = "ppr_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    agent_result_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agent_results.id"), nullable=True)
    tender_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    schedule_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    schedule_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    criteria: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    total_marks: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_marks: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<PPRSchedule {self.id}: {self.schedule_type}>"


class ComplianceCheck(Base):
    """Individual compliance checks."""

    __tablename__ = "compliance_checks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    agent_result_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agent_results.id"), nullable=True)
    tender_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    check_name: Mapped[str] = mapped_column(String(255), nullable=False)
    check_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<ComplianceCheck {self.id}: {self.check_name}>"


class FeedbackLabel(Base):
    """Human feedback for agent outputs (training data)."""

    __tablename__ = "feedback_labels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    agent_result_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agent_results.id"), nullable=True, index=True)
    tender_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    label: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    score_adjustment: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reviewer_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<FeedbackLabel {self.id}: {self.label}>"


class TenderPreparation(Base):
    """Tender preparation workflow — forms, documents, mapping."""

    __tablename__ = "tender_preparations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tender_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    forms_required: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    forms_completed: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    forms_missing: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    document_map: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="not_started", nullable=False)
    completeness_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    contract_signing_required: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    contract_signing_completed: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_tender_preparations_tender_id", "tender_id"),
    )

    def __repr__(self) -> str:
        return f"<TenderPreparation {self.id}: {self.status}>"


class UserQuery(Base):
    """Track user queries for continuous learning."""

    __tablename__ = "user_queries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    query_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    query_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tender_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    response_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    was_cached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_satisfaction: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<UserQuery {self.id}: {self.query_type}>"


class LegacyTenderDocument(Base):
    """Legacy tender documents with extraction tracking fields.

    Serves the e-GP document extraction pipeline. Distinguished from canonical
    TenderDocument by including extraction_method, extraction_status, page_count,
    format, content_text, and content_json fields used only by the crawler pipeline.

    NOTE: This uses a different table name (tender_documents_extracted) to avoid
    conflict with canonical TenderDocument which owns the tender_documents table.
    """

    __tablename__ = "tender_documents_extracted"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tender_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    doc_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    filename: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extraction_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    extraction_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_tender_documents_extracted_tender_id", "tender_id"),
    )

    def __repr__(self) -> str:
        return f"<LegacyTenderDocument {self.id}: {self.doc_type}>"


class UserLegacy(Base):
    """Legacy user model.

    DEPRECATED — canonical User model lives in app.models.user.
    This model is preserved for backward compatibility with legacy tables/data
    that may still reference the legacy user schema with tenant_id FK.
    """

    __tablename__ = "users_legacy"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="viewer", nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<UserLegacy {self.id}: {self.email}>"


class APPRecordLegacy(Base):
    """Legacy APP record.

    DEPRECATED — canonical APPRecord lives in app.models.intelligence.
    """

    __tablename__ = "app_records_legacy"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tender_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    app_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    agency: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    department_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    agency_target: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estimated_amount_bdt: Mapped[Optional[float]] = mapped_column(nullable=True)
    procurement_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    package_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    work_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_file: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_app_records_legacy_tender_id", "tender_id"),
        Index("ix_app_records_legacy_agency", "agency"),
    )

    def __repr__(self) -> str:
        return f"<APPRecordLegacy {self.id}>"


class ContractorLegacy(Base):
    """Legacy contractor profile.

    DEPRECATED — canonical Contractor lives in app.models.intelligence.
    """

    __tablename__ = "contractors_legacy"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contractor_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True, index=True)
    company_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    registration_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    total_awards: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_award_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    preferred_agencies: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    preferred_zones: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    preferred_project_sizes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    activity_trend: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    equipment_list: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    key_personnel: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    dna_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_contractors_legacy_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<ContractorLegacy {self.id}: {self.name}>"
