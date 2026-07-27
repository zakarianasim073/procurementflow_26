"""
Webhook Subscription Model

Enterprise webhook support for outbound event delivery.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WebhookSubscription(Base):
    """
    A webhook subscription for receiving outbound events.

    Subscribers register a URL and event filter; the system POSTs
    JSON payloads to the URL whenever matching events occur.
    """
    __tablename__ = "webhook_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Target
    url: Mapped[str] = mapped_column(Text, nullable=False)
    secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Event filtering
    event_types: Mapped[List[str]] = mapped_column(JSON, default=list)  # e.g. ["tender.awarded", "agent.completed"]
    event_filter: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSONPath or simple key=val filter

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Delivery stats
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    last_delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Retry config
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    __table_args__ = (
        Index("ix_webhook_subs_tenant_active", "tenant_id", "is_active"),
        Index("ix_webhook_subs_verified", "is_verified", "is_active"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "url": self.url,
            "event_types": self.event_types or [],
            "event_filter": self.event_filter,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_status": self.last_status,
            "last_delivered_at": self.last_delivered_at.isoformat() if self.last_delivered_at else None,
            "last_error": self.last_error,
            "max_retries": self.max_retries,
            "retry_interval_seconds": self.retry_interval_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WebhookDeliveryLog(Base):
    """
    Audit log of every webhook delivery attempt.
    """
    __tablename__ = "webhook_delivery_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subscription_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Payload snapshot
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    payload_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Response
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Error
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_webhook_logs_sub_created", "subscription_id", "created_at"),
    )
