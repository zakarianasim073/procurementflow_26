"""Agent and ETL models: results, thoughts, reports, and pre-computed intelligence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import Boolean, DateTime, Index, Integer, JSON, Numeric, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentResult(Base):
    """Store all agent execution results."""

    __tablename__ = "agent_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    agent_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    agent_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    agent_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    tender_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    output: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Provenance
    trace_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    source_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_agent_results_agent_id", "agent_id"),
        Index("ix_agent_results_tender_id", "tender_id"),
        Index("ix_agent_results_status", "status"),
    )


class NPPRecord(Base):
    """Negotiated Percentage Below Estimate (NPP) evaluation records."""

    __tablename__ = "npp_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tender_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    package_no: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    work_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pe_office: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    agency: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    zone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    estimated_amount_bdt: Mapped[Optional[Numeric]] = mapped_column(Numeric(16, 2), nullable=True)
    lowest_bid: Mapped[Optional[Numeric]] = mapped_column(Numeric(16, 2), nullable=True)
    bid_average: Mapped[Optional[Numeric]] = mapped_column(Numeric(16, 2), nullable=True)
    lowest_percent_below_oe: Mapped[Optional[Numeric]] = mapped_column(Numeric(8, 4), nullable=True)
    average_percent_below_oe: Mapped[Optional[Numeric]] = mapped_column(Numeric(8, 4), nullable=True)
    bid_spread_percent: Mapped[Optional[Numeric]] = mapped_column(Numeric(8, 4), nullable=True)
    bidder_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cluster_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    discount_strategy_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    slt_risk: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    likely_market_discount: Mapped[Optional[Numeric]] = mapped_column(Numeric(8, 4), nullable=True)
    source_file: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_npp_records_tender_id", "tender_id"),
        Index("ix_npp_records_agency", "agency"),
    )


class TenderDataPool(Base):
    """Central store for all extracted tender data - the Tender Dashboard."""

    __tablename__ = "tender_data_pool"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tender_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Basic Info
    package_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    work_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    procuring_entity: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pe_office: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    zone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    division: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Schedule & Dates
    publication_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closing_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    opening_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    tender_security_amount: Mapped[Optional[Numeric]] = mapped_column(Numeric(16, 2), nullable=True)
    performance_security_amount: Mapped[Optional[Numeric]] = mapped_column(Numeric(16, 2), nullable=True)
    completion_period_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Financial
    estimated_amount_bdt: Mapped[Optional[Numeric]] = mapped_column(Numeric(16, 2), nullable=True)
    tender_fee: Mapped[Optional[Numeric]] = mapped_column(Numeric(12, 2), nullable=True)

    # Qualification criteria extracted from TDS
    min_experience_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_turnover_bdt: Mapped[Optional[Numeric]] = mapped_column(Numeric(16, 2), nullable=True)
    min_liquid_assets_bdt: Mapped[Optional[Numeric]] = mapped_column(Numeric(16, 2), nullable=True)
    min_annual_construction_volume: Mapped[Optional[Numeric]] = mapped_column(Numeric(16, 2), nullable=True)
    similar_works_required: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    required_equipment: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    required_personnel: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    required_licenses: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    special_qualifications: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # BOQ and source document references
    boq_items: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    boq_total: Mapped[Optional[Numeric]] = mapped_column(Numeric(16, 2), nullable=True)
    nit_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tds_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    boq_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    drawings_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    corrigendum_urls: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    extraction_status: Mapped[Optional[str]] = mapped_column(String(20), default="pending", nullable=True)
    source_format: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Raw data ref
    raw_data_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_tender_data_pool_tender_id", "tender_id"),
    )


class TenderReport(Base):
    """Generated tender reports."""

    __tablename__ = "tender_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tender_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    report_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    report_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommendations: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    generated_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_tender_reports_tender_id", "tender_id"),
    )


class AgentThought(Base):
    """Agent thoughts/insights waiting for human approval."""

    __tablename__ = "agent_thoughts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    agent_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tender_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    thought_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    impact: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    reviewer_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_agent_thoughts_status", "status"),
        Index("ix_agent_thoughts_agent_id", "agent_id"),
    )


class PreComputedIntelligence(Base):
    """Pre-computed intelligence cache for instant query responses."""

    __tablename__ = "pre_computed_intelligence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    cache_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    cache_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    intelligence_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    agency: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    zone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tender_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_pre_computed_intelligence_cache_key", "cache_key"),
        Index("ix_pre_computed_intelligence_type", "intelligence_type"),
    )


class RateAnalysis(Base):
    """Market rate analysis records."""

    __tablename__ = "rate_analysis"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    rate_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    agency: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    zone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    procurement_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    item_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    item_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sor_rate: Mapped[Optional[Numeric]] = mapped_column(Numeric(16, 2), nullable=True)
    quoted_rate: Mapped[Optional[Numeric]] = mapped_column(Numeric(16, 2), nullable=True)
    rate_diff_pct: Mapped[Optional[Numeric]] = mapped_column(Numeric(8, 4), nullable=True)
    market_trend: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    source_file: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_rate_analysis_rate_id", "rate_id"),
        Index("ix_rate_analysis_agency", "agency"),
    )
