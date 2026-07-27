"""Analytics warehouse ORM models (T-020).

Dimension and fact tables for OLAP queries.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, Index, Numeric, String, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── DIMENSION TABLES ──────────────────────────────────────────────────


class DimAgencies(Base):
    """Agencies dimension table."""

    __tablename__ = "dim_agencies"

    agency_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agency_code: Mapped[str] = mapped_column(String(50), nullable=False)
    agency_name: Mapped[str] = mapped_column(String(255), nullable=False)
    division: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_tender_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_spend_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    tender_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_dim_agencies_code", "agency_code"),
        Index("ix_dim_agencies_division", "division"),
    )


class DimZones(Base):
    """Zones/regions dimension table."""

    __tablename__ = "dim_zones"

    zone_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    zone_name: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    agency_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tender_count: Mapped[int] = mapped_column(default=0)
    total_spend_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_dim_zones_region", "region"),
        Index("ix_dim_zones_type", "agency_type"),
    )


class DimCategories(Base):
    """Categories/sectors dimension table."""

    __tablename__ = "dim_categories"

    category_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    category_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    subsector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    tender_count: Mapped[int] = mapped_column(default=0)
    avg_tender_value_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    __table_args__ = (Index("ix_dim_categories_sector", "sector"),)


class DimContractors(Base):
    """Contractors dimension table."""

    __tablename__ = "dim_contractors"

    contractor_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    contractor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    zone: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    bid_count: Mapped[int] = mapped_column(default=0)
    award_count: Mapped[int] = mapped_column(default=0)
    total_contract_value_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    completion_rate_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_dim_contractors_name", "contractor_name"),
        Index("ix_dim_contractors_zone", "zone"),
    )


# ── FACT TABLES ───────────────────────────────────────────────────────


class FactTenders(Base):
    """Tenders fact table."""

    __tablename__ = "fact_tenders"

    tender_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agency_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("dim_agencies.agency_id"), nullable=True
    )
    zone_id: Mapped[Optional[str]] = mapped_column(
        String(10), ForeignKey("dim_zones.zone_id"), nullable=True
    )
    category_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("dim_categories.category_id"), nullable=True
    )
    tender_value_bdt: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    estimated_value_bdt: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    procurement_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tender_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="open")
    published_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    deadline_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    award_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    completion_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    bid_count: Mapped[int] = mapped_column(default=0)
    duration_days: Mapped[Optional[int]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_fact_tenders_agency", "agency_id"),
        Index("ix_fact_tenders_zone", "zone_id"),
        Index("ix_fact_tenders_category", "category_id"),
        Index("ix_fact_tenders_status", "status"),
        Index("ix_fact_tenders_published", "published_date"),
        Index("ix_fact_tenders_award", "award_date"),
    )


class FactAwards(Base):
    """Awards fact table."""

    __tablename__ = "fact_awards"

    award_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tender_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("fact_tenders.tender_id"), nullable=True
    )
    contractor_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("dim_contractors.contractor_id"), nullable=True
    )
    award_value_bdt: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    award_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    completion_status: Mapped[str] = mapped_column(String(50), default="pending")
    days_to_award: Mapped[Optional[int]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_fact_awards_tender", "tender_id"),
        Index("ix_fact_awards_contractor", "contractor_id"),
        Index("ix_fact_awards_date", "award_date"),
    )


class FactBids(Base):
    """Bids fact table."""

    __tablename__ = "fact_bids"

    bid_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tender_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("fact_tenders.tender_id"), nullable=True
    )
    contractor_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("dim_contractors.contractor_id"), nullable=True
    )
    bid_amount_bdt: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    bid_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    is_winner: Mapped[bool] = mapped_column(Boolean, default=False)
    days_to_bid: Mapped[Optional[int]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_fact_bids_tender", "tender_id"),
        Index("ix_fact_bids_contractor", "contractor_id"),
        Index("ix_fact_bids_date", "bid_date"),
        Index("ix_fact_bids_winner", "is_winner"),
    )
