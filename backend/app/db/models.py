"""
Procurement Flow Specialist BD — SQLAlchemy Models
PostgreSQL-only schema.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, Float, BigInteger, Text, DateTime,
    Boolean, ForeignKey, JSON, Enum, Numeric, Index, UniqueConstraint,
    LargeBinary, Date, TIMESTAMP
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


# ── Enums ────────────────────────────────────────────────────────────────

class TenderStatus(str, enum.Enum):
    LIVE = "live"
    ARCHIVED = "archived"
    AWARDED = "awarded"
    CANCELLED = "cancelled"
    DRAFT = "draft"


class AgentStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class DocumentType(str, enum.Enum):
    NIT = "nit"
    TDS = "tds"
    BOQ = "boq"
    DRAWING = "drawing"
    CORRIGENDUM = "corrigendum"
    SPECIFICATION = "specification"
    OPENING_REPORT = "opening_report"
    CONTRACT = "contract"
    OTHER = "other"


# ── Multi-Tenant Core ────────────────────────────────────────────────────

# ⚠️ DEPRECATED — Tenant and Organization moved to canonical app.models.enterprise
# Import shims kept for backward compatibility with legacy code only.
# New code must import from app.models.enterprise

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255))
    role = Column(String(50), default="viewer")  # admin, estimator, viewer
    password_hash = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    last_login = Column(DateTime(timezone=True))
    
    # Legacy compatibility mapper uses a separate SQLAlchemy registry from the
    # canonical enterprise Tenant model. A string relationship across those
    # registries cannot resolve and prevented every legacy mapper from
    # initializing. Consumers join by tenant_id; canonical models own relations.


# ── Procurement Core ─────────────────────────────────────────────────────

# ⚠️ DEPRECATED — Use canonical app.models.Tender instead
# This import shim is kept for backward compatibility with legacy ETL/crawler code.
# The table is created from app.models.Tender (canonical); this is a re-export only.
# New code must import from app.models.tender


# ⚠️ DEPRECATED — Award moved to canonical app.models.procurement
# Import shim kept for backward compatibility with legacy code only.
# New code must import from app.models.procurement


class APPRecord(Base):
    """Annual Procurement Plan records."""
    __tablename__ = "app_records"
    __table_args__ = (
        Index("idx_app_tender_id", "tender_id"),
        Index("idx_app_agency", "agency"),
    )
    
    id = Column(String(36), primary_key=True, default=_uuid)
    tender_id = Column(String(100), index=True)
    app_id = Column(String(100), index=True)
    
    agency = Column(String(255), index=True)
    department_id = Column(String(100))
    agency_target = Column(String(255))
    
    title = Column(Text)
    estimated_amount_bdt = Column(Numeric(16, 2))
    procurement_type = Column(String(255))
    package_no = Column(String(255))
    
    work_name = Column(Text)
    status = Column(String(50), default="active")
    is_archived = Column(Boolean, default=False)
    source = Column(String(255))
    source_file = Column(String(500))
    raw_data = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class Contractor(Base):
    """Contractor profiles and DNA."""
    __tablename__ = "contractors"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False, index=True)
    contractor_id = Column(String(100), unique=True, index=True)
    
    # Profile
    company_type = Column(String(100))
    registration_no = Column(String(100))
    address = Column(Text)
    contact = Column(String(255))
    
    # DNA metrics (computed)
    total_awards = Column(Integer, default=0)
    total_award_value = Column(Numeric(16, 2), default=0)
    win_rate = Column(Float, default=0.0)
    preferred_agencies = Column(JSON)
    preferred_zones = Column(JSON)
    preferred_project_sizes = Column(JSON)
    activity_trend = Column(JSON)
    
    # Equipment & capacity
    equipment_list = Column(JSON)
    key_personnel = Column(JSON)
    
    # Status
    is_blacklisted = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    raw_data = Column(JSON)
    dna_updated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class Lifecycle(Base):
    """APP ↔ Tender ↔ Award lifecycle matching."""
    __tablename__ = "lifecycle"
    __table_args__ = (
        Index("idx_lifecycle_app", "app_id"),
        Index("idx_lifecycle_tender", "tender_id"),
        Index("idx_lifecycle_award", "award_tender_id"),
    )
    
    id = Column(String(36), primary_key=True, default=_uuid)
    app_id = Column(String(100), index=True)
    tender_id = Column(String(100), index=True)
    award_tender_id = Column(String(100), index=True)
    
    match_confidence = Column(Float)
    variance_amount = Column(Numeric(16, 2))
    variance_pct = Column(Float)
    lifecycle_stage = Column(String(50))  # app_to_tender, tender_to_award, complete
    
    raw_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ⚠️ DEPRECATED — OpeningReport moved to canonical app.models.procurement
# Import shim kept for backward compatibility with legacy code only.
# New code must import from app.models.procurement


class Document(Base):
    """Tender documents (NIT, TDS, BOQ, Drawings, etc.)."""
    __tablename__ = "documents"
    __table_args__ = (
        Index("idx_doc_tender_id", "tender_id"),
    )
    
    id = Column(String(36), primary_key=True, default=_uuid)
    tender_id = Column(String(100), ForeignKey("tenders.tender_id"), nullable=False, index=True)
    
    doc_type = Column(String(50), nullable=False)  # nit, tds, boq, drawing, etc.
    doc_name = Column(String(255))
    file_path = Column(String(500))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    
    # Extracted data
    extracted_text = Column(Text)
    extracted_data = Column(JSON)
    ocr_required = Column(Boolean, default=False)
    ocr_done = Column(Boolean, default=False)
    
    # Status
    is_mapped = Column(Boolean, default=False)  # mapped to form fields
    mapping_errors = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


# ── Agent System ─────────────────────────────────────────────────────────

class AgentResult(Base):
    """Store all agent execution results."""
    __tablename__ = "agent_results"
    __table_args__ = (
        Index("idx_agent_result_agent", "agent_id"),
        Index("idx_agent_result_tender", "tender_id"),
        Index("idx_agent_result_status", "status"),
    )
    
    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True)
    
    agent_id = Column(String(50), nullable=False, index=True)
    agent_name = Column(String(255))
    agent_version = Column(String(20))
    
    request_id = Column(String(36), index=True)
    tender_id = Column(String(100), index=True)
    
    status = Column(String(20), default="pending")  # pending, running, success, failed
    output = Column(JSON)
    error = Column(Text)
    
    execution_time_ms = Column(Integer)
    model_used = Column(String(100))
    
    # Provenance
    trace_id = Column(String(36))
    source_ids = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class AgentLog(Base):
    """Agent execution logs."""
    __tablename__ = "agent_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    result_id = Column(String(36), ForeignKey("agent_results.id"), index=True)
    agent_id = Column(String(50), index=True)
    tender_id = Column(String(100), index=True)
    
    level = Column(String(10), default="INFO")  # DEBUG, INFO, WARNING, ERROR
    message = Column(Text)
    meta = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class AgentJob(Base):
    """Agent job queue."""
    __tablename__ = "agent_jobs"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True)
    
    agent_id = Column(String(50), nullable=False, index=True)
    request_id = Column(String(36), index=True)
    tender_id = Column(String(100), index=True)
    
    state = Column(String(20), default="pending")  # pending, processing, done, failed
    priority = Column(Integer, default=0)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_error = Column(Text)
    
    input_data = Column(JSON)
    result_id = Column(String(36))
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class AgentBrainMessage(Base):
    """Inter-agent communication messages (Agent Brain)."""
    __tablename__ = "agent_brain_messages"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    
    sender_id = Column(String(50), nullable=False, index=True)
    recipient_id = Column(String(50), index=True)  # None = broadcast
    
    message_type = Column(String(50))  # request, response, broadcast, knowledge_share
    subject = Column(String(255))
    body = Column(JSON)
    thread_id = Column(String(36), index=True)
    
    status = Column(String(20), default="sent")  # sent, delivered, read, responded
    response_to = Column(String(36))  # message_id this is responding to
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ── Knowledge & Learning ─────────────────────────────────────────────────

class KnowledgeEntry(Base):
    """Central Knowledge Lake - all procurement intelligence."""
    __tablename__ = "knowledge_entries"
    __table_args__ = (
        Index("idx_knowledge_tender", "tender_id"),
        Index("idx_knowledge_type", "entry_type"),
        Index("idx_knowledge_embedding", "embedding_id"),
    )
    
    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True)
    tender_id = Column(String(100), ForeignKey("tenders.tender_id"), nullable=True, index=True)
    
    entry_type = Column(String(50), nullable=False, index=True)  # tender, boq, award, competitor, rate, report, opening
    title = Column(String(500))
    content = Column(Text)
    
    # Structured data
    data = Column(JSON)
    summary = Column(Text)
    
    # Source
    source = Column(String(50))
    source_url = Column(String(500))
    source_file = Column(String(255))
    
    # Embedding (for vector search)
    embedding_id = Column(String(100), index=True)
    embedding_model = Column(String(100))
    
    # Tags & categorization
    tags = Column(JSON)
    agency = Column(String(255))
    zone = Column(String(100))
    procurement_type = Column(String(50))
    
    # Lifecycle
    checksum = Column(String(64))
    is_archived = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    
    # The canonical Tender relationship lives in app.models. This compatibility
    # model deliberately remains relationship-free because it has a separate
    # SQLAlchemy registry and is queried directly by tender_id.


# ── Rules & Compliance ───────────────────────────────────────────────────

class Ruleset(Base):
    """Versioned rulesets for PPR and compliance evaluation."""
    __tablename__ = "rulesets"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True)
    
    name = Column(String(255), nullable=False)
    ruleset_type = Column(String(50))  # ppr_evaluation, ppr_compliance, eligibility
    version = Column(String(20), nullable=False)
    
    rules = Column(JSON, nullable=False)  # The actual rules
    description = Column(Text)
    active = Column(Boolean, default=True)
    
    created_by = Column(String(36))
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    
    UniqueConstraint("name", "version", name="uq_ruleset_version")


class PPRSchedule(Base):
    """PPR Schedule 4/5/6 evaluation results."""
    __tablename__ = "ppr_schedules"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    agent_result_id = Column(String(36), ForeignKey("agent_results.id"))
    tender_id = Column(String(100), index=True)
    
    schedule_type = Column(String(20))  # schedule_4, schedule_5, schedule_6
    schedule_label = Column(String(100))
    
    criteria = Column(JSON)  # [{name, score, max_score, passed, details}]
    total_marks = Column(Float)
    max_marks = Column(Float)
    percentage = Column(Float)
    passed = Column(Boolean)
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class ComplianceCheck(Base):
    """Individual compliance checks."""
    __tablename__ = "compliance_checks"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    agent_result_id = Column(String(36), ForeignKey("agent_results.id"))
    tender_id = Column(String(100), index=True)
    
    check_name = Column(String(255), nullable=False)
    check_type = Column(String(50))  # document, eligibility, qualification
    passed = Column(Boolean)
    score = Column(Float)
    max_score = Column(Float)
    details = Column(Text)
    recommendation = Column(Text)
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ── Feedback & Human-in-the-Loop ────────────────────────────────────────

class FeedbackLabel(Base):
    """Human feedback for agent outputs (training data)."""
    __tablename__ = "feedback_labels"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    agent_result_id = Column(String(36), ForeignKey("agent_results.id"), index=True)
    tender_id = Column(String(100), index=True)
    
    label = Column(String(50))  # correct, incorrect, needs_review
    score_adjustment = Column(Float)
    reviewer_comment = Column(Text)
    reviewer_id = Column(String(36))
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ── Tender Preparation ──────────────────────────────────────────────────

class TenderPreparation(Base):
    """Tender preparation workflow - forms, documents, mapping."""
    __tablename__ = "tender_preparations"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    tender_id = Column(String(100), ForeignKey("tenders.tender_id"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True)
    
    # Forms needed
    forms_required = Column(JSON)  # List of forms needed
    forms_completed = Column(JSON)  # List of forms completed
    forms_missing = Column(JSON)  # Forms still missing
    
    # Document mapping
    document_map = Column(JSON)  # form_field → document mapping
    
    # Preparation status
    status = Column(String(50), default="not_started")  # not_started, in_progress, completed
    completeness_pct = Column(Float, default=0.0)
    
    # Contract signing info
    contract_signing_required = Column(JSON)
    contract_signing_completed = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

# ── NPP Records ──────────────────────────────────────────────────────────

class NPPRecord(Base):
    """Negotiated Percentage Below Estimate (NPP) evaluation records."""
    __tablename__ = "npp_records"
    __table_args__ = (
        Index("idx_npp_tender_id", "tender_id"),
        Index("idx_npp_agency", "agency"),
    )
    
    id = Column(String(36), primary_key=True, default=_uuid)
    tender_id = Column(String(100), index=True, nullable=False)
    package_no = Column(String(255))
    work_name = Column(Text)
    pe_office = Column(String(255))
    agency = Column(String(255), index=True)
    zone = Column(String(100))
    estimated_amount_bdt = Column(Numeric(16, 2))
    lowest_bid = Column(Numeric(16, 2))
    bid_average = Column(Numeric(16, 2))
    lowest_percent_below_oe = Column(Numeric(8, 4))
    average_percent_below_oe = Column(Numeric(8, 4))
    bid_spread_percent = Column(Numeric(8, 4))
    bidder_count = Column(Integer, default=0)
    cluster_detected = Column(Boolean, default=False)
    discount_strategy_detected = Column(Boolean, default=False)
    slt_risk = Column(String(50))
    likely_market_discount = Column(Numeric(8, 4))
    source_file = Column(String(500))
    raw_data = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ── PPR Evaluations ──────────────────────────────────────────────────────

class PPREvaluation(Base):
    """PPR (Schedule 4/5/6) evaluation results."""
    __tablename__ = "ppr_evaluations"
    __table_args__ = (
        Index("idx_ppr_tender_id", "tender_id"),
    )
    
    id = Column(String(36), primary_key=True, default=_uuid)
    tender_id = Column(String(100), index=True, nullable=False)
    schedule_type = Column(String(50))  # schedule_4, schedule_5, schedule_6
    schedule_label = Column(String(255))
    criteria = Column(Text)
    total_marks = Column(Numeric(8, 2))
    max_marks = Column(Numeric(8, 2))
    percentage = Column(Numeric(8, 4))
    passed = Column(Boolean, default=False)
    raw_data = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ── Rate Analysis ────────────────────────────────────────────────────────

class TenderDataPool(Base):
    """Central store for all extracted tender data - the Tender Dashboard."""
    __tablename__ = "tender_data_pool"
    __table_args__ = (
        Index("idx_tdp_tender_id", "tender_id"),
    )
    
    def __setattr__(self, key, value):
        """Convert empty strings to None for date columns."""
        if key in ('publication_date', 'closing_date', 'opening_date') and value == '':
            value = None
        super().__setattr__(key, value)
    
    id = Column(String(36), primary_key=True, default=_uuid)
    tender_id = Column(String(100), nullable=False, index=True)
    
    # Basic Info
    package_no = Column(String(100))
    work_name = Column(Text)
    procuring_entity = Column(String(255))
    pe_office = Column(String(255))
    zone = Column(String(100))
    division = Column(String(100))
    district = Column(String(100))
    
    # Schedule & Dates
    publication_date = Column(DateTime)
    closing_date = Column(DateTime)
    opening_date = Column(DateTime)
    tender_security_amount = Column(Numeric(16, 2))
    performance_security_amount = Column(Numeric(16, 2))
    completion_period_days = Column(Integer)
    
    # Financial
    estimated_amount_bdt = Column(Numeric(16, 2))
    tender_fee = Column(Numeric(12, 2))
    
    # Qualification Criteria (from TDS)
    min_experience_years = Column(Integer)
    min_turnover_bdt = Column(Numeric(16, 2))
    min_liquid_assets_bdt = Column(Numeric(16, 2))
    min_annual_construction_volume = Column(Numeric(16, 2))
    similar_works_required = Column(Integer)
    required_equipment = Column(JSON)
    required_personnel = Column(JSON)
    required_licenses = Column(JSON)
    special_qualifications = Column(JSON)
    
    # BOQ Data
    boq_items = Column(JSON)  # Full BOQ with items, quantities, units
    boq_total = Column(Numeric(16, 2))
    
    # Documents
    nit_url = Column(Text)
    tds_url = Column(Text)
    boq_url = Column(Text)
    drawings_url = Column(Text)
    corrigendum_urls = Column(JSON)
    
    # Status
    extraction_status = Column(String(20), default="pending")  # pending, extracting, complete, failed
    source_format = Column(String(10))  # pdf, json, html
    raw_data_ref = Column(Text)  # reference to stored raw data
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class TenderDocument(Base):
    """Stored tender documents (PDFs, JSONs)."""
    __tablename__ = "tender_documents"
    __table_args__ = (
        Index("idx_td_tender_id", "tender_id"),
    )
    
    id = Column(String(36), primary_key=True, default=_uuid)
    tender_id = Column(String(100), nullable=False, index=True)
    doc_type = Column(String(50))  # nit, tds, boq, drawing, corrigendum, other
    filename = Column(String(500))
    format = Column(String(10))  # pdf, json, html
    content_text = Column(Text)  # Extracted text (from PDF/HTML)
    content_json = Column(JSON)  # Structured data (from JSON)
    file_path = Column(String(1000))
    file_size_bytes = Column(Integer)
    page_count = Column(Integer)
    extraction_method = Column(String(50))  # pdf_parser, ocr, json_parse, html_parse
    extraction_status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class TenderReport(Base):
    """Generated tender reports."""
    __tablename__ = "tender_reports"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    tender_id = Column(String(100), nullable=False, index=True)
    report_type = Column(String(50))  # summary, full, qualification, boq, financial
    report_data = Column(JSON)
    summary = Column(Text)
    recommendations = Column(JSON)
    generated_by = Column(String(100))  # agent_id
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class AgentThought(Base):
    """Agent thoughts/insights waiting for human approval."""
    __tablename__ = "agent_thoughts"
    __table_args__ = (
        Index("idx_thought_status", "status"),
        Index("idx_thought_agent", "agent_id"),
    )
    
    id = Column(String(36), primary_key=True, default=_uuid)
    agent_id = Column(String(100), nullable=False, index=True)
    agent_name = Column(String(255))
    tender_id = Column(String(100), index=True)
    thought_type = Column(String(50))  # insight, recommendation, pattern, warning, improvement
    title = Column(String(500))
    description = Column(Text)
    evidence = Column(JSON)  # supporting data
    impact = Column(String(50))  # low, medium, high, critical
    confidence = Column(Float, default=0.0)  # 0-100
    status = Column(String(20), default="pending")  # pending, approved, rejected, implemented
    reviewer_comment = Column(Text)
    approved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class PreComputedIntelligence(Base):
    """Pre-computed intelligence cache for instant query responses."""
    __tablename__ = "pre_computed_intelligence"
    __table_args__ = (
        Index("idx_pci_key", "cache_key"),
        Index("idx_pci_type", "intelligence_type"),
    )
    
    id = Column(String(36), primary_key=True, default=_uuid)
    cache_key = Column(String(255), unique=True, nullable=False, index=True)
    cache_data = Column(JSON, default=dict)
    intelligence_type = Column(String(50), index=True)  # slt, nppi, moat, tender_analysis, competitor_map
    agency = Column(String(255), index=True)
    category = Column(String(100))
    zone = Column(String(100))
    tender_id = Column(String(100), index=True)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class UserQuery(Base):
    """Track user queries for continuous learning."""
    __tablename__ = "user_queries"
    
    id = Column(String(36), primary_key=True, default=_uuid)
    query_text = Column(Text)
    query_type = Column(String(50))  # tender_lookup, analysis_request, decision
    tender_id = Column(String(100), index=True)
    context = Column(JSON, default=dict)
    response_summary = Column(Text)
    response_time_ms = Column(Integer)
    was_cached = Column(Boolean, default=False)
    user_satisfaction = Column(String(20))  # satisfied, neutral, dissatisfied
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class RateAnalysis(Base):
    """Market rate analysis records."""
    __tablename__ = "rate_analysis"
    __table_args__ = (
        Index("idx_rate_rate_id", "rate_id"),
        Index("idx_rate_agency", "agency"),
    )
    
    id = Column(String(36), primary_key=True, default=_uuid)
    rate_id = Column(String(100), index=True, nullable=False)
    agency = Column(String(255))
    zone = Column(String(100))
    procurement_type = Column(String(255))
    item_code = Column(String(100))
    item_description = Column(Text)
    sor_rate = Column(Numeric(16, 2))
    quoted_rate = Column(Numeric(16, 2))
    rate_diff_pct = Column(Numeric(8, 4))
    market_trend = Column(String(100))
    raw_data = Column(JSON)
    source_file = Column(String(500))
    
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ── Multi-Client Subscription & Quota ────────────────────────────────────

# ⚠️ DEPRECATED — SubscriptionPlan, ClientSubscription, TenderUsageLog moved to app.models.subscription
# Import shims kept for backward compatibility with legacy code only.
# New code must import from app.models.subscription


# ⚠️ DEPRECATED — ClientPriorityState moved to canonical app.models.procurement
# Import shim kept for backward compatibility with legacy code only.
# New code must import from app.models.procurement


# ── Backward compatibility shims (ADR-002 migration, T-021 / T-022) ────────────────

# Import canonical models from app.models and re-export as legacy.
# This allows existing code to continue using `from app.db.models import Model`
# without modification, while the actual table definitions live in canonical app.models only.
# T-022: Tenant, Organization moved to app.models.enterprise; services updated
# T-023: crawlers/ETL migrated; shims will be deleted with final cleanup

try:
    from app.models.tender import Tender
except ImportError:
    Tender = None

try:
    from app.models.enterprise import Tenant, Organization
except ImportError:
    Tenant = None
    Organization = None

try:
    from app.models.subscription import ClientSubscription, SubscriptionPlan, TenderUsageLog
except ImportError:
    ClientSubscription = None
    SubscriptionPlan = None
    TenderUsageLog = None

try:
    from app.models.procurement import Award, OpeningReport, ClientPriorityState
except ImportError:
    Award = None
    OpeningReport = None
    ClientPriorityState = None

try:
    from app.models.agents_etl import AgentResult, NPPRecord, TenderDataPool, TenderReport, AgentThought, PreComputedIntelligence, RateAnalysis
except ImportError:
    AgentResult = None
    NPPRecord = None
    TenderDataPool = None
    TenderReport = None
    AgentThought = None
    PreComputedIntelligence = None
    RateAnalysis = None


# ── LEGACY-ONLY MODELS (T-023 Final Decision) ────────────────────────────────
#
# The following models remain in this file and are NOT migrated to canonical ORM:
#
# 1. TenderDocument (line 606):
#    - Reason: Table-name conflict with canonical app.models.tender.TenderDocument
#    - Canonical version: used by Tender relationship, structured with FK/enum
#    - Legacy version: used by crawlers (tender_dashboard.py, acquire_tender_1202364.py)
#      with extra extraction-tracking fields (extraction_method, extraction_status, page_count)
#    - Decision: Keep legacy-only; crawlers use this version, Tender API uses canonical version
#    - Safety: No breaking changes; both serve different purposes
#
# 2. Unused models (safe to delete in future cleanup):
#    - AgentLog, AgentJob, AgentBrainMessage (agent infrastructure, not imported anywhere)
#    - Ruleset, PPRSchedule, ComplianceCheck, FeedbackLabel (compliance/evaluation, not used)
#    - TenderPreparation, UserQuery, Lifecycle (legacy features, not used)
#    - Status: Completely unused; no imports found in codebase
#    - Future action: Safe to delete once schema cleanup is planned
#
# T-023 COMPLETE: All crawlers, agents, and services now use canonical ORM.
# Only 2 models remain legacy, both are handled and documented above.

# Note: TenderDocument remains legacy-only (no canonical migration) due to table name conflict with app.models.tender.TenderDocument
# Both models use __tablename__ = "tender_documents" but serve different purposes (canonical=upload, legacy=e-GP extraction)
