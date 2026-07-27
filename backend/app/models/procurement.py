"""Procurement models: awards, opening reports, and bid intelligence."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Index, Integer, JSON, Numeric, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Award(Base):
    """Tender award/contract award record with contractor details."""

    __tablename__ = "awards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)

    tender_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Award details
    award_amount: Mapped[Optional[Numeric]] = mapped_column(Numeric(16, 2), nullable=True)
    amount_bdt: Mapped[Optional[Numeric]] = mapped_column(Numeric(16, 2), nullable=True)
    award_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contract_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contract_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    work_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Contractor info
    contractor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    contractor_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    winner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    experience_cert_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Procurement details
    procurement_nature: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    procurement_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    agency: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Raw data
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    source_file: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_awards_tender_id", "tender_id"),
        Index("ix_awards_contractor_name", "contractor_name"),
        Index("ix_awards_tenant_id", "tenant_id"),
    )


class OpeningReport(Base):
    """Tender opening report with bid details and winner info."""

    __tablename__ = "opening_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tender_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)

    # Opening session info
    opening_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    opening_place: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    opened_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # TEC info
    estimated_amount_bdt: Mapped[Optional[Numeric]] = mapped_column(Numeric(16, 2), nullable=True)
    pe_office: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    agency: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    zone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    package_work_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Bidders - JSON array: [{name, quoted_amount, discount, final_amount, status}]
    bidders: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # SLT / ALT flags
    has_slt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_alt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Winning info
    winner_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    winner_amount: Mapped[Optional[Numeric]] = mapped_column(Numeric(16, 2), nullable=True)
    winner_discount: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Status
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Raw data
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    source_pdf: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_json: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_opening_reports_tender_id", "tender_id"),
        Index("ix_opening_reports_tenant_id", "tenant_id"),
        Index("ix_opening_reports_agency", "agency"),
    )


class ClientPriorityState(Base):
    """Tenant's bid priority state for a tender (score, tier, recommendation)."""

    __tablename__ = "client_priority_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    tender_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    priority_score: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    priority_tier: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)
    workload_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    need_for_work_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    financial_headroom: Mapped[Numeric] = mapped_column(Numeric(16, 2), default=0, nullable=False)
    recommendation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    advice_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_client_priority_states_tenant_id", "tenant_id"),
        Index("ix_client_priority_states_tender_id", "tender_id"),
        Index("ix_client_priority_states_priority_tier", "priority_tier"),
    )
