"""Subscription models: plans, subscriptions, and usage tracking."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Index, Integer, JSON, Numeric, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SubscriptionPlan(Base):
    """SaaS subscription plan definition (free, starter, professional, enterprise)."""

    __tablename__ = "subscription_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    monthly_tender_limit: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    monthly_price_bdt: Mapped[Numeric] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    features: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    subscriptions: Mapped[list["ClientSubscription"]] = relationship(
        "ClientSubscription", back_populates="plan"
    )

    __table_args__ = (
        Index("ix_subscription_plans_name", "name"),
        Index("ix_subscription_plans_is_active", "is_active"),
    )


class ClientSubscription(Base):
    """Tenant's active subscription to a plan with quota tracking."""

    __tablename__ = "client_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("subscription_plans.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    tender_quota_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tender_quota_limit: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    quota_reset_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    billing_cycle_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    billing_cycle_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    plan: Mapped["SubscriptionPlan"] = relationship("SubscriptionPlan", back_populates="subscriptions")
    tenant: Mapped["Tenant"] = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        Index("ix_client_subscriptions_tenant_id", "tenant_id"),
        Index("ix_client_subscriptions_status", "status"),
    )


class TenderUsageLog(Base):
    """Usage event log for tender quota tracking (pre-screen, win-prob, etc.)."""

    __tablename__ = "tender_usage_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    tender_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quota_consumed: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_tender_usage_logs_tenant_id", "tenant_id"),
        Index("ix_tender_usage_logs_tender_id", "tender_id"),
        Index("ix_tender_usage_logs_created_at", "created_at"),
    )
